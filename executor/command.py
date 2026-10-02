"""Montagem da linha de comando do `codex exec`.

Somente flags confirmadas em `codex exec --help` (codex-cli 0.154.0):
  --json, -o/--output-last-message, -s/--sandbox, -C/--cd, -m/--model, -c key=value,
  --ignore-user-config, --ignore-rules, --skip-git-repo-check, --color.
O prompt vai por stdin (argumento posicional `-`), pois `--help` documenta que `-` lê as instruções do stdin.
Nenhum segredo trafega em argv.
"""

import json

SANDBOX_MODE = "workspace-write"


def build_argv(codex_bin, workspace, last_message_path, model, reasoning_effort):
    return [
        str(codex_bin), "exec",
        "--json",
        "--output-last-message", str(last_message_path),
        "--sandbox", SANDBOX_MODE,
        "--cd", str(workspace),
        "--model", model,
        "-c", f"model_reasoning_effort={json.dumps(reasoning_effort)}",  # valor TOML: string entre aspas
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",  # o workspace fica fora de qualquer repositório git (exigência do harness)
        "--color", "never",
        "-",
    ]


def stable_flags(argv):
    """Flags sem caminhos específicos da execução (para agent.flags do execution_config)."""
    out = []
    skip = False
    for i, a in enumerate(argv[2:], start=2):
        if skip:
            skip = False
            continue
        if a in ("--output-last-message", "--cd"):
            out.append(f"{a} <{'last_message_file' if a.startswith('--o') else 'workspace'}>")
            skip = True
        elif a in ("--model",):
            out.append(f"--model <model.name>")
            skip = True
        elif a == "-c":
            out.append("-c model_reasoning_effort=<generation_parameters.reasoning_effort>")
            skip = True
        elif a == "-":
            out.append("- (prompt via stdin)")
        elif a in ("--sandbox", "--color"):
            out.append(f"{a} {argv[i + 1]}")
            skip = True
        else:
            out.append(a)
    return out
