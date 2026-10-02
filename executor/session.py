"""Execução de um subprocesso em grupo próprio, com timeout e kill do grupo inteiro."""

import os
import signal
import subprocess
import time


def kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_session(argv, cwd, env, stdin_path, stdout_path, stderr_path, timeout_s):
    """Roda `argv`; stdin/stdout/stderr são arquivos (sem pipes, sem risco de bloqueio).

    Em qualquer desfecho o grupo de processos é morto (netos incluídos). Retorna dict com
    returncode, timed_out, duration_s, launch_error.
    """
    start = time.monotonic()
    with open(stdin_path, "rb") as fin, open(stdout_path, "wb") as fout, open(stderr_path, "wb") as ferr:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=fin, stdout=fout, stderr=ferr,
                                    start_new_session=True)
        except OSError as exc:
            return {"returncode": None, "timed_out": False, "launch_error": f"{type(exc).__name__}: {exc}",
                    "duration_s": round(time.monotonic() - start, 3)}
        timed_out = False
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            kill_group(proc)
            proc.wait()
    return {"returncode": None if timed_out else proc.returncode, "timed_out": timed_out,
            "launch_error": None, "duration_s": round(time.monotonic() - start, 3)}


def codex_version(codex_bin, env, timeout_s=30):
    """Saída bruta de `codex --version` (com o ambiente isolado)."""
    out = subprocess.run([str(codex_bin), "--version"], env=env, capture_output=True, text=True,
                         timeout=timeout_s, stdin=subprocess.DEVNULL)
    return out.returncode, out.stdout.strip(), out.stderr.strip()
