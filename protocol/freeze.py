"""Congelamento do protocolo (comando `freeze`). NÃO executar antes da liberação dos oráculos.

Precondições (todas verificadas, nenhuma contornável):
  1. --release-ref aponta para um arquivo existente (relatório do revisor independente);
  2. --confirm-oracles-released explícito;
  3. protocol/execution_config.json existe e não contém null;
  4. o manifesto passa em manifest.check_runs (18 e fallback 12);
  5. ainda não existe FREEZE.json.
Efeito: grava FREEZE.json (versão, data, semente, hashes SHA-256 de prompts, rubrica, protocolo,
esquema, configuração e baseline de cada tarefa) e manifest.json (cópia do rascunho com hashes).
Depois disso, qualquer alteração nos arquivos listados invalida o congelamento (verify_freeze).
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import manifest as manifest_mod
from . import records

FROZEN_FILES = (
    "PROTOCOL.md",
    "RUBRIC.md",
    "taxonomy.py",
    "sensitivity.py",
    "prompts/controle.md",
    "prompts/explicacao.md",
    "schema/run_record.schema.json",
    "schema/results_header.csv",
    "schema/reevaluation_header.csv",
    "config/execution_config.json",
)


# P3: campos de replicabilidade do Codex que não podem estar nulos, vazios nem ser 'nao_exposto'
# no congelamento (o valor deve ser o que a execução reporta; nada é presumido).
REQUIRED_CONFIG_FIELDS = (
    "model.name",
    "model.version_or_snapshot",
    "agent.codex_version",
    "agent.interface",
    "agent.invocation_command",
    "agent.flags",
    "agent.sandbox_mode",
    "agent.approval_policy",
    "execution.working_directory",
    "execution.date_first_run",
)
INTERFACES = ("cli", "api")


class FreezeError(Exception):
    pass


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _find_nulls(value, prefix=""):
    if value is None:
        return [prefix or "(raiz)"]
    found = []
    if isinstance(value, dict):
        for k, v in value.items():
            found += _find_nulls(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            found += _find_nulls(v, f"{prefix}[{i}]")
    return found


def _get_path(cfg, dotted):
    cur = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return KeyError
        cur = cur[part]
    return cur


def check_codex_interface_fields(cfg):
    """Problemas nos campos obrigatórios de interface/versão do Codex (P3). Lista vazia = ok."""
    problems = []
    for dotted in REQUIRED_CONFIG_FIELDS:
        value = _get_path(cfg, dotted)
        if value is KeyError:
            problems.append(f"campo obrigatório ausente: {dotted}")
        elif value is None:
            problems.append(f"campo obrigatório nulo: {dotted}")
        elif dotted == "agent.flags":
            if not isinstance(value, list) or not all(isinstance(f, str) and f.strip() for f in value):
                problems.append("agent.flags deve ser lista de strings não vazias (lista vazia = nenhuma flag)")
        elif not isinstance(value, str) or not value.strip() or value.strip().lower() == "nao_exposto":
            problems.append(f"campo obrigatório vazio ou 'nao_exposto': {dotted}")
        elif dotted == "agent.interface" and value not in INTERFACES:
            problems.append(f"agent.interface deve ser um de {INTERFACES}, recebido {value!r}")
    problems += check_author_choices(cfg)
    return problems


def check_author_choices(cfg):
    """Q11: se `author_choices` existir, model.name e generation_parameters.reasoning_effort devem
    coincidir com os valores escolhidos pelo autor (evita deriva entre a decisão e o congelado)."""
    choices = cfg.get("author_choices") if isinstance(cfg, dict) else None
    if not choices:
        return []
    problems = []
    for chosen, dotted in (("model_name", "model.name"), ("reasoning_effort", "generation_parameters.reasoning_effort")):
        value = _get_path(cfg, dotted)
        if value != choices.get(chosen):
            problems.append(f"{dotted}={value!r} diverge da escolha do autor em author_choices.{chosen}={choices.get(chosen)!r}")
    return problems


def check_preconditions(protocol_dir, release_ref, confirmed):
    protocol_dir = Path(protocol_dir)
    problems = []
    if not release_ref or not Path(release_ref).is_file():
        problems.append("--release-ref ausente ou inexistente (relatório de liberação do revisor)")
    if not confirmed:
        problems.append("falta --confirm-oracles-released")
    if (protocol_dir / "FREEZE.json").exists():
        problems.append("FREEZE.json já existe; o protocolo já está congelado")
    for rel in FROZEN_FILES:
        if not (protocol_dir / rel).is_file():
            problems.append(f"arquivo ausente: {rel}")
    cfg = protocol_dir / "config" / "execution_config.json"
    if cfg.is_file():
        cfg_doc = json.loads(cfg.read_text(encoding="utf-8"))
        nulls = _find_nulls(cfg_doc)
        if nulls:
            problems.append("execution_config.json com campos null: " + ", ".join(nulls))
        problems += [f"execution_config.json: {p}" for p in check_codex_interface_fields(cfg_doc)]
    draft = protocol_dir / "manifest.draft.json"
    if not draft.is_file():
        problems.append("manifest.draft.json ausente")
    else:
        doc = json.loads(draft.read_text(encoding="utf-8"))
        try:
            manifest_mod.check_runs(doc["runs"])
            manifest_mod.check_runs(doc["runs"], fallback_only=True)
        except ValueError as exc:
            problems.append(f"manifesto inválido: {exc}")
    return problems


def freeze(protocol_dir, release_ref, confirmed, baseline_hash_fn, version="v1.0.0", now=None):
    """Congela. `baseline_hash_fn(task_id)` -> sha256 (harness.workspace.baseline_hash)."""
    protocol_dir = Path(protocol_dir)
    problems = check_preconditions(protocol_dir, release_ref, confirmed)
    if problems:
        raise FreezeError("; ".join(problems))
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    file_hashes = {rel: sha256_file(protocol_dir / rel) for rel in FROZEN_FILES}
    doc = json.loads((protocol_dir / "manifest.draft.json").read_text(encoding="utf-8"))
    prompt_hashes = {c: file_hashes[f"prompts/{c}.md"] for c in manifest_mod.CONDITIONS}
    baseline_hashes = {t: baseline_hash_fn(t) for t in manifest_mod.TASKS}
    config = json.loads((protocol_dir / "config" / "execution_config.json").read_text(encoding="utf-8"))
    final = dict(doc, status="FROZEN", frozen=True, protocol_version=version,
                 prompt_hashes=prompt_hashes, baseline_hashes=baseline_hashes,
                 execution_config=config)
    manifest_text = manifest_mod.dumps(final)
    (protocol_dir / "manifest.json").write_text(manifest_text, encoding="utf-8")
    freeze_doc = {
        "protocol_version": version,
        "frozen_at": now,
        "seed": doc["seed"],
        "release_ref": str(release_ref),
        "release_ref_sha256": sha256_file(release_ref),
        "files": file_hashes,
        "manifest_json_sha256": hashlib.sha256(manifest_text.encode("utf-8")).hexdigest(),
        "prompt_hashes": prompt_hashes,
        "baseline_hashes": baseline_hashes,
    }
    (protocol_dir / "FREEZE.json").write_text(
        json.dumps(freeze_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return freeze_doc


def verify_freeze(protocol_dir):
    """Lista de divergências entre os arquivos atuais e FREEZE.json (vazia = íntegro)."""
    protocol_dir = Path(protocol_dir)
    doc = json.loads((protocol_dir / "FREEZE.json").read_text(encoding="utf-8"))
    diffs = []
    for rel, digest in doc["files"].items():
        path = protocol_dir / rel
        if not path.is_file() or sha256_file(path) != digest:
            diffs.append(rel)
    mpath = protocol_dir / "manifest.json"
    if not mpath.is_file() or hashlib.sha256(mpath.read_bytes()).hexdigest() != doc["manifest_json_sha256"]:
        diffs.append("manifest.json")
    return diffs
