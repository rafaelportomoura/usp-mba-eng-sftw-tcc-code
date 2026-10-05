"""Estatística descritiva, tabelas e gráfico do TCC (TCC-070).

Uso: python3 -m analysis.report [--results results/results.csv] [--out results/tables]
Lê o CSV consolidado e grava tabelas (CSV e Markdown) e um gráfico SVG. Só mediana, mínimo e
máximo; não há teste de significância (EXPERIMENT.md/TASKS.md, TCC-070).
"""
import argparse
import csv
import json
import statistics
from pathlib import Path

from protocol import sensitivity

ROOT = Path(__file__).resolve().parent.parent
CONDITIONS = ("controle", "explicacao")
TASKS = ("t1_shipping", "t2_order_pricing", "t3_inventory_reservation")
CRITERIA = ("trace_code", "trace_tests", "assumptions", "risks", "rationale", "fidelity", "reproducibility")
METRICS = ("auditability_total",) + CRITERIA + ("ap_points", "rp_points", "output_words", "duration_s", "hidden_pass_rate")
COLORS = {"controle": "#5b6c8f", "explicacao": "#d9822b"}


def load(path):
    rows = list(csv.DictReader(Path(path).read_text(encoding="utf-8").splitlines()))
    for r in rows:
        for c in CRITERIA + ("auditability_total", "output_words", "ap_decisions", "ap_risks", "ap_links",
                             "rp_assumptions", "rp_risks", "rp_traces", "hidden_tests_passed", "hidden_tests_total"):
            r[c] = int(r[c])
        r["duration_s"] = float(r["duration_s"])
        r["ap_points"] = r["ap_decisions"] + r["ap_risks"] + r["ap_links"]
        r["rp_points"] = r["rp_assumptions"] + r["rp_risks"] + r["rp_traces"]
        r["hidden_pass_rate"] = r["hidden_tests_passed"] / r["hidden_tests_total"]
    return rows


def summary(rows, metric):
    v = [r[metric] for r in rows]
    return {"n": len(v), "mediana": statistics.median(v), "minimo": min(v), "maximo": max(v)}


def table(rows, group_keys):
    """Uma linha por grupo e métrica: n, mediana, mínimo e máximo."""
    out = []
    groups = sorted({tuple(r[k] for k in group_keys) for r in rows})
    for g in groups:
        sub = [r for r in rows if tuple(r[k] for k in group_keys) == g]
        for m in METRICS:
            out.append({**dict(zip(group_keys, g)), "metrica": m, **summary(sub, m)})
    return out


def differences(rows, by_task=False):
    """Diferença das medianas explicacao - controle por métrica (e por tarefa, se pedido)."""
    out = []
    scopes = [(t, [r for r in rows if r["task_id"] == t]) for t in TASKS] if by_task else [("todas", rows)]
    for name, sub in scopes:
        for m in METRICS:
            a = [r[m] for r in sub if r["condition"] == "explicacao"]
            b = [r[m] for r in sub if r["condition"] == "controle"]
            if a and b:
                out.append({"escopo": name, "metrica": m, "mediana_explicacao": statistics.median(a),
                            "mediana_controle": statistics.median(b),
                            "diferenca": round(statistics.median(a) - statistics.median(b), 4)})
    return out


def sensitivity_table(rows, scoring):
    """Sensibilidade pré-especificada de C2 e C6 (protocol/sensitivity.py); não altera nenhuma nota."""
    inputs = {r["run_id"]: json.loads((Path(scoring) / r["run_id"] / "sensitivity_inputs.json").read_text(encoding="utf-8"))
              for r in rows}
    rep = sensitivity.sensitivity_report(rows, inputs)
    out = []
    for name, v in rep.items():
        cuts = v["cuts"]
        changed = sum(sensitivity.recompute(r, inputs[r["run_id"]], **cuts) != r["auditability_total"] for r in rows)
        out.append({"variante": name, "cortes": json.dumps(cuts) if cuts else "oficiais",
                    "mediana_controle": v["median_controle"], "mediana_explicacao": v["median_explicacao"],
                    "diferenca": v["difference"], "execucoes_com_total_alterado": changed,
                    "direcao_de_H1_muda": v["conclusion_changes"]})
    return out


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def markdown(rows, title):
    cols = list(rows[0])
    lines = [f"### {title}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += ["| " + " | ".join(str(r[c]) for c in cols) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def svg(rows):
    """Pontos de auditability_total (0-14) por tarefa e condição, com a mediana em traço."""
    w, h, left, top, bottom = 760, 380, 56, 50, 50
    pw = (w - left - 20) / len(TASKS)
    ph = h - top - bottom
    y = lambda v: top + ph * (1 - v / 14)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="12">',
         f'<rect width="{w}" height="{h}" fill="#ffffff"/>',
         f'<text x="{w / 2}" y="22" text-anchor="middle" font-size="14" font-weight="bold">Escore de auditabilidade (0 a 14) por tarefa e condição</text>']
    for v in range(0, 15, 2):
        p.append(f'<line x1="{left}" x2="{w - 20}" y1="{y(v)}" y2="{y(v)}" stroke="#e3e3dd"/>'
                 f'<text x="{left - 8}" y="{y(v) + 4}" text-anchor="end">{v}</text>')
    for i, t in enumerate(TASKS):
        x0 = left + i * pw
        p.append(f'<text x="{x0 + pw / 2}" y="{h - 14}" text-anchor="middle" font-weight="bold">{t}</text>')
        for j, c in enumerate(CONDITIONS):
            cx = x0 + pw * (0.3 + 0.4 * j)
            vals = sorted(r["auditability_total"] for r in rows if r["task_id"] == t and r["condition"] == c)
            for k, v in enumerate(vals):
                p.append(f'<circle cx="{cx + (k - (len(vals) - 1) / 2) * 14}" cy="{y(v)}" r="5" fill="{COLORS[c]}" fill-opacity="0.85"/>')
            if vals:
                m = statistics.median(vals)
                p.append(f'<line x1="{cx - 28}" x2="{cx + 28}" y1="{y(m)}" y2="{y(m)}" stroke="{COLORS[c]}" stroke-width="2.5"/>'
                         f'<text x="{cx}" y="{h - 42}" text-anchor="middle" fill="{COLORS[c]}">{c}</text>'
                         f'<text x="{cx}" y="{h - 29}" text-anchor="middle" fill="{COLORS[c]}">mediana {m:g}</text>')
    p.append("</svg>")
    return "\n".join(p) + "\n"


def run(results, out):
    rows = load(results)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    tabs = {"descritiva_por_condicao": table(rows, ["condition"]),
            "descritiva_por_tarefa_e_condicao": table(rows, ["task_id", "condition"]),
            "diferenca_explicacao_menos_controle": differences(rows),
            "diferenca_por_tarefa": differences(rows, by_task=True),
            "sensibilidade_c2_c6": sensitivity_table(rows, Path(results).parent / "scoring")}
    md = ["# Tabelas descritivas (geradas por `python3 -m analysis.report`)\n",
          f"Fonte: `{Path(results).name}`, {len(rows)} execuções. Mediana, mínimo e máximo; sem teste de significância.\n"]
    for name, t in tabs.items():
        write_csv(out / f"{name}.csv", t)
        md.append(markdown(t, name.replace("_", " ")))
    (out / "tabelas.md").write_text("\n".join(md), encoding="utf-8")
    (out / "grafico_auditabilidade.svg").write_text(svg(rows), encoding="utf-8")
    return tabs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--results", default=str(ROOT / "results" / "results.csv"))
    ap.add_argument("--out", default=str(ROOT / "results" / "tables"))
    a = ap.parse_args(argv)
    tabs = run(a.results, a.out)
    print(f"OK: {len(tabs)} tabelas e 1 gráfico em {a.out}")


if __name__ == "__main__":
    main()
