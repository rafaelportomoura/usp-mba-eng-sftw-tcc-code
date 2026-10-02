"""Manifesto de execução (rascunho): 18 execuções, fallback de 12 e plano de cegamento.

Determinístico: depende apenas da semente. Usa random.Random(semente) com embaralhamento
Fisher-Yates sobre `rng.random()`, cuja sequência é estável entre versões do Python
(random.shuffle e randrange já mudaram de implementação em versões anteriores).

Delineamento: aleatorização restrita por blocos.
  bloco A = repetições 1 e 2 de cada célula (12 execuções, embaralhadas entre si);
  bloco B = repetição 3 de cada célula (6 execuções, embaralhadas entre si).
O número da repetição segue a ordem cronológica de execução dentro da célula.
O bloco A sozinho é o fallback balanceado (2 repetições por célula) e é executado primeiro,
de modo que interromper após 12 execuções preserva o balanceamento.
"""

import json
import random
from itertools import product

SEED = 20261002
TASKS = ("t1_shipping", "t2_order_pricing", "t3_inventory_reservation")
CONDITIONS = ("controle", "explicacao")
REPLICATES = (1, 2, 3)
TIMEOUT_S = 720
REEVALUATION_N = 6
# Q12.2=B: a passagem 2 ocorre no mínimo 24 h depois da passagem 1 (fora do sprint de um dia).
MIN_REEVAL_INTERVAL_H = 24
LABEL_POOL = 24  # 18 avaliações + 6 reavaliações, todas com identificadores do mesmo formato

_BLOCK_A_REPLICATES = (1, 2)


def shuffle(items, rng):
    """Fisher-Yates determinístico sobre rng.random(); retorna nova lista."""
    out = list(items)
    for i in range(len(out) - 1, 0, -1):
        j = int(rng.random() * (i + 1))
        out[i], out[j] = out[j], out[i]
    return out


def cells():
    return list(product(TASKS, CONDITIONS))


def generate(seed=SEED):
    """Lista ordenada das 18 execuções (dicts); as 12 primeiras formam o fallback."""
    rng = random.Random(seed)
    block_a = [(t, c) for t, c, _ in product(TASKS, CONDITIONS, _BLOCK_A_REPLICATES)]
    block_b = [(t, c) for t, c, _ in product(TASKS, CONDITIONS, (3,))]
    runs = []
    seen = {}
    for block, group in (("A", shuffle(block_a, rng)), ("B", shuffle(block_b, rng))):
        for task_id, condition in group:
            # a repetição é numerada na ordem cronológica de execução dentro da célula
            replicate = seen[(task_id, condition)] = seen.get((task_id, condition), 0) + 1
            n = len(runs) + 1
            runs.append({
                "sequence": n,
                "run_id": f"R{n:02d}",
                "task_id": task_id,
                "condition": condition,
                "replicate": replicate,
                "block": block,
                "fallback": block == "A",
            })
    return runs


def fallback(runs):
    """Subconjunto balanceado de 12 execuções (2 por célula), preservando run_id e ordem."""
    return [r for r in runs if r["fallback"]]


def check_runs(runs, fallback_only=False):
    """Levanta ValueError se o conjunto não for o delineamento exigido."""
    expected_reps = _BLOCK_A_REPLICATES if fallback_only else REPLICATES
    if fallback_only:
        runs = [r for r in runs if r["fallback"]]
    if len(runs) != len(cells()) * len(expected_reps):
        raise ValueError(f"número de execuções inesperado: {len(runs)}")
    ids = [r["run_id"] for r in runs]
    if len(set(ids)) != len(ids):
        raise ValueError("run_id duplicado")
    seqs = [r["sequence"] for r in runs]
    if seqs != sorted(seqs):
        raise ValueError("sequência fora de ordem")
    for task_id, condition in cells():
        reps = sorted(r["replicate"] for r in runs
                      if r["task_id"] == task_id and r["condition"] == condition)
        if reps != list(expected_reps):
            raise ValueError(f"célula {task_id}/{condition} desbalanceada: {reps}")
    return True


def build_document(seed=SEED, execution_config=None):
    """Documento do manifesto. Rascunho: sem hashes e sem congelamento."""
    runs = generate(seed)
    check_runs(runs)
    check_runs(runs, fallback_only=True)
    return {
        "status": "DRAFT",
        "frozen": False,
        "protocol_version": None,
        "seed": seed,
        "design": "aleatorizacao restrita: bloco A (repeticoes 1-2, 12 execucoes) seguido do bloco B (repeticao 3, 6 execucoes)",
        "shuffle": "Fisher-Yates sobre random.Random(seed).random()",
        "timeout_s": TIMEOUT_S,
        "prompt_hashes": {c: None for c in CONDITIONS},
        "baseline_hashes": {t: None for t in TASKS},
        "execution_config": execution_config,
        "runs": runs,
        "fallback_run_ids": [r["run_id"] for r in fallback(runs)],
    }


def dumps(document):
    return json.dumps(document, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def blind_plan(runs, seed=SEED, reeval_n=REEVALUATION_N, eligible=None):
    """Plano de avaliação cega.

    - Identificadores neutros S01..S24 sorteados com random.Random(seed + 1); nenhum codifica
      tarefa, condição, repetição nem ordem de execução.
    - Passagem 1: todas as execuções elegíveis em ordem aleatória.
    - Passagem 2: reavaliação de `reeval_n` execuções, uma por célula (sorteada entre as elegíveis),
      com NOVOS identificadores e em ordem aleatória; deve ocorrer no mínimo MIN_REEVAL_INTERVAL_H (24 h) depois
      da passagem 1 (Q12.2=B); o intervalo é verificado em records.validate_reevaluation.
    `eligible`: conjunto de run_id realmente concluídos (padrão: todos).
    Retorna dict com pass1, pass2 (listas de {blind_id, run_id}, na ordem de apresentação)
    e key (blind_id -> run_id), que deve ficar fora do alcance do avaliador.
    """
    rng = random.Random(seed + 1)
    pool = [r for r in runs if eligible is None or r["run_id"] in eligible]
    if len(pool) + reeval_n > LABEL_POOL:
        raise ValueError("mais artefatos do que identificadores disponíveis")
    by_cell = {}
    for r in pool:
        by_cell.setdefault((r["task_id"], r["condition"]), []).append(r["run_id"])
    cell_keys = cells()
    if reeval_n != len(cell_keys):
        raise ValueError("a reavaliação seleciona exatamente uma execução por célula")
    chosen = []
    for key in cell_keys:
        options = by_cell.get(key)
        if not options:
            raise ValueError(f"sem execução elegível na célula {key}")
        chosen.append(options[int(rng.random() * len(options))])
    labels = shuffle([f"S{i:02d}" for i in range(1, LABEL_POOL + 1)], rng)
    order1 = shuffle([r["run_id"] for r in pool], rng)
    order2 = shuffle(chosen, rng)
    pass1 = [{"blind_id": labels[i], "run_id": rid} for i, rid in enumerate(order1)]
    pass2 = [{"blind_id": labels[len(order1) + i], "run_id": rid} for i, rid in enumerate(order2)]
    key = {e["blind_id"]: e["run_id"] for e in pass1 + pass2}
    return {"seed": seed + 1, "pass1": pass1, "pass2": pass2, "key": key}
