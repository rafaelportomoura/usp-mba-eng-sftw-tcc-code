"""Execução de suítes unittest em subprocesso isolado, com timeout e resultado por arquivo.

Garantias:
- denominador estável: o total vem da enumeração estática da suíte oficial (``oracle_index``),
  nunca do que o código do agente permitiu carregar;
- o resultado trafega por arquivo (nonce + ``os._exit`` no coletor), não por stdout;
- timeout e término normal matam o grupo de processos inteiro (netos incluídos);
- testes públicos e ocultos rodam SEMPRE em cópia; o workspace do agente nunca é alterado;
- a suíte pública é a oficial (``tasks/<t>/public_tests``), sobrescrevendo ``tests/`` na cópia.
"""

import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from . import oracle_index, registry

_RUNNER = Path(__file__).resolve().parent / "unittest_json.py"
DEFAULT_TIMEOUT_S = 120


def _kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _empty(expected, status, details=()):
    return {"total": len(expected), "passed": 0, "failed": len(expected),
            "failed_tests": sorted(expected), "passed_tests": [], "not_run_tests": [],
            "unexpected_failures": [], "details": list(details), "status": status}


def _finalize(raw, expected):
    exp = set(expected)
    passed = sorted(set(raw["passed_tests"]) & exp)
    failed = sorted(exp - set(passed))
    unexpected = sorted((set(raw["failed_tests"]) | set(raw["not_run_tests"])) - exp)
    if raw.get("fatal") or raw["load_errors"]:
        status = "import_error"
    elif failed:
        status = "failed"
    else:
        status = "ok"
    details = list(raw["details"])
    if raw.get("fatal"):
        details.insert(0, raw["fatal"])
    return {"total": len(exp), "passed": len(passed), "failed": len(failed),
            "failed_tests": failed, "passed_tests": passed,
            "not_run_tests": sorted(set(raw["not_run_tests"]) & exp),
            "unexpected_failures": unexpected, "details": details, "status": status}


def _run(cwd, start, timeout, expected):
    """Roda ``start`` em ``cwd``; devolve resultado normalizado contra ``expected``."""
    expected = list(expected)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH="", PYTHONHASHSEED="0",
               PYTHONIOENCODING="utf-8")
    with tempfile.TemporaryDirectory(prefix="tcc-result-") as rdir:
        result_path = os.path.join(rdir, "result.json")
        nonce = secrets.token_hex(16)
        with open(os.path.join(rdir, "stdout"), "wb") as out, open(os.path.join(rdir, "stderr"), "wb") as err:
            proc = subprocess.Popen(
                [sys.executable, str(_RUNNER), start, ".", result_path, nonce],
                cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                start_new_session=True,
            )
            timed_out = False
            try:
                proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
            finally:
                _kill_group(proc)
                proc.wait()
        if timed_out:
            return _empty(expected, "timeout")
        stderr_tail = Path(rdir, "stderr").read_text(errors="replace")[-2000:]
        try:
            raw = json.loads(Path(result_path).read_text(encoding="utf-8"))
            if raw.get("nonce") != nonce:
                raise ValueError("nonce divergente")
            for key in ("passed_tests", "failed_tests", "not_run_tests", "load_errors", "details"):
                if not isinstance(raw[key], list):
                    raise ValueError(f"campo inválido: {key}")
        except (OSError, ValueError, KeyError) as exc:
            return _empty(expected, "runner_error", [f"{type(exc).__name__}: {exc}", stderr_tail])
        return _finalize(raw, expected)


def _copy(workspace, dest):
    shutil.copytree(workspace, dest, ignore=shutil.ignore_patterns("__pycache__"))


def run_public_tests(task_id, workspace, timeout=DEFAULT_TIMEOUT_S):
    """Roda os testes públicos OFICIAIS contra o código do workspace, em cópia temporária."""
    pub = registry.public_tests_dir(task_id)
    with tempfile.TemporaryDirectory(prefix="tcc-public-") as tmp:
        scratch = Path(tmp) / "ws"
        _copy(workspace, scratch)
        shutil.rmtree(scratch / "tests", ignore_errors=True)
        if (scratch / "tests").exists():
            (scratch / "tests").unlink()
        shutil.copytree(pub, scratch / "tests", ignore=shutil.ignore_patterns("__pycache__"))
        return _run(str(scratch), "tests", timeout, oracle_index.expected_tests(pub))


def run_hidden_tests(task_id, workspace, timeout=DEFAULT_TIMEOUT_S, oracle_dir=None):
    """Copia o workspace, injeta o oráculo em pacote de nome aleatório e o executa.

    O workspace original nunca recebe arquivos de avaliação; um ``tests_hidden/`` criado pelo
    agente é irrelevante (o pacote do oráculo tem nome aleatório).
    """
    oracle = Path(oracle_dir) if oracle_dir else registry.oracle_dir(task_id)
    pkg = "_oracle_" + secrets.token_hex(6)
    with tempfile.TemporaryDirectory(prefix="tcc-hidden-") as tmp:
        scratch = Path(tmp) / "ws"
        _copy(workspace, scratch)
        hidden = scratch / pkg
        hidden.mkdir()
        (hidden / "__init__.py").write_text("")
        for src in oracle.glob("*.py"):
            shutil.copy2(src, hidden / src.name)
        return _run(str(scratch), pkg, timeout, oracle_index.expected_tests(oracle))
