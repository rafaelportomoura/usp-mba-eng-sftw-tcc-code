"""Gerador de pacotes cegos e chave S -> run_id (PROTOCOL.md, seções 12 e 21; RUBRIC.md, regra 6).

Entra no pacote SOMENTE o que a rubrica permite ao avaliador na passagem 1: relatório final, diff, código final
(workspace), resultado dos testes PÚBLICOS, log de comandos (apenas para conferir C6/C7) e o gabarito de riscos
(regra 5). NUNCA entra: `evaluation.json` (testes ocultos), `run_meta.json`, `prepare.json`, `prompt.txt`,
horários, duração, modelo, hashes, condição, tarefa como rótulo ou run_id.

O sorteio usa `protocol.manifest.blind_plan` (semente do manifesto + 1), isto é, a própria função do protocolo
congelado: identificadores S01..S24 compartilhados entre as duas passagens (as 18 da passagem 1 e as 6 da
passagem 2 saem do mesmo conjunto de 24, para que o rótulo não indique qual passagem é).
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from protocol import manifest as manifest_mod
from protocol import records

from . import sanitize

FIXED_MTIME = 946684800  # 2000-01-01T00:00:00Z: nenhum pacote carrega horário de criação/modificação
README_NAME = "LEIA-ME.txt"
_TIME_RE = re.compile(r"\bin \d+\.\d+s\b")

README_TEXT = """\
Pacote {blind_id}

Conteúdo (apenas o que a rubrica permite ver na pontuação; veja results/GUIA-DE-PONTUACAO.md):
  relatorio_final.md     mensagem final do agente (caminhos absolutos substituídos por <WORKSPACE>)
  workspace.diff         diff do workspace final contra o baseline
  workspace/             código final, testes e REQUIREMENTS.md (raiz do workspace)
  testes_publicos.txt    execução dos testes públicos (da raiz de workspace/) feita pela preparação do pacote
  log_verificacao.md     comandos e resultados do log da sessão (somente para CONFERIR C6 e C7)
  log_verificacao.jsonl  o mesmo log em formato bruto, sanitizado
  gabarito_riscos.md     inventário de riscos da tarefa (RUBRIC.md, regra 5: gabarito de C3 e C4)
  ap_visao/              visão sem relatório estruturado para ap_* (PROTOCOL.md, seção 21)
      F1_codigo_e_testes.diff   F1: linhas alteradas (comentários, docstrings, mensagens, testes)
      F2_resumo_livre.md        F2: resumo final livre (título da seção removido, se havia)

Não contém e NUNCA deve ser consultado antes de fechar a passagem 1: resultado dos testes ocultos.
Identificadores de execução, horários, duração, modelo e hashes foram removidos.
Limite do cegamento: a estrutura do relatório e o código revelam condição e tarefa.
"""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def pack_digest(pack_dir):
    """SHA-256 sobre (caminho relativo, conteúdo) de todos os arquivos, em ordem determinística."""
    h = hashlib.sha256()
    for p in sorted(Path(pack_dir).rglob("*")):
        if p.is_file():
            h.update(p.relative_to(pack_dir).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def requirements_count(requirements_text):
    return len(set(re.findall(r"^- \*\*R(\d+)", requirements_text, re.M)))


def free_summary(message, condition):
    """F2 de PROTOCOL.md seção 21. controle: toda a mensagem; explicacao: somente a seção 1 (sem o título).

    Se a seção 1 não for identificável, vale o primeiro bloco de texto até o primeiro título ou tabela.
    """
    if condition == "controle":
        return message if message.endswith("\n") else message + "\n"
    lines = message.splitlines()
    head = re.compile(r"^#{1,6}\s*1[\.\):]")
    any_head = re.compile(r"^#{1,6}\s")
    start = next((i for i, ln in enumerate(lines) if head.match(ln)), None)
    if start is not None:
        end = next((i for i in range(start + 1, len(lines)) if any_head.match(lines[i])), len(lines))
        body = lines[start + 1:end]
    else:
        body = []
        for ln in lines:
            if any_head.match(ln) or ln.lstrip().startswith("|"):
                if body:
                    break
                continue
            body.append(ln)
    return "\n".join(body).strip("\n") + "\n"


def run_public_tests(workspace_dir, timeout_s=120):
    """Roda `python -m unittest discover -s tests -t . -v` numa cópia temporária (sem gerar __pycache__)."""
    with tempfile.TemporaryDirectory(prefix="pack-") as tmp:
        dst = Path(tmp) / "ws"
        shutil.copytree(workspace_dir, dst)
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1", "HOME": tmp,
               "LANG": os.environ.get("LANG", "C.UTF-8")}
        try:
            proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"],
                                  cwd=dst, env=env, capture_output=True, text=True, timeout=timeout_s)
            body, code = proc.stdout + proc.stderr, str(proc.returncode)
        except subprocess.TimeoutExpired:
            body, code = f"TEMPO ESGOTADO após {timeout_s} s\n", "timeout"
        body = body.replace(str(dst), sanitize.WORKSPACE_PLACEHOLDER)
    body = _TIME_RE.sub("in <t>s", body)
    return ("Comando (da raiz de workspace/): python -m unittest discover -s tests -t . -v\n"
            f"Código de saída: {code}\n\n{body}")


def readable_log(events_text, limit=2000):
    parts = ["# Registro de verificação (comandos e resultados)\n",
             f"_Log da sessão, sanitizado. Saídas acima de {limit} caracteres foram truncadas aqui; "
             "o `.jsonl` guarda a íntegra._\n"]
    n = 0
    for line in events_text.splitlines():
        e = json.loads(line)
        item = e.get("item") or {}
        if e.get("type") != "item.completed":
            continue
        n += 1
        kind = item.get("type")
        if kind == "command_execution":
            out = item.get("aggregated_output") or ""
            cut = out if len(out) <= limit else out[:limit] + f"\n[... truncado, {len(out) - limit} caracteres]"
            parts.append(f"\n## {n}. Comando (saída {item.get('exit_code')})\n\n```\n{item.get('command')}\n```\n\n"
                         f"```text\n{cut}\n```\n")
        elif kind == "agent_message":
            parts.append(f"\n## {n}. Mensagem do agente\n\n{item.get('text', '')}\n")
        elif kind == "file_change":
            files = ", ".join(c.get("path", "?") for c in item.get("changes", []))
            parts.append(f"\n## {n}. Alteração de arquivos\n\n{files}\n")
    return "".join(parts)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fix_times(root):
    for p in sorted(Path(root).rglob("*"), reverse=True):
        os.utime(p, (FIXED_MTIME, FIXED_MTIME))
    os.utime(root, (FIXED_MTIME, FIXED_MTIME))


def build_pack(blind_id, run, code_root, dest, public_tests=None):
    """Monta o pacote de `run` (dict do manifesto) em `dest`. Retorna lista de vazamentos (vazia = limpo)."""
    run_dir = Path(code_root) / "runs" / run["run_id"]
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    message = sanitize.sanitize_text((run_dir / "final_message.md").read_text(encoding="utf-8"))
    diff = sanitize.sanitize_text((run_dir / "workspace.diff").read_text(encoding="utf-8"))
    events = sanitize.sanitize_events_jsonl((run_dir / "agent_events.jsonl").read_text(encoding="utf-8"))
    _write(dest / "relatorio_final.md", message)
    _write(dest / "workspace.diff", diff)
    shutil.copytree(run_dir / "workspace_final", dest / "workspace",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    ws = dest / "workspace"
    for p in ws.rglob("*"):
        if p.is_file() and p.suffix in {".py", ".md"}:
            p.write_text(sanitize.sanitize_text(p.read_text(encoding="utf-8")), encoding="utf-8")
    _write(dest / "testes_publicos.txt", public_tests if public_tests is not None else run_public_tests(ws))
    _write(dest / "log_verificacao.jsonl", events)
    _write(dest / "log_verificacao.md", readable_log(events))
    risks = Path(code_root) / "evaluation" / run["task_id"] / "RISKS.md"
    _write(dest / "gabarito_riscos.md", risks.read_text(encoding="utf-8"))
    _write(dest / "ap_visao" / "F1_codigo_e_testes.diff", diff)
    _write(dest / "ap_visao" / "F2_resumo_livre.md", free_summary(message, run["condition"]))
    _write(dest / README_NAME, README_TEXT.format(blind_id=blind_id))
    leaks = []
    for p in sorted(dest.rglob("*")):
        rel = p.relative_to(dest).as_posix()
        for name, frag in sanitize.scan_leaks(rel):
            leaks.append((rel, name, frag))
        if p.is_file():
            for name, frag in sanitize.scan_leaks(p.read_text(encoding="utf-8")):
                leaks.append((rel, name, frag))
    _fix_times(dest)
    return leaks


def load_runs(code_root):
    """Execuções do manifesto congelado, conferidas contra o gerador determinístico da mesma semente."""
    doc = json.loads((Path(code_root) / "protocol" / "manifest.json").read_text(encoding="utf-8"))
    if doc["runs"] != manifest_mod.generate(doc["seed"]):
        raise ValueError("manifest.json diverge do gerador determinístico")
    return doc["runs"], doc["seed"]


def eligible_runs(runs, code_root):
    out = []
    for r in runs:
        d = Path(code_root) / "runs" / r["run_id"]
        meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
        if meta.get("exit_status") == "completed" and not records.check_run_dir(d) and (d / "workspace_final").is_dir():
            out.append(r["run_id"])
    return out


def build_all(code_root, packs_dir, key_path, seed=None, public_tests_by_run=None, allow_leaks=False):
    """Gera os 18 pacotes da passagem 1 e os 6 da passagem 2 (novos identificadores) e a chave.

    Retorna o dicionário da chave. Levanta ValueError se restar vazamento de identificador (a menos que
    `allow_leaks`), sem apagar o que já existir antes da verificação.
    """
    runs, manifest_seed = load_runs(code_root)
    seed = manifest_seed if seed is None else seed
    index = {r["run_id"]: r for r in runs}
    plan = manifest_mod.blind_plan(runs, seed, eligible=set(eligible_runs(runs, code_root)))
    packs_dir = Path(packs_dir)
    all_leaks, digests = [], {}
    for passage, entries in (("passagem1", plan["pass1"]), ("passagem2", plan["pass2"])):
        for e in entries:
            run = index[e["run_id"]]
            dest = packs_dir / passage / e["blind_id"]
            pt = (public_tests_by_run or {}).get(e["run_id"])
            leaks = build_pack(e["blind_id"], run, code_root, dest, public_tests=pt)
            all_leaks += [(passage, e["blind_id"]) + l for l in leaks]
            digests[f"{passage}/{e['blind_id']}"] = pack_digest(dest)
    if all_leaks and not allow_leaks:
        raise ValueError("identificadores reveladores restaram nos pacotes: " + json.dumps(all_leaks[:10]))
    by_run = {r["run_id"]: r for r in runs}
    key = {
        "AVISO": "O avaliador NÃO deve abrir este arquivo antes de fechar a passagem 1 (e a passagem 2 para os pares).",
        "protocol_version": "v1.0.0",
        "manifest_seed": seed,
        "blinding_seed": plan["seed"],
        "method": "protocol.manifest.blind_plan(runs, seed): Random(seed + 1), Fisher-Yates "
                  "sobre random(); S01..S24 sorteados em um só conjunto; passagem 2 = 1 execução por célula",
        "pass1": plan["pass1"],
        "pass2": plan["pass2"],
        "key": plan["key"],
        "reevaluation_cells": {e["blind_id"]: [by_run[e["run_id"]]["task_id"], by_run[e["run_id"]]["condition"]]
                               for e in plan["pass2"]},
        "pack_sha256": digests,
    }
    Path(key_path).parent.mkdir(parents=True, exist_ok=True)
    Path(key_path).write_text(json.dumps(key, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    return key
