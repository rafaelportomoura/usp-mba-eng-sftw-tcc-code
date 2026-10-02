"""Validação de registros consolidados contra schema/run_record.schema.json (somente stdlib).

Implementa o subconjunto de JSON Schema usado pelo esquema (type, enum, pattern, minimum,
maximum, minLength, required, additionalProperties) e acrescenta regras semânticas.
"""

import csv
import io
import json
import re
from pathlib import Path

from . import manifest as manifest_mod
from . import taxonomy

PROTOCOL_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = PROTOCOL_DIR / "schema" / "run_record.schema.json"
SCORE_FIELDS = ("trace_code", "trace_tests", "assumptions", "risks", "rationale", "fidelity", "reproducibility")
ERR_FIELDS = tuple(taxonomy.err_field(t) for t in taxonomy.ERROR_TYPES)
CLAIM_FIELDS = tuple(taxonomy.claim_field(t) for t in taxonomy.CLAIM_TYPES)
RP_FIELDS = ("rp_assumptions", "rp_risks", "rp_traces")
# Arquivos produzidos na pontuação (depois da execução); não fazem parte de REQUIRED_RUN_FILES.
SCORING_RUN_FILES = (
    "error_classification.json",  # P1: um item por teste oculto reprovado e por alegação divergente
    "review_points.json",         # P2: itens contados, com o veredito de cada um
)
# Registro de revisão humana de trechos gerados e reutilizados no texto (P4); só o cabeçalho é fixo.
AI_REVIEW_FIELDS = ("item_id", "origem", "run_id", "destino_no_texto", "tipo_uso", "revisor",
                    "data_revisao", "como_foi_verificado", "decisao", "observacoes")
REQUIRED_RUN_FILES = (
    "prompt.txt",          # bytes exatos enviados ao agente (origem do prompt_hash)
    "agent_events.jsonl",  # log nativo do Codex, com a versao da ferramenta registrada
    "final_message.md",    # mensagem final do agente (base de output_words e da rubrica)
    "workspace.diff",      # diff do workspace final contra o baseline
    "prepare.json",        # harness: manifesto do workspace
    "evaluation.json",     # harness: testes publicos/ocultos
    "run_meta.json",       # run_id, modelo, versao, horarios, exit_status
)


def load_schema(path=SCHEMA_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _type_ok(value, expected):
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    raise ValueError(f"tipo não suportado: {expected}")


def _check_value(name, value, spec, errors):
    if not _type_ok(value, spec["type"]):
        errors.append(f"{name}: tipo {type(value).__name__} inválido, esperado {spec['type']}")
        return
    if "enum" in spec and value not in spec["enum"]:
        errors.append(f"{name}: valor {value!r} fora de {spec['enum']}")
    if "pattern" in spec and isinstance(value, str) and not re.search(spec["pattern"], value):
        errors.append(f"{name}: não corresponde a {spec['pattern']}")
    if "minLength" in spec and isinstance(value, str) and len(value) < spec["minLength"]:
        errors.append(f"{name}: comprimento menor que {spec['minLength']}")
    if "minimum" in spec and not isinstance(value, str) and value < spec["minimum"]:
        errors.append(f"{name}: {value} < {spec['minimum']}")
    if "maximum" in spec and not isinstance(value, str) and value > spec["maximum"]:
        errors.append(f"{name}: {value} > {spec['maximum']}")


def validate_schema(record, schema=None):
    schema = schema or load_schema()
    errors = []
    for name in schema.get("required", []):
        if name not in record:
            errors.append(f"{name}: ausente")
    if schema.get("additionalProperties") is False:
        for name in record:
            if name not in schema["properties"]:
                errors.append(f"{name}: campo não previsto")
    for name, spec in schema["properties"].items():
        if name in record:
            _check_value(name, record[name], spec, errors)
    return errors


def validate_record(record, schema=None):
    """Esquema + regras semânticas. Retorna lista de erros (vazia = válido)."""
    errors = validate_schema(record, schema)
    if errors:
        return errors
    total = sum(record[f] for f in SCORE_FIELDS)
    if record["auditability_total"] != total:
        errors.append(f"auditability_total={record['auditability_total']} difere da soma dos itens ({total})")
    if record["hidden_tests_passed"] > record["hidden_tests_total"]:
        errors.append("hidden_tests_passed excede hidden_tests_total")
    if record["exit_status"] == "completed" and record["duration_s"] > manifest_mod.TIMEOUT_S:
        errors.append(f"completed com duration_s > timeout de {manifest_mod.TIMEOUT_S}s")
    failed = record["hidden_tests_total"] - record["hidden_tests_passed"]
    if sum(record[f] for f in ERR_FIELDS) != failed:
        errors.append(f"soma de err_* ({sum(record[f] for f in ERR_FIELDS)}) difere de hidden_tests_total - "
                      f"hidden_tests_passed ({failed}): todo teste reprovado ou não executado recebe um tipo")
    if sum(record[f] for f in CLAIM_FIELDS) > record["claims_checked"]:
        errors.append("claimdiv_* excede claims_checked")
    if record["condition"] == "controle" and (record["claims_checked"] or any(record[f] for f in CLAIM_FIELDS)):
        errors.append("controle: claims_checked e claimdiv_* devem ser 0 (a classificação de alegações vale só para explicacao)")
    if record["claims_checked"] > 10:
        errors.append("claims_checked > 10 (limite do procedimento de C6)")
    points = sum(record[f] for f in RP_FIELDS)
    if record["rp_confirmed"] > points:
        errors.append("rp_confirmed excede a soma de rp_assumptions, rp_risks e rp_traces")
    if record["exit_status"] == "timeout" and record["duration_s"] < manifest_mod.TIMEOUT_S * 0.99:
        errors.append("timeout com duration_s inferior ao limite de 12 minutos")
    return errors


def coerce_row(row, schema=None):
    """Converte strings de uma linha CSV para os tipos do esquema (falhas permanecem string)."""
    schema = schema or load_schema()
    out = {}
    for name, raw in row.items():
        spec = schema["properties"].get(name)
        if spec is not None and isinstance(raw, str):
            try:
                if spec["type"] == "integer":
                    raw = int(raw)
                elif spec["type"] == "number":
                    raw = float(raw)
            except ValueError:
                pass
        out[name] = raw
    return out


def header():
    return list(load_schema()["properties"])


def read_csv(text):
    reader = csv.DictReader(io.StringIO(text))
    expected = header()
    if reader.fieldnames != expected:
        raise ValueError(f"cabeçalho inválido: {reader.fieldnames} != {expected}")
    return [coerce_row(r) for r in reader]


def write_csv(records):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=header(), lineterminator="\n")
    writer.writeheader()
    for r in records:
        writer.writerow(r)
    return buf.getvalue()


def validate_dataset(records, manifest_runs=None, fallback=False, freeze=None):
    """Valida o conjunto: registros, unicidade, balanceamento e consistência com o manifesto.

    `manifest_runs`: lista de execuções do manifesto (consistência de tarefa/condição/repetição).
    `fallback`: exige 2 repetições por célula (12 registros) em vez de 3 (18).
    `freeze`: documento FREEZE.json; hashes de prompt e baseline devem coincidir.
    """
    errors = []
    for i, r in enumerate(records):
        for e in validate_record(r):
            errors.append(f"linha {i + 2} ({r.get('run_id', '?')}): {e}")
    if errors:
        return errors
    ids = [r["run_id"] for r in records]
    if len(set(ids)) != len(ids):
        errors.append("run_id duplicado")
    if any(r["exit_status"] == "infra_failure" for r in records):
        errors.append("infra_failure não pertence ao conjunto consolidado (vai para o registro de exclusões)")
    expected_reps = 2 if fallback else 3
    for cell in manifest_mod.cells():
        reps = sorted(r["replicate"] for r in records if (r["task_id"], r["condition"]) == cell)
        if reps != list(range(1, expected_reps + 1)):
            errors.append(f"célula {cell[0]}/{cell[1]} desbalanceada: repetições {reps}")
    by_cond, by_task = {}, {}
    for r in records:
        by_cond.setdefault(r["condition"], set()).add(r["prompt_hash"])
        by_task.setdefault(r["task_id"], set()).add(r["baseline_hash"])
    for cond, hashes in by_cond.items():
        if len(hashes) != 1:
            errors.append(f"condição {cond} com mais de um prompt_hash")
    if len(by_cond) == 2 and len({next(iter(h)) for h in by_cond.values()}) != 2:
        errors.append("as duas condições compartilham o mesmo prompt_hash")
    for task, hashes in by_task.items():
        if len(hashes) != 1:
            errors.append(f"tarefa {task} com mais de um baseline_hash")
    if manifest_runs is not None:
        index = {m["run_id"]: m for m in manifest_runs}
        for r in records:
            m = index.get(r["run_id"])
            if m is None:
                errors.append(f"{r['run_id']}: ausente do manifesto")
            elif (m["task_id"], m["condition"], m["replicate"]) != (r["task_id"], r["condition"], r["replicate"]):
                errors.append(f"{r['run_id']}: tarefa/condição/repetição divergem do manifesto")
    if freeze is not None:
        for r in records:
            if r["prompt_hash"] != freeze["prompt_hashes"].get(r["condition"]):
                errors.append(f"{r['run_id']}: prompt_hash diverge do congelado")
            if r["baseline_hash"] != freeze["baseline_hashes"].get(r["task_id"]):
                errors.append(f"{r['run_id']}: baseline_hash diverge do congelado")
    return errors


def check_run_dir(path):
    """Lista de arquivos obrigatórios ausentes em runs/<run_id>/."""
    path = Path(path)
    return [f for f in REQUIRED_RUN_FILES if not (path / f).is_file()]


def count_words(text):
    """Palavras da mensagem final: sequências \\w+ (hífen/apóstrofo internos unem). Pipes e '---' de tabelas não contam."""
    return len(re.findall(r"\w+(?:[’'-]\w+)*", text))
