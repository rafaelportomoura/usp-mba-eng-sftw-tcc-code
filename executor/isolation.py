"""Isolamento do CODEX_HOME e do ambiente: nada do ~/.codex do usuário (MCP, hooks, plugins, memória) entra.

- Cada execução usa <scratch>/<run_id>/{codex_home,home,workspace}, FORA dos dois repositórios.
- Só o arquivo de credenciais é copiado (ou linkado) para o CODEX_HOME, com modo 0600, a partir de
  um caminho passado explicitamente. O CODEX_HOME é apagado ao final. Credenciais nunca vão a runs/.
- Ambiente do subprocesso por allowlist; HOME aponta para um diretório vazio descartável.
"""

import json
import os
import shutil
from pathlib import Path

from harness import registry, workspace as ws_mod

ACADEMIC_REPO = Path("/home/rafaelportomoura/Projects/personal/usp-mba-eng-sftw-tcc")
AUTH_NAME = "auth.json"
DEFAULT_ENV_ALLOWLIST = ("PATH", "LANG", "LC_ALL", "TERM")
MIN_SECRET_LEN = 16


class IsolationError(RuntimeError):
    pass


def assert_scratch_outside_repos(path):
    """O scratch não pode ficar dentro de nenhum dos dois repositórios nem de um repositório git."""
    resolved = Path(path).resolve()
    for repo in (registry.ROOT, ACADEMIC_REPO):
        if resolved == repo or repo in resolved.parents or resolved in repo.parents:
            raise IsolationError(f"scratch dentro de/contendo repositório do projeto: {repo}")
    ws_mod.assert_outside_repositories(resolved)  # qualquer ancestral com .git


def make_layout(scratch_base, run_id):
    base = Path(scratch_base).resolve() / run_id
    assert_scratch_outside_repos(base)
    if base.exists():
        raise IsolationError(f"scratch já existe: {base}")
    layout = {"base": base, "codex_home": base / "codex_home", "home": base / "home",
              "workspace": base / "workspace"}
    layout["codex_home"].mkdir(parents=True, mode=0o700)
    layout["home"].mkdir(mode=0o700)
    return layout


def install_credentials(auth_file, codex_home, mode="copy"):
    """Copia (ou linka) as credenciais para o CODEX_HOME descartável. Retorna o modo usado."""
    src = Path(auth_file).expanduser().resolve()
    if not src.is_file():
        raise IsolationError(f"arquivo de credenciais inexistente: {src}")
    for repo in (registry.ROOT, ACADEMIC_REPO):
        if repo in src.parents:
            raise IsolationError(f"credenciais dentro de repositório do projeto: {src}")
    dest = Path(codex_home) / AUTH_NAME
    if mode == "link":
        dest.symlink_to(src)
    elif mode == "copy":
        dest.write_bytes(src.read_bytes())
        os.chmod(dest, 0o600)
    else:
        raise IsolationError(f"modo de credencial inválido: {mode}")
    return mode


def build_env(layout, pass_env=()):
    env = {k: os.environ[k] for k in DEFAULT_ENV_ALLOWLIST if k in os.environ}
    for k in pass_env:
        if k in os.environ:
            env[k] = os.environ[k]
    env["CODEX_HOME"] = str(layout["codex_home"])
    env["HOME"] = str(layout["home"])
    env.setdefault("LANG", "C.UTF-8")
    return env


def secret_values(auth_file):
    """Valores string (>=16 caracteres) do arquivo de credenciais, para varredura de vazamento."""
    try:
        doc = json.loads(Path(auth_file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []

    def walk(v):
        if isinstance(v, str):
            if len(v) >= MIN_SECRET_LEN:
                out.append(v)
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
    walk(doc)
    return out


def redact_secrets(root, secrets):
    """Substitui qualquer segredo encontrado sob `root`; retorna os arquivos alterados (sem o valor)."""
    changed = []
    if not secrets:
        return changed
    for path in sorted(Path(root).rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        data = path.read_bytes()
        new = data
        for s in secrets:
            new = new.replace(s.encode(), b"[REDACTED]")
        if new != data:
            path.write_bytes(new)
            changed.append(path.relative_to(root).as_posix())
    return changed


def destroy(base):
    shutil.rmtree(base, ignore_errors=True)
