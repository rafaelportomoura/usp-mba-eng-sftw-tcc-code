"""Gerador de `codex` falso (stub) para testes. NÃO é o Codex: imita só a superfície usada pelo executor.

Os eventos JSONL emitidos são SINTÉTICOS (formato inventado para teste; não representam os eventos reais).
"""

import os
import stat
import sys
import textwrap

TEMPLATE = r'''#!{python}
import json, os, subprocess, sys, time
CFG = {cfg!r}
if sys.argv[1:] == ["--version"]:
    print(CFG.get("version", "codex-cli 0.154.0"))
    sys.exit(0)
argv = sys.argv[1:]
stdin = sys.stdin.buffer.read()
def opt(name):
    return argv[argv.index(name) + 1]
ws = opt("--cd")
home = os.environ.get("CODEX_HOME", "")
record = dict(argv=argv, cwd=os.getcwd(), env=dict(os.environ), stdin_hex=stdin.hex(),
              codex_home_files=sorted(os.listdir(home)) if home and os.path.isdir(home) else None,
              auth_mode=oct(os.stat(os.path.join(home, "auth.json")).st_mode & 0o777)
                        if home and os.path.exists(os.path.join(home, "auth.json")) else None)
open(CFG["record"], "w").write(json.dumps(record))
mode = CFG["mode"]
print(json.dumps({{"synthetic": True, "type": "synthetic.start"}}), flush=True)
print("linha que nao e json", flush=True)
if mode == "hang":
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    open(CFG["pidfile"], "w").write(str(p.pid))
    time.sleep(600)
if mode == "leak":
    print(json.dumps({{"synthetic": True, "token": CFG["secret"]}}), flush=True)
    sys.stderr.write("erro com " + CFG["secret"] + "\n")
if mode == "peek":
    print(json.dumps({{"synthetic": True, "cmd": "cat /x/evaluation/t1_shipping/oracle/test_hidden.py"}}))
if mode in ("ok", "leak", "peek", "fail"):
    mod = os.path.join(ws, "shipping.py")
    with open(mod, "a") as fh:
        fh.write("\n# alterado pelo stub\n")
    os.makedirs(os.path.join(home, "sessions"), exist_ok=True)
    open(os.path.join(home, "sessions", "rollout-synthetic.jsonl"), "w").write("{{}}\n")
    open(opt("--output-last-message"), "w").write("mensagem final sintetica")
if mode == "fail":
    sys.exit(3)
'''


def make_stub(path, **cfg):
    cfg.setdefault("mode", "ok")
    with open(path, "w") as fh:
        fh.write(TEMPLATE.format(python=sys.executable, cfg=cfg))
    os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    return path
