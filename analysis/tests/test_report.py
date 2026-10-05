import csv
import json
import tempfile
import unittest
from pathlib import Path

from analysis import report

TASKS = report.TASKS
HEAD = ["run_id", "task_id", "condition", "duration_s", "output_words", "hidden_tests_passed", "hidden_tests_total",
        "trace_code", "trace_tests", "assumptions", "risks", "rationale", "fidelity", "reproducibility",
        "auditability_total", "ap_decisions", "ap_risks", "ap_links", "rp_assumptions", "rp_risks", "rp_traces"]


def row(i, task, cond, total):
    base = dict(zip(HEAD, [f"R{i:02d}", task, cond, 10.0 + i, 20 + i, 5, 5, 0, 0, 0, 0, 0, 0, 0, total, 1, 0, 2, 0, 0, 0]))
    base["trace_code"] = total
    return base


class ReportCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.csv = Path(self.tmp.name) / "results.csv"
        rows, i = [], 0
        for t in TASKS:
            for c, vals in (("controle", (2, 3, 4)), ("explicacao", (10, 12, 14))):
                for v in vals:
                    i += 1
                    rows.append(row(i, t, c, v))
        for r in rows:
            d = Path(self.tmp.name) / "scoring" / r["run_id"]
            d.mkdir(parents=True)
            (d / "sensitivity_inputs.json").write_text(json.dumps(
                {"n_requirements": 7, "c2_valid_refs": 5, "c2_rest_declared": 0, "c6_claims": 5, "c6_material": 0, "c6_minor": 0}))
        with open(self.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=HEAD)
            w.writeheader()
            w.writerows(rows)

    def tearDown(self):
        self.tmp.cleanup()

    def test_medians_and_difference(self):
        rows = report.load(self.csv)
        s = report.summary([r for r in rows if r["condition"] == "controle"], "auditability_total")
        self.assertEqual((s["n"], s["mediana"], s["minimo"], s["maximo"]), (9, 3, 2, 4))
        d = {x["metrica"]: x for x in report.differences(rows)}
        self.assertEqual(d["auditability_total"]["diferenca"], 9)
        self.assertEqual(d["ap_points"]["diferenca"], 0)

    def test_sensitivity_table_has_all_variants(self):
        rows = report.load(self.csv)
        tab = report.sensitivity_table(rows, Path(self.tmp.name) / "scoring")
        self.assertEqual([x["variante"] for x in tab][0], "oficial")
        self.assertEqual(len(tab), 9)
        self.assertEqual(tab[0]["execucoes_com_total_alterado"] >= 0, True)

    def test_outputs_are_written_and_deterministic(self):
        out = Path(self.tmp.name) / "t"
        report.run(self.csv, out)
        first = {p.name: p.read_text() for p in out.iterdir()}
        self.assertEqual(set(first), {"descritiva_por_condicao.csv", "descritiva_por_tarefa_e_condicao.csv",
                                      "diferenca_explicacao_menos_controle.csv", "diferenca_por_tarefa.csv", "sensibilidade_c2_c6.csv",
                                      "tabelas.md", "grafico_auditabilidade.svg"})
        self.assertTrue(first["grafico_auditabilidade.svg"].startswith("<svg"))
        report.run(self.csv, out)
        self.assertEqual(first, {p.name: p.read_text() for p in out.iterdir()})


if __name__ == "__main__":
    unittest.main()
