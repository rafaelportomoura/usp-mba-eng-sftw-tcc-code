"""Repositório experimental sintético (18 execuções com identificadores reveladores plantados)."""

import hashlib
import json
from pathlib import Path

from protocol import manifest

MODULES = {"t1_shipping": "shipping", "t2_order_pricing": "pricing", "t3_inventory_reservation": "inventory"}
NREQ = {"t1_shipping": 7, "t2_order_pricing": 8, "t3_inventory_reservation": 7}
MODEL = "gpt-9.9-secreto"
BASELINE = {t: hashlib.sha256(t.encode()).hexdigest() for t in manifest.TASKS}
PROMPT = {c: b"prompt " + c.encode() for c in manifest.CONDITIONS}


def thread_id(n):
    return f"01a0fb{n:02d}-ce32-7832-9352-5be0ae3c8c1e"


def make_code_root(root):
    root = Path(root)
    runs = manifest.generate()
    (root / "protocol" / "config").mkdir(parents=True)
    (root / "protocol" / "manifest.json").write_text(json.dumps({"seed": manifest.SEED, "runs": runs}), encoding="utf-8")
    (root / "protocol" / "config" / "execution_config.json").write_text(json.dumps({"agent": {"interface": "cli"}}), encoding="utf-8")
    (root / "protocol" / "FREEZE.json").write_text(json.dumps({
        "prompt_hashes": {c: hashlib.sha256(b).hexdigest() for c, b in PROMPT.items()},
        "baseline_hashes": BASELINE}), encoding="utf-8")
    for task in manifest.TASKS:
        d = root / "evaluation" / task
        d.mkdir(parents=True)
        (d / "RISKS.md").write_text(f"# Riscos de {task}\n1. risco de exemplo\n", encoding="utf-8")
    for n, r in enumerate(runs, start=1):
        _make_run(root / "runs" / r["run_id"], r, n)
    return runs


def _make_run(d, r, n):
    task, cond, rid = r["task_id"], r["condition"], r["run_id"]
    mod = MODULES[task]
    scratch = f"/home/alguem/.cache/tcc-scratch/{rid}/workspace"
    ws = d / "workspace_final"
    (ws / "tests").mkdir(parents=True)
    reqs = "\n".join(f"- **R{i}** requisito {i}" for i in range(1, NREQ[task] + 1))
    (ws / "REQUIREMENTS.md").write_text(f"# {task}\n\n{reqs}\n", encoding="utf-8")
    (ws / f"{mod}.py").write_text(f'"""Módulo da execução {n}."""\n\n\ndef f(x):\n    # decisão {n}: R1 em f\n    return x + {n}\n', encoding="utf-8")
    (ws / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (ws / "tests" / "test_public.py").write_text(
        f"import unittest\nfrom {mod} import f\n\n\nclass T(unittest.TestCase):\n    def test_r1_ok(self):\n        self.assertEqual(f(0), {n})\n\n\n"
        "if __name__ == '__main__':\n    unittest.main()\n", encoding="utf-8")
    if cond == "explicacao":
        msg = (f"## 1. Resumo da solução: o que foi alterado e onde.\n\n- Alterei [{mod}.py]({scratch}/{mod}.py).\n\n"
               "## 2. Premissas adotadas\n\n- premissa A\n\n## 5. Rastreabilidade\n\n| Requisito | Arquivo |\n|---|---|\n| R1 | f |\n")
    else:
        msg = f"Implementei em `{mod}.py` ({scratch}/{mod}.py).\n\nRan 1 test\nOK\n"
    (d / "final_message.md").write_text(msg, encoding="utf-8")
    (d / "workspace.diff").write_text(f"--- a/{mod}.py\n+++ b/{mod}.py\n@@ -1 +1 @@\n-x\n+    # decisão {n}: R1 em f\n", encoding="utf-8")
    events = [
        {"type": "thread.started", "thread_id": thread_id(n)},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"id": "item_0", "type": "agent_message", "text": f"lendo {scratch}"}},
        {"type": "item.completed", "item": {"id": "item_1", "type": "command_execution", "command": "pwd",
                                            "aggregated_output": scratch + "\n", "exit_code": 0, "status": "completed"}},
        {"type": "turn.completed", "usage": {"input_tokens": 1000 + n}},
    ]
    (d / "agent_events.jsonl").write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    (d / "prompt.txt").write_bytes(PROMPT[cond])
    (d / "prepare.json").write_text(json.dumps({"run_id": rid, "workspace_path": scratch}), encoding="utf-8")
    (d / "evaluation.json").write_text(json.dumps({
        "run_id": rid, "baseline_hash": BASELINE[task], "hidden_tests_passed": 5, "hidden_tests_total": 5}), encoding="utf-8")
    (d / "run_meta.json").write_text(json.dumps({
        "run_id": rid, "condition": cond, "exit_status": "completed", "model_passed": MODEL,
        "codex_version_reported": "codex-cli 0.0.1", "started_at": f"2026-10-02T06:{n:02d}:00+00:00",
        "duration_s": 10.0 + n, "prompt_sha256": hashlib.sha256(PROMPT[cond]).hexdigest()}), encoding="utf-8")
