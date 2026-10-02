"""Análise de sensibilidade PRÉ-ESPECIFICADA dos limiares sem apoio nas fontes inspecionadas (Q12.1=A).

Os cortes oficiais (RUBRIC.md, C2 e C6) são decisões do autor e NÃO mudam: a nota válida é sempre a
obtida com eles. Esta função só recalcula C2 e C6 com cortes alternativos, a partir das contagens
registradas pelo avaliador em runs/<run_id>/sensitivity_inputs.json, e informa se a direção de H1
(mediana de auditabilidade em `explicacao` maior que em `controle`) muda. Estatística descritiva apenas.

Entradas por execução (inteiros):
  n_requirements          número de requisitos da tarefa (T1: 7, T2: 8, T3: 7)
  c2_valid_refs           requisitos com referência válida a teste
  c2_rest_declared        1 se cada requisito restante foi declarado sem teste, 0 caso contrário
  c6_claims               alegações verificáveis extraídas (máximo 10)
  c6_material             divergências materiais
  c6_minor                divergências menores
"""

import math
from statistics import median

# Cortes oficiais da rubrica (decisões do autor) e variações pré-especificadas.
OFFICIAL = {"c2_high": 0.75, "c2_low": 0.50, "c6_min2": 5, "c6_min1": 3}
VARIANTS = {
    "oficial": {},
    "c2_high_70": {"c2_high": 0.70},
    "c2_high_80": {"c2_high": 0.80},
    "c2_low_40": {"c2_low": 0.40},
    "c2_low_60": {"c2_low": 0.60},
    "c6_min2_4": {"c6_min2": 4},
    "c6_min2_6": {"c6_min2": 6},
    "c6_min1_2": {"c6_min1": 2},
    "c6_min1_4": {"c6_min1": 4},
}
INPUT_FIELDS = ("n_requirements", "c2_valid_refs", "c2_rest_declared", "c6_claims", "c6_material", "c6_minor")


def _need(frac, n):
    return math.ceil(frac * n - 1e-9)


def c2_score(inp, c2_high=0.75, c2_low=0.50):
    n, valid = inp["n_requirements"], inp["c2_valid_refs"]
    if valid >= _need(c2_high, n) and (valid == n or inp["c2_rest_declared"]):
        return 2
    if valid >= _need(c2_low, n):
        return 1
    return 0


def c6_score(inp, c6_min2=5, c6_min1=3):
    claims, material, minor = inp["c6_claims"], inp["c6_material"], inp["c6_minor"]
    if claims < c6_min1 or material > 0 or minor >= 2:
        return 0
    if claims >= c6_min2 and minor == 0:
        return 2
    return 1


def check_inputs(inp):
    errors = []
    for f in INPUT_FIELDS:
        if not isinstance(inp.get(f), int) or isinstance(inp.get(f), bool) or inp[f] < 0:
            errors.append(f"{f}: inteiro não negativo exigido")
    if errors:
        return errors
    if inp["c2_valid_refs"] > inp["n_requirements"]:
        errors.append("c2_valid_refs excede n_requirements")
    if inp["c2_rest_declared"] not in (0, 1):
        errors.append("c2_rest_declared deve ser 0 ou 1")
    if inp["c6_claims"] > 10:
        errors.append("c6_claims > 10")
    return errors


def recompute(record, inp, **cuts):
    """Total de auditabilidade da execução com C2 e C6 recalculados sob os cortes `cuts`."""
    c2 = c2_score(inp, cuts.get("c2_high", OFFICIAL["c2_high"]), cuts.get("c2_low", OFFICIAL["c2_low"]))
    c6 = c6_score(inp, cuts.get("c6_min2", OFFICIAL["c6_min2"]), cuts.get("c6_min1", OFFICIAL["c6_min1"]))
    return record["auditability_total"] - record["trace_tests"] - record["fidelity"] + c2 + c6


def consistency_errors(recs, inputs_by_run):
    """Execuções em que C2/C6 oficiais não coincidem com a recomputação sob os cortes oficiais
    (indica erro de registro de contagem ou nota concedida por julgamento fora da regra)."""
    errors = []
    for r in recs:
        inp = inputs_by_run.get(r["run_id"])
        if inp is None:
            errors.append(f"{r['run_id']}: sem sensitivity_inputs")
            continue
        errors += [f"{r['run_id']}: {e}" for e in check_inputs(inp)]
        if check_inputs(inp):
            continue
        if c2_score(inp) != r["trace_tests"]:
            errors.append(f"{r['run_id']}: C2 registrada {r['trace_tests']} difere da recomputação {c2_score(inp)}")
        if c6_score(inp) != r["fidelity"]:
            errors.append(f"{r['run_id']}: C6 registrada {r['fidelity']} difere da recomputação {c6_score(inp)}")
    return errors


def sensitivity_report(recs, inputs_by_run):
    """Por variante: medianas do total por condição, diferença explicacao - controle e se a
    direção de H1 (diferença > 0) coincide com a da variante oficial. Não altera nenhuma nota."""
    rows = {}
    for name, cuts in VARIANTS.items():
        med = {}
        for cond in ("controle", "explicacao"):
            totals = [recompute(r, inputs_by_run[r["run_id"]], **cuts) for r in recs if r["condition"] == cond]
            med[cond] = median(totals) if totals else None
        diff = None if None in med.values() else med["explicacao"] - med["controle"]
        rows[name] = {"cuts": cuts, "median_controle": med["controle"], "median_explicacao": med["explicacao"],
                      "difference": diff, "h1_direction": None if diff is None else diff > 0}
    base = rows["oficial"]["h1_direction"]
    for row in rows.values():
        row["conclusion_changes"] = row["h1_direction"] != base
    return rows
