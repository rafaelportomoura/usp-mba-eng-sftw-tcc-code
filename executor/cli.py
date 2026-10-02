"""CLI do executor.

  python -m executor.cli dry-run  --config CFG --task T --condition C [--run-id R] [--codex-bin BIN]
  python -m executor.cli run      --config CFG --task T --condition C --run-id R --auth-file AUTH --scratch-dir DIR
  python -m executor.cli run-all  --config CFG --manifest protocol/manifest.json --auth-file AUTH --scratch-dir DIR [--only R01,R02]
  python -m executor.cli flags     (flags estáveis e comando-modelo para agent.flags / agent.invocation_command)

`--auth-file` é sempre explícito (não há padrão): o arquivo é copiado para um CODEX_HOME descartável fora
dos repositórios e apagado ao final. O dry-run não lê credenciais, não chama o Codex e não grava em runs/.
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

from harness import registry

from . import command, config, run as run_mod

INVOCATION_TEMPLATE = ("codex exec --json --output-last-message <last_message_file> --sandbox workspace-write "
                       "--cd <workspace> --model <model.name> -c model_reasoning_effort=<reasoning_effort> "
                       "--ignore-user-config --ignore-rules --skip-git-repo-check --color never - "
                       "(prompt via stdin; CODEX_HOME descartavel)")


def _common(p, need_run=True):
    p.add_argument("--config", required=True, help="execution_config.json (modelo e esforço obrigatórios)")
    p.add_argument("--codex-bin", default="codex")


def _run_args(p):
    p.add_argument("--auth-file", required=True)
    p.add_argument("--auth-mode", choices=("copy", "link"), default="copy")
    p.add_argument("--scratch-dir", required=True, help="base FORA dos repositórios")
    p.add_argument("--runs-dir", default=str(registry.RUNS_DIR))
    p.add_argument("--pass-env", action="append", default=[], metavar="NOME")
    p.add_argument("--allow-unfrozen", action="store_true", help="somente ensaios; fica registrado em run_meta")
    p.add_argument("--archive-previous", action="store_true")
    p.add_argument("--keep-scratch", action="store_true")


def main(argv=None):
    p = argparse.ArgumentParser(prog="executor")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dry-run")
    _common(d)
    d.add_argument("--task", required=True, choices=registry.task_ids())
    d.add_argument("--condition", required=True, choices=("controle", "explicacao"))
    d.add_argument("--run-id", default="DRY")
    r = sub.add_parser("run")
    _common(r)
    _run_args(r)
    r.add_argument("--task", required=True, choices=registry.task_ids())
    r.add_argument("--condition", required=True, choices=("controle", "explicacao"))
    r.add_argument("--run-id", required=True)
    a = sub.add_parser("run-all")
    _common(a)
    _run_args(a)
    a.add_argument("--manifest", required=True)
    a.add_argument("--only", default="", help="lista de run_id separada por vírgula")
    sub.add_parser("flags")
    args = p.parse_args(argv)

    if args.cmd == "flags":
        sample = command.build_argv("codex", "<workspace>", "<last_message_file>", "<model.name>",
                                    "<reasoning_effort>")
        print(json.dumps({"agent.flags": command.stable_flags(sample),
                          "agent.invocation_command": INVOCATION_TEMPLATE,
                          "agent.sandbox_mode": command.SANDBOX_MODE, "agent.interface": "cli"},
                         indent=2, ensure_ascii=False))
        return 0
    try:
        params = config.load(args.config)
        if args.cmd == "dry-run":
            with tempfile.TemporaryDirectory(prefix="tcc-dry-") as tmp:
                out = run_mod.plan(args.task, args.condition, args.run_id, params, args.codex_bin,
                                   Path(tmp) / "workspace", Path(tmp) / "final_message.md")
            out["note"] = "dry-run: nada foi executado, nenhuma credencial lida, nada gravado em runs/"
            print(json.dumps(out, indent=2, ensure_ascii=False))
            return 0
        kw = dict(params=params, runs_dir=args.runs_dir, scratch_base=args.scratch_dir,
                  auth_file=args.auth_file, codex_bin=args.codex_bin, auth_mode=args.auth_mode,
                  pass_env=tuple(args.pass_env), allow_unfrozen=args.allow_unfrozen,
                  archive_previous=args.archive_previous, keep_scratch=args.keep_scratch)
        if args.cmd == "run":
            meta = run_mod.run_one(args.task, args.condition, args.run_id, **kw)
            print(json.dumps({k: meta.get(k) for k in ("run_id", "exit_status", "duration_s", "hidden_tests",
                                                       "public_tests", "classification_required")}, indent=2))
            return 0
        runs = run_mod.load_manifest_runs(args.manifest)
        only = {x for x in args.only.split(",") if x}
        for item in runs:  # sequencial, na ordem do manifesto, sem reordenar; para no primeiro problema
            if only and item["run_id"] not in only:
                continue
            if (Path(args.runs_dir) / item["run_id"] / "run_meta.json").exists() and not args.archive_previous:
                print(f"{item['run_id']}: já executado; pulando", file=sys.stderr)
                continue
            meta = run_mod.run_one(item["task_id"], item["condition"], item["run_id"], **kw)
            print(f"{item['run_id']}: {meta['exit_status']}", flush=True)
            if meta["classification_required"]:
                print("parando: classificação humana necessária (agent_error x infra_failure)", file=sys.stderr)
                return 2
        return 0
    except (config.ConfigError, run_mod.ExecutorError, RuntimeError, ValueError, OSError) as exc:
        print(f"erro: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
