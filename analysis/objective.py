"""Campos OBJETIVOS por execução, lidos de runs/ (nunca mostrados nas fichas do avaliador).

Saída: results/consolidado_esqueleto.csv com o cabeçalho de schema/results_header.csv; só as colunas objetivas
são preenchidas. Contém condição, duração e resultado dos testes ocultos, portanto NÃO deve ser aberto antes de
fechar a passagem 1 (RUBRIC.md, regra 6; PROTOCOL.md, seção 12).
"""

import csv
import hashlib
import io
import json
from pathlib import Path

from protocol import records

OBJECTIVE_FIELDS = ("run_id", "task_id", "condition", "replicate", "model", "codex_version", "codex_interface",
                    "prompt_hash", "baseline_hash", "started_at", "duration_s", "exit_status",
                    "hidden_tests_passed", "hidden_tests_total", "output_words")


def run_objective(code_root, run, interface):
    d = Path(code_root) / "runs" / run["run_id"]
    meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8"))
    ev = json.loads((d / "evaluation.json").read_text(encoding="utf-8"))
    prompt_hash = hashlib.sha256((d / "prompt.txt").read_bytes()).hexdigest()
    if prompt_hash != meta.get("prompt_sha256"):
        raise ValueError(f"{run['run_id']}: prompt.txt não confere com prompt_sha256 de run_meta.json")
    return {
        "run_id": run["run_id"], "task_id": run["task_id"], "condition": run["condition"],
        "replicate": run["replicate"], "model": meta["model_passed"], "codex_version": meta["codex_version_reported"],
        "codex_interface": interface, "prompt_hash": prompt_hash, "baseline_hash": ev["baseline_hash"],
        "started_at": meta["started_at"], "duration_s": meta["duration_s"], "exit_status": meta["exit_status"],
        "hidden_tests_passed": ev["hidden_tests_passed"], "hidden_tests_total": ev["hidden_tests_total"],
        "output_words": records.count_words((d / "final_message.md").read_text(encoding="utf-8")),
    }


def skeleton_rows(code_root, runs):
    cfg = json.loads((Path(code_root) / "protocol" / "config" / "execution_config.json").read_text(encoding="utf-8"))
    interface = cfg["agent"]["interface"]
    rows = []
    for run in sorted(runs, key=lambda r: r["run_id"]):
        obj = run_objective(code_root, run, interface)
        rows.append({h: obj.get(h, "") for h in records.header()})
    return rows


def write_skeleton(path, rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=records.header(), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(buf.getvalue(), encoding="utf-8")
