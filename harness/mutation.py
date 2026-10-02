"""Regressão de mutação do oráculo.

Para cada tarefa, ``evaluation/<t>/alternatives/*.py`` são soluções CORRETAS alternativas (devem passar
100% dos testes públicos e ocultos) e ``evaluation/<t>/mutants/*.py`` são mutantes (devem ser
reprovados por pelo menos um teste oculto). Cada arquivo substitui o módulo da tarefa no workspace.
"""

import shutil
import tempfile
from pathlib import Path

from . import registry, runner, workspace


def _variants(task_id, kind):
    return sorted((registry.evaluation_dir(task_id) / kind).glob("*.py"))


def run_variant(task_id, path):
    module = registry.TASKS[task_id]["module"]
    with tempfile.TemporaryDirectory(prefix="tcc-mut-") as tmp:
        ws = Path(tmp) / "ws"
        workspace.build_workspace(task_id, ws)
        shutil.copy2(path, ws / module)
        return runner.run_public_tests(task_id, ws), runner.run_hidden_tests(task_id, ws)


def check(task_id):
    """Retorna (ok, relatório) para as alternativas e os mutantes de uma tarefa."""
    survivors, rejected, report = [], [], {"alternatives": {}, "mutants": {}}
    for path in _variants(task_id, "alternatives"):
        pub, hid = run_variant(task_id, path)
        good = pub["status"] == "ok" and hid["status"] == "ok"
        report["alternatives"][path.name] = f"public {pub['passed']}/{pub['total']}, hidden {hid['passed']}/{hid['total']}"
        if not good:
            rejected.append(path.name)
    for path in _variants(task_id, "mutants"):
        pub, hid = run_variant(task_id, path)
        killed = hid["failed"] > 0
        report["mutants"][path.name] = f"hidden {hid['passed']}/{hid['total']}" + ("" if killed else " SOBREVIVEU")
        if not killed:
            survivors.append(path.name)
    report["correct_alternatives_rejected"] = rejected
    report["surviving_mutants"] = survivors
    return not rejected and not survivors, report
