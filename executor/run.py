"""Orquestração de uma execução: prepare -> sessão `codex exec` -> captura -> diff -> avaliação."""

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from harness import cli as harness_cli, registry
from protocol import freeze as freeze_mod

from . import command, config, diffing, events, isolation, session

PROMPTS_DIR = registry.ROOT / "protocol" / "prompts"
PROTOCOL_DIR = registry.ROOT / "protocol"
SESSIONS_SUBDIR = "sessions"


class ExecutorError(RuntimeError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def prompt_bytes(condition):
    path = PROMPTS_DIR / f"{condition}.md"
    if not path.is_file():
        raise ExecutorError(f"prompt inexistente para a condição {condition!r}: {path}")
    return path.read_bytes()


def protocol_status(allow_unfrozen):
    """Execuções reais exigem protocolo congelado e íntegro, salvo `allow_unfrozen` (registrado)."""
    frozen = (PROTOCOL_DIR / "FREEZE.json").is_file()
    if frozen:
        diffs = freeze_mod.verify_freeze(PROTOCOL_DIR)
        if diffs:
            raise ExecutorError(f"protocolo congelado diverge de FREEZE.json: {diffs}")
    elif not allow_unfrozen:
        raise ExecutorError("protocolo não congelado (protocol/FREEZE.json ausente); "
                            "execuções reais só após TCC-020 (freeze). Use --allow-unfrozen apenas em ensaios.")
    return {"protocol_frozen": frozen, "allow_unfrozen_used": bool(allow_unfrozen and not frozen)}


def plan(task_id, condition, run_id, params, codex_bin, workspace_path, last_message_path):
    """Comando e prompt que seriam usados (sem executar nada)."""
    data = prompt_bytes(condition)
    argv = command.build_argv(codex_bin, workspace_path, last_message_path, params.model,
                              params.reasoning_effort)
    return {"run_id": run_id, "task_id": task_id, "condition": condition, "argv": argv,
            "stable_flags": command.stable_flags(argv), "prompt_sha256": sha256_bytes(data),
            "prompt_bytes": len(data), "timeout_s": params.timeout_s,
            "sandbox_mode": command.SANDBOX_MODE}


def _archive_previous(run_dir):
    k = 1
    while (run_dir.parent / "_excluded" / f"{run_dir.name}.attempt{k}").exists():
        k += 1
    dest = run_dir.parent / "_excluded" / f"{run_dir.name}.attempt{k}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(run_dir), str(dest))
    return dest


def run_one(task_id, condition, run_id, params, runs_dir, scratch_base, auth_file, codex_bin="codex",
            auth_mode="copy", pass_env=(), allow_unfrozen=False, archive_previous=False,
            keep_scratch=False, evaluate=True):
    runs_dir = Path(runs_dir)
    run_dir = runs_dir / run_id
    status = protocol_status(allow_unfrozen)
    if run_dir.exists():
        if (run_dir / "run_meta.json").exists() and not archive_previous:
            raise ExecutorError(f"{run_dir} já existe; arquivar com --archive-previous (log preservado em _excluded/)")
        if archive_previous:
            _archive_previous(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    layout = isolation.make_layout(scratch_base, run_id)
    secrets = isolation.secret_values(auth_file)
    meta = {"run_id": run_id, "task_id": task_id, "condition": condition, "finished": False,
            "attempt_started_at": now(), **status}
    try:
        harness_cli.prepare(task_id, run_id, layout["workspace"], runs_dir)
        initial = Path(tempfile.mkdtemp(prefix="initial-", dir=layout["base"]))
        shutil.rmtree(initial)
        shutil.copytree(layout["workspace"], initial)

        data = prompt_bytes(condition)
        (run_dir / "prompt.txt").write_bytes(data)
        prompt_hash = sha256_bytes(data)
        last_message = run_dir / "final_message.md"
        argv = command.build_argv(codex_bin, layout["workspace"], last_message, params.model,
                                  params.reasoning_effort)
        auth_installed = isolation.install_credentials(auth_file, layout["codex_home"], auth_mode)
        env = isolation.build_env(layout, pass_env)

        rc, out, err = session.codex_version(codex_bin, env)
        reported = out or err
        if rc != 0 or not reported:
            raise ExecutorError(f"`codex --version` falhou (rc={rc}): {reported!r}")
        if params.codex_version_expected and params.codex_version_expected not in reported:
            raise ExecutorError(f"versão do Codex divergente: esperada {params.codex_version_expected!r}, "
                                f"reportada {reported!r}")

        meta.update(
            prompt_path="prompt.txt", prompt_sha256=prompt_hash, prompt_bytes=len(data),
            codex_version_reported=reported, codex_bin=str(codex_bin),
            model_passed=params.model, reasoning_effort_passed=params.reasoning_effort,
            sandbox_mode=command.SANDBOX_MODE, command=argv, command_stdin="prompt.txt",
            flags_stable=command.stable_flags(argv), timeout_s=params.timeout_s,
            timeout_matches_protocol=params.timeout_s == config.PROTOCOL_TIMEOUT_S,
            config_path=params.config_path, auth_mode=auth_installed,
            env_keys=sorted(env), env_allowlist=list(isolation.DEFAULT_ENV_ALLOWLIST) + list(pass_env),
            codex_home="<descartável, apagado ao final>", scratch_workspace=str(layout["workspace"]),
            user_config_inherited=False, user_config_flags=["--ignore-user-config", "--ignore-rules"],
            started_at=now())
        (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

        res = session.run_session(argv, layout["workspace"], env, run_dir / "prompt.txt",
                                  run_dir / "agent_events.jsonl", run_dir / "stderr.txt", params.timeout_s)
        finished_at = now()
        if not last_message.exists():
            last_message.write_bytes(b"")
            meta["final_message_missing"] = True

        sessions = layout["codex_home"] / SESSIONS_SUBDIR
        if sessions.is_dir():
            shutil.copytree(sessions, run_dir / "codex_home_sessions")
        meta["codex_home_files_after"] = sorted(
            p.relative_to(layout["codex_home"]).as_posix() for p in layout["codex_home"].rglob("*")
            if p.name != isolation.AUTH_NAME)
        # credencial apagada antes de qualquer outra coisa
        isolation.destroy(layout["codex_home"])

        (run_dir / "workspace.diff").write_text(
            diffing.workspace_diff(initial, layout["workspace"]), encoding="utf-8")
        final_copy = run_dir / "workspace_final"
        shutil.copytree(layout["workspace"], final_copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

        if res["launch_error"]:
            exit_status = "unclassified_launch_error"
        elif res["timed_out"]:
            exit_status = "timeout"
        elif res["returncode"] == 0:
            exit_status = "completed"
        else:
            exit_status = "unclassified_nonzero_exit"  # agent_error x infra_failure exige evidência no log
        meta.update(finished_at=finished_at, duration_s=res["duration_s"], returncode=res["returncode"],
                    timed_out=res["timed_out"], launch_error=res["launch_error"], exit_status=exit_status,
                    classification_required=exit_status.startswith("unclassified"),
                    events_summary=events.summarize(run_dir / "agent_events.jsonl"),
                    stderr_bytes=(run_dir / "stderr.txt").stat().st_size,
                    final_message_bytes=last_message.stat().st_size)
        meta["evaluation_probe"] = oracle_probe(run_dir)

        if evaluate:
            try:
                ev = harness_cli.evaluate(task_id, run_id, layout["workspace"], runs_dir)
                meta["hidden_tests"] = f"{ev['hidden_tests_passed']}/{ev['hidden_tests_total']}"
                meta["public_tests"] = f"{ev['public_tests_passed']}/{ev['public_tests_total']}"
            except Exception as exc:  # defeito do harness: registrar, não esconder
                meta["evaluation_error"] = f"{type(exc).__name__}: {exc}"
        leaked = isolation.redact_secrets(run_dir, secrets)
        meta["secrets_redacted_in"] = leaked
        meta["finished"] = True
        return meta
    except Exception as exc:
        meta["executor_error"] = f"{type(exc).__name__}: {exc}"
        meta["exit_status"] = "unclassified_executor_error"
        raise
    finally:
        isolation.destroy(layout["codex_home"])
        (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        if not keep_scratch:
            isolation.destroy(layout["base"])


def oracle_probe(run_dir):
    """Indício (não prova) de acesso ao material de avaliação: procura marcadores nos logs brutos.

    O sandbox `workspace-write` restringe escrita; a leitura do restante do disco NÃO está provada
    como bloqueada (ver handoff). Este sinal só aponta menções a caminhos/marcadores.
    """
    needles = [str(registry.EVALUATION_DIR), "evaluation/", registry.EVALUATION_MARKER, "test_hidden"]
    hits = {}
    for name in ("agent_events.jsonl", "stderr.txt", "final_message.md", "workspace.diff"):
        text = (Path(run_dir) / name).read_text(encoding="utf-8", errors="replace")
        found = [n for n in needles if n in text]
        if found:
            hits[name] = found
    return {"suspected_evaluation_mentions": hits}


def load_manifest_runs(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return doc["runs"]
