"""Remoção de identificadores reveladores dos artefatos entregues ao avaliador (PROTOCOL.md, seção 12).

Cegamento parcial declarado: a estrutura do relatório continua revelando a condição, e o código revela a
tarefa. O que se remove é o que revelaria a ORDEM de execução, a repetição ou metadados do executor.
"""

import json
import re

WORKSPACE_PLACEHOLDER = "<WORKSPACE>"
OMITTED = "<omitido>"

# Caminho absoluto do workspace de scratch do executor (contém o run_id).
_WORKSPACE_RE = re.compile(r"(?:/[^/\s\"'`()\[\]\\<>]+)*/tcc-scratch/R\d{2}/workspace")

# Padrões que NÃO podem restar em nenhum arquivo de um pacote.
LEAK_PATTERNS = {
    "run_id": re.compile(r"\bR\d{2}\b"),
    "scratch": re.compile(r"tcc-scratch"),
    "caminho_home": re.compile(r"/home/"),
    "usuario": re.compile(r"rafaelportomoura"),
    "uuid": re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
    "carimbo_de_tempo": re.compile(r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"),
    "hash_sha256": re.compile(r"\b[0-9a-f]{64}\b"),
    "modelo": re.compile(r"gpt-\d", re.I),
    "ferramenta": re.compile(r"codex[- ]?cli", re.I),
    "repositorio": re.compile(r"usp-mba|runs/|protocol/|manifest"),
}


def sanitize_text(text):
    return _WORKSPACE_RE.sub(WORKSPACE_PLACEHOLDER, text)


def _walk(value):
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_walk(v) for v in value]
    if isinstance(value, dict):
        return {k: _walk(v) for k, v in value.items()}
    return value


def sanitize_event(event):
    """thread_id (UUIDv7, ordenado no tempo) e uso de tokens são removidos; caminhos são neutralizados."""
    if event.get("type") == "thread.started":
        return {"type": "thread.started", "thread_id": OMITTED}
    if event.get("type") == "turn.completed":
        return {"type": "turn.completed"}
    return _walk(event)


def sanitize_events_jsonl(text):
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        out.append(json.dumps(sanitize_event(json.loads(line)), ensure_ascii=False, separators=(",", ":")))
    return "\n".join(out) + "\n"


def scan_leaks(text, extra_forbidden=()):
    """Lista de (padrão, trecho) encontrados em `text`. Vazia = limpo."""
    found = []
    for name, rx in LEAK_PATTERNS.items():
        for m in rx.finditer(text):
            found.append((name, m.group(0)))
    for token in extra_forbidden:
        if token and token in text:
            found.append(("proibido", token))
    return found
