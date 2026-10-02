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


def attention_points(record):
    """Q06: pontos de atenção do artefato (visão sem relatório estruturado), mesma regra nas duas condições."""
    return record["ap_decisions"] + record["ap_risks"] + record["ap_links"]


def attention_fraction(record):
    """Fração dos pontos do artefato que conferem; None (indefinida) quando não há pontos."""
    total = attention_points(record)
    return None if total == 0 else record["ap_confirmed"] / total


def attention_summary(recs):
    """Q06, por condição: medianas (incluindo zeros) de pontos, por tipo, confirmados e vindos do resumo livre;
    fração que confere entre execuções com ao menos um ponto (nunca imputada como 0).
    O campo `median_points_without_summary` mostra o que sobra quando o resumo livre é desconsiderado."""
    out = {}
    for cond in CONDITIONS:
        rows = [r for r in recs if r["condition"] == cond]
        fracs = [attention_fraction(r) for r in rows if attention_points(r) > 0]
        out[cond] = {
            "runs": len(rows),
            "runs_with_points": len(fracs),
            "median_points": median([attention_points(r) for r in rows]) if rows else None,
            "median_decisions": median([r["ap_decisions"] for r in rows]) if rows else None,
            "median_risks": median([r["ap_risks"] for r in rows]) if rows else None,
            "median_links": median([r["ap_links"] for r in rows]) if rows else None,
            "median_confirmed": median([r["ap_confirmed"] for r in rows]) if rows else None,
            "median_from_summary": median([r["ap_from_summary"] for r in rows]) if rows else None,
            "median_points_without_summary": (
                median([attention_points(r) - r["ap_from_summary"] for r in rows]) if rows else None),
            "median_fraction": median(fracs) if fracs else None,
            "pooled_fraction": (sum(r["ap_confirmed"] for r in rows if attention_points(r) > 0)
                                / sum(attention_points(r) for r in rows)) if fracs else None,
        }
    return out


def attention_difference(recs):
    """Q06: diferença descritiva explicacao - controle nas medianas de pontos do artefato (sem inferência).
    None se faltar alguma condição."""
    s = attention_summary(recs)
    if not s["controle"]["runs"] or not s["explicacao"]["runs"]:
        return None
    return {"median_points": s["explicacao"]["median_points"] - s["controle"]["median_points"],
            "median_confirmed": s["explicacao"]["median_confirmed"] - s["controle"]["median_confirmed"]}


def reevaluation_summary(rows):
    """Q12.2=B: reavaliação intra-avaliador, por critério, sobre os artefatos com as duas passagens.

    Relata (não só a concordância exata, Baltes et al., 2025, p. 38): distribuição das notas 0/1/2 em cada
    passagem, matriz passagem 1 x passagem 2 (3x3), concordância exata e diferença absoluta média; e, para
    o total, a diferença absoluta média. Nenhuma estatística de concordância ordinal (n = 6). `intervals_h`
    traz o intervalo em horas entre as passagens de cada artefato.
    """
    from . import records

    p1 = {r["run_id"]: r for r in rows if r["pass"] == 1}
    pairs = [(p1[r["run_id"]], r) for r in rows if r["pass"] == 2 and r["run_id"] in p1]
    out = {"pairs": len(pairs), "criteria": {}, "intervals_h": {}}
    for a, b in pairs:
        gap = records.parse_timestamp(b["scored_at"]) - records.parse_timestamp(a["scored_at"])
        out["intervals_h"][a["run_id"]] = round(gap.total_seconds() / 3600, 2)
    for f in records.SCORE_FIELDS:
        matrix = [[0, 0, 0] for _ in range(3)]
        for a, b in pairs:
            matrix[a[f]][b[f]] += 1
        out["criteria"][f] = {
            "distribution_pass1": [sum(matrix[i]) for i in range(3)],
            "distribution_pass2": [sum(matrix[j][i] for j in range(3)) for i in range(3)],
            "matrix_pass1_rows_pass2_cols": matrix,
            "exact_agreement": (sum(matrix[i][i] for i in range(3)) / len(pairs)) if pairs else None,
            "mean_abs_difference": (sum(abs(a[f] - b[f]) for a, b in pairs) / len(pairs)) if pairs else None,
        }
    out["total_mean_abs_difference"] = (
        sum(abs(a["auditability_total"] - b["auditability_total"]) for a, b in pairs) / len(pairs)) if pairs else None
    return out
