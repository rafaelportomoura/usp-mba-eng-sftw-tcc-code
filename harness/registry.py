"""Registro das tarefas e caminhos canônicos do repositório experimental."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "tasks"
EVALUATION_DIR = ROOT / "evaluation"
RUNS_DIR = ROOT / "runs"
PYTHON_VERSION_FILE = ROOT / ".python-version"

# Marcador presente em todo arquivo exclusivo de avaliação (oráculos, soluções, riscos).
EVALUATION_MARKER = "EVALUATION-ONLY"

TASKS = {
    "t1_shipping": {"level": "baixa", "module": "shipping.py"},
    "t2_order_pricing": {"level": "media", "module": "pricing.py"},
    "t3_inventory_reservation": {"level": "alta", "module": "inventory.py"},
}


def task_ids():
    return list(TASKS)


def task_dir(task_id):
    _check(task_id)
    return TASKS_DIR / task_id


def evaluation_dir(task_id):
    _check(task_id)
    return EVALUATION_DIR / task_id


def _check(task_id):
    if task_id not in TASKS:
        raise KeyError(f"unknown task: {task_id!r}")


def public_tests_dir(task_id):
    return task_dir(task_id) / "public_tests"


def oracle_dir(task_id):
    return evaluation_dir(task_id) / "oracle"


def pinned_python():
    """Versão de Python fixada em .python-version (ex.: '3.14.7')."""
    return PYTHON_VERSION_FILE.read_text().strip()
