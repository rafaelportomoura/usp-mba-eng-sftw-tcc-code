"""Geração de workspaces isolados e verificação de vazamento de oráculos."""

import hashlib
import json
import shutil
from pathlib import Path

from . import registry

FORBIDDEN_PARTS = {"evaluation", "oracle", "reference", "tests_hidden"}
IGNORED = {"__pycache__"}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree_files(root):
    root = Path(root)
    return sorted(
        p for p in root.rglob("*")
        if p.is_file() and not (set(p.relative_to(root).parts) & IGNORED)
    )


def tree_hash(root):
    """Hash determinístico (caminho relativo + conteúdo) de uma árvore de arquivos."""
    root = Path(root)
    digest = hashlib.sha256()
    for path in tree_files(root):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def requirements_hash(task_id):
    return sha256_file(registry.task_dir(task_id) / "REQUIREMENTS.md")


def public_tests_hash(task_id):
    return tree_hash(registry.public_tests_dir(task_id))


def oracle_hash(task_id):
    """Hash agregado do oráculo (não expõe conteúdo)."""
    return tree_hash(registry.oracle_dir(task_id))


def evaluation_bundle_hash(task_id=None):
    """Hash agregado de TODO o material de avaliação (oráculo, referências, alternativas, mutantes,
    RISKS.md, baseline_expectations.json). Sem ``task_id``, cobre todas as tarefas. Não expõe conteúdo."""
    return tree_hash(registry.evaluation_dir(task_id) if task_id else registry.EVALUATION_DIR)


def harness_hash():
    """Hash do código do harness (exclui seus testes)."""
    root = registry.ROOT / "harness"
    digest = hashlib.sha256()
    for path in tree_files(root):
        rel = path.relative_to(root)
        if rel.parts[0] == "tests":
            continue
        digest.update(rel.as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def baseline_hash(task_id):
    return tree_hash(registry.task_dir(task_id) / "baseline")


def evaluation_hashes():
    """Hashes de todos os arquivos não vazios do diretório de avaliação."""
    hashes = {}
    for path in tree_files(registry.EVALUATION_DIR):
        if path.stat().st_size > 0:
            hashes[sha256_file(path)] = path.relative_to(registry.ROOT).as_posix()
    return hashes


def find_leaks(workspace):
    """Retorna a lista de motivos pelos quais o workspace vazaria material de avaliação."""
    workspace = Path(workspace)
    forbidden_hashes = evaluation_hashes()
    leaks = []
    for path in tree_files(workspace):
        rel = path.relative_to(workspace)
        if set(rel.parts) & FORBIDDEN_PARTS:
            leaks.append(f"{rel}: caminho proibido")
        digest = sha256_file(path)
        if digest in forbidden_hashes:
            leaks.append(f"{rel}: conteúdo idêntico a {forbidden_hashes[digest]}")
        if registry.EVALUATION_MARKER.encode() in path.read_bytes():
            leaks.append(f"{rel}: contém marcador {registry.EVALUATION_MARKER}")
    return leaks


def assert_no_leak(workspace):
    leaks = find_leaks(workspace)
    if leaks:
        raise RuntimeError("vazamento detectado: " + "; ".join(leaks))


def assert_outside_repositories(dest):
    """O workspace não pode ficar dentro de repositório git (ex.: este), pois `../..` alcançaria evaluation/."""
    resolved = Path(dest).resolve()
    for candidate in (resolved, *resolved.parents):
        if candidate == registry.ROOT or (candidate / ".git").exists():
            raise ValueError(f"destino dentro de repositório ({candidate}); use um diretório fora (ex.: /tmp)")
    if registry.ROOT.is_relative_to(resolved):
        raise ValueError("destino contém o repositório experimental")


def build_workspace(task_id, dest):
    """Cria o workspace contendo SOMENTE baseline, requisitos e testes públicos.

    Retorna o manifesto (não gravado no workspace).
    """
    tdir = registry.task_dir(task_id)
    dest = Path(dest).resolve()
    assert_outside_repositories(dest)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"destino não vazio: {dest}")
    dest.mkdir(parents=True, exist_ok=True)
    ignore = shutil.ignore_patterns("__pycache__")
    shutil.copytree(tdir / "baseline", dest, dirs_exist_ok=True, ignore=ignore)
    shutil.copy2(tdir / "REQUIREMENTS.md", dest / "REQUIREMENTS.md")
    shutil.copytree(tdir / "public_tests", dest / "tests", ignore=ignore)
    assert_no_leak(dest)
    files = {p.relative_to(dest).as_posix(): sha256_file(p) for p in tree_files(dest)}
    return {
        "task_id": task_id,
        "baseline_hash": baseline_hash(task_id),
        "workspace_hash": tree_hash(dest),
        "files": files,
    }


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
