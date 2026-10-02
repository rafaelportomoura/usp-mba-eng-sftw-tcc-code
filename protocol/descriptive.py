"""Resumos DESCRITIVOS por condição para P1 (tipo de erro) e P2 (facilidade de revisão).

Sem testes de significância (PROTOCOL.md, seção 13). Funções puras sobre registros consolidados.
"""

from statistics import median

from . import taxonomy

CONDITIONS = ("controle", "explicacao")


def error_type_profile(recs):
    """Por condição e tipo: testes ocultos reprovados, execuções com ao menos uma falha do tipo
    e participação (0..1) no total de reprovações da condição (None se a condição não reprovou)."""
    out = {}
    for cond in CONDITIONS:
        rows = [r for r in recs if r["condition"] == cond]
        total = sum(r[taxonomy.err_field(t)] for r in rows for t in taxonomy.ERROR_TYPES)
        out[cond] = {"runs": len(rows), "failed_tests": total, "types": {}}
        for t in taxonomy.ERROR_TYPES:
            f = taxonomy.err_field(t)
            n = sum(r[f] for r in rows)
            out[cond]["types"][t] = {
                "tests": n,
                "runs_with": sum(1 for r in rows if r[f] > 0),
                "share": (n / total) if total else None,
            }
    return out


def claim_divergence_profile(recs):
    """Alegações divergentes por tipo, só na condição `explicacao` (no controle é sempre 0 por regra)."""
    rows = [r for r in recs if r["condition"] == "explicacao"]
    return {
        "claims_checked": sum(r["claims_checked"] for r in rows),
        "types": {t: sum(r[taxonomy.claim_field(t)] for r in rows) for t in taxonomy.CLAIM_TYPES},
    }


def review_points(record):
    return record["rp_assumptions"] + record["rp_risks"] + record["rp_traces"]


def review_fraction(record):
    """Fração de pontos de atenção que conferem; None (indefinida) quando não há pontos."""
    total = review_points(record)
    return None if total == 0 else record["rp_confirmed"] / total


def review_summary(recs):
    """Por condição: mediana de pontos e de confirmados (inclui os zeros) e fração entre execuções
    com ao menos um ponto. A fração NUNCA é imputada como 0 quando indefinida."""
    out = {}
    for cond in CONDITIONS:
        rows = [r for r in recs if r["condition"] == cond]
        fracs = [review_fraction(r) for r in rows if review_points(r) > 0]
        out[cond] = {
            "runs": len(rows),
            "runs_with_points": len(fracs),
            "median_points": median([review_points(r) for r in rows]) if rows else None,
            "median_confirmed": median([r["rp_confirmed"] for r in rows]) if rows else None,
            "median_fraction": median(fracs) if fracs else None,
            "pooled_fraction": (sum(r["rp_confirmed"] for r in rows if review_points(r) > 0)
                                / sum(review_points(r) for r in rows)) if fracs else None,
        }
    return out
