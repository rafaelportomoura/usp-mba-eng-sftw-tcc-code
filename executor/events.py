"""Leitura tolerante de agent_events.jsonl.

Não presume esquema: o arquivo bruto é a fonte. A função só conta linhas e relata a distribuição do
valor do campo de topo `type` QUANDO existir (observação genérica, sem interpretar eventos).
"""

import json
from collections import Counter


def summarize(path):
    lines = invalid = blank = 0
    non_object = 0
    types = Counter()
    keys = Counter()
    with open(path, "rb") as fh:
        for raw in fh:
            if not raw.strip():
                blank += 1
                continue
            lines += 1
            try:
                obj = json.loads(raw.decode("utf-8", errors="replace"))
            except ValueError:
                invalid += 1
                continue
            if not isinstance(obj, dict):
                non_object += 1
                continue
            keys.update(obj.keys())
            t = obj.get("type")
            if isinstance(t, str):
                types[t] += 1
    return {"lines": lines, "blank_lines": blank, "invalid_json_lines": invalid,
            "non_object_lines": non_object, "top_level_keys": dict(sorted(keys.items())),
            "top_level_type_counts": dict(sorted(types.items()))}
