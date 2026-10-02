import contextlib
import csv
import io
import re
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from protocol import records

from analysis import cli, sheets
from analysis.tests import fixtures

T0 = datetime(2026, 10, 5, 9, 0, 0, tzinfo=timezone(timedelta(hours=-3)))
ZERO = {c: "0" for c in sheets.PASS1_COLS if c not in ("blind_id", "scored_at", "auditability_total", "notes")
        and c not in sheets.ERR_FIELDS}


class CliCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        fixtures.make_code_root(base / "code")
        self.clock = [T0]
        self.ctx = cli.Ctx(results=base / "results", code_root=base / "code", now=lambda: self.clock[0])
        self.assertEqual(self.run_cli(["build-packs"])[0], 0)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(argv, self.ctx)
        return code, out.getvalue(), err.getvalue()

    def ids(self, passage):
        return [r["blind_id"] for r in self.ctx.load(passage)]

    def fill1(self, bid, **extra):
        fields = dict(ZERO, **extra)
        return self.run_cli(["set", "--pass", "1", bid] + [f"{k}={v}" for k, v in fields.items()])

    def fill_all_pass1(self):
        for bid in self.ids(1):
            code, _, err = self.fill1(bid)
            self.assertEqual(code, 0, err)


class TestSheets(CliCase):
    def test_columns_and_blindness(self):
        header = (self.ctx.results / "fichas" / "passagem1.csv").read_text().splitlines()[0].split(",")
        for c in list(records.SCORE_FIELDS) + list(records.RP_FIELDS) + list(records.AP_FIELDS) + list(records.ERR_FIELDS) \
                + list(records.CLAIM_FIELDS) + ["claims_checked", "rp_confirmed", "ap_confirmed", "ap_from_summary",
                                                "scored_at", "auditability_total", "c2_valid_refs", "c6_claims", "notes"]:
            self.assertIn(c, header)
        for c in ("run_id", "condition", "task_id", "duration_s", "hidden_tests_passed", "prompt_hash", "model"):
            self.assertNotIn(c, header)
        for p in (self.ctx.results / "fichas").glob("*.csv"):
            self.assertIsNone(re.search(r"\bR\d{2}\b", p.read_text()))
            rows = list(csv.DictReader(io.StringIO(p.read_text())))
            self.assertTrue(all(not any(v for k, v in r.items() if k != "blind_id") for r in rows))
        self.assertEqual(len(self.ids(1)), 18)
        self.assertEqual(len(self.ids(2)), 6)

    def test_objective_skeleton_filled_only_objective(self):
        rows = list(csv.DictReader(io.StringIO((self.ctx.results / "consolidado_esqueleto.csv").read_text())))
        self.assertEqual(len(rows), 18)
        self.assertEqual(list(rows[0]), records.header())
        r = rows[0]
        self.assertEqual((r["model"], r["codex_version"], r["hidden_tests_total"], r["exit_status"]),
                         (fixtures.MODEL, "codex-cli 0.0.1", "5", "completed"))
        self.assertTrue(r["prompt_hash"] and r["baseline_hash"] and r["output_words"] and r["duration_s"])
        self.assertEqual((r["trace_code"], r["rp_assumptions"], r["notes"]), ("", "", ""))

    def test_rebuild_does_not_overwrite_filled_sheet(self):
        bid = self.ids(1)[0]
        self.fill1(bid)
        self.assertEqual(self.run_cli(["build-packs", "--force"])[0], 0)
        self.assertEqual(sheets.state(self.ctx.load(1)[0], 1), "completa")


class TestSet(CliCase):
    def test_set_computes_total_and_stamps(self):
        bid = self.ids(1)[0]
        code, out, err = self.run_cli(["set", "--pass", "1", bid, "trace_code=2", "trace_tests=0", "assumptions=1",
                                       "risks=1", "rationale=2", "fidelity=0", "reproducibility=1", "notes=dúvida em C4"])
        self.assertEqual(code, 0, err)
        row = self.ctx.load(1)[0]
        self.assertEqual(row["auditability_total"], "7")
        self.assertEqual(row["scored_at"], "2026-10-05T09:00:00-03:00")
        self.assertEqual(sheets.state(row, 1), "parcial")
        records.parse_timestamp(row["scored_at"])

    def test_invalid_values_rejected_in_portuguese_and_not_saved(self):
        bid = self.ids(1)[0]
        code, _, err = self.run_cli(["set", "--pass", "1", bid, "trace_code=3"])
        self.assertEqual(code, 1)
        self.assertIn("deve estar entre 0 e 2", err)
        self.assertIn("nada foi gravado", err)
        self.assertEqual(self.ctx.load(1)[0]["trace_code"], "")
        code, _, err = self.run_cli(["set", "--pass", "1", bid, "rp_confirmed=1"])
        self.assertIn("rp_confirmed excede", err)
        code, _, err = self.run_cli(["set", "--pass", "1", bid, "claims_checked=11"])
        self.assertIn("claims_checked > 10", err)
        code, _, err = self.run_cli(["set", "--pass", "1", bid, "scored_at=2020-01-01T00:00:00Z"])
        self.assertEqual(code, 1)

    def test_c2_c6_follow_anchors(self):
        bid = self.ids(1)[0]
        n = self.ctx.n_req()[bid]
        code, _, err = self.run_cli(["set", "--pass", "1", bid, f"c2_valid_refs={n}", "c2_rest_declared=0",
                                     "c6_claims=5", "c6_material=0", "c6_minor=0", "trace_tests=1", "fidelity=2"])
        self.assertEqual(code, 1)
        self.assertIn("trace_tests (C2)=1 difere", err)

    def test_err_blocked_until_pass1_closed(self):
        bid = self.ids(1)[0]
        code, _, err = self.run_cli(["set", "--pass", "1", bid, "err_outros=0"])
        self.assertEqual(code, 1)
        self.assertIn("depois de fechada a passagem 1", err)

    def test_validate_catches_manual_edit_problems(self):
        bid = self.ids(1)[0]
        self.fill1(bid)
        rows = self.ctx.load(1)
        rows[0]["auditability_total"] = "9"
        rows[0]["scored_at"] = ""
        rows[1]["trace_code"] = "x"
        self.ctx.save(1, rows)
        code, out, _ = self.run_cli(["validate", "--pass", "1"])
        self.assertEqual(code, 1)
        self.assertIn("difere da soma", out)
        self.assertIn("sem scored_at", out)
        self.assertIn("deve ser um número inteiro", out)
        rows[0]["auditability_total"] = ""
        rows[0]["scored_at"] = self.clock[0].isoformat()
        rows[1]["trace_code"] = ""
        self.ctx.save(1, rows)
        self.assertEqual(self.run_cli(["validate", "--pass", "1"])[0], 0)
        code, out, _ = self.run_cli(["validate", "--pass", "1", "--completo"])
        self.assertEqual(code, 1)
        self.assertIn("ficha ainda vazia", out)

    def test_stamp_completes_missing_timestamps(self):
        bid = self.ids(1)[0]
        rows = self.ctx.load(1)
        rows[0].update(ZERO)
        self.ctx.save(1, rows)
        self.assertEqual(self.run_cli(["validate", "--pass", "1"])[0], 1)
        self.assertEqual(self.run_cli(["stamp", "--pass", "1"])[0], 0)
        self.assertEqual(self.ctx.load(1)[0]["scored_at"], "2026-10-05T09:00:00-03:00")
        self.assertEqual(self.ctx.load(1)[0]["auditability_total"], "0")
        self.assertEqual(self.run_cli(["validate", "--pass", "1"])[0], 0)

    def test_no_run_id_or_condition_in_output(self):
        key_runs = set(self.ctx.key()["key"].values())
        outs = []
        for argv in (["status"], ["validate"], ["set", "--pass", "1", self.ids(1)[0], "trace_code=9"]):
            outs.append("".join(self.run_cli(argv)[1:]))
        outs.append("".join(self.run_cli(["consolidate"])[1:]))
        blob = "\n".join(outs)
        for rid in key_runs:
            self.assertNotIn(rid, blob)
        self.assertNotIn("controle", blob)
        self.assertNotIn("explicacao", blob)


class TestPass2Gate(CliCase):
    def test_pass2_blocked_before_pass1_closed_and_before_24h(self):
        code, _, err = self.run_cli(["set", "--pass", "2", self.ids(2)[0], "trace_code=0"])
        self.assertEqual(code, 1)
        self.assertIn("depois de fechar a passagem 1", err)
        self.fill_all_pass1()
        self.clock[0] = T0 + timedelta(hours=23, minutes=59)
        code, _, err = self.run_cli(["set", "--pass", "2", self.ids(2)[0], "trace_code=0"])
        self.assertEqual(code, 1)
        self.assertIn("a partir de", err)
        self.clock[0] = T0 + timedelta(hours=24)
        code, _, err = self.run_cli(["set", "--pass", "2", self.ids(2)[0], "trace_code=0"])
        self.assertEqual(code, 0, err)
        self.assertIn("2026-10-06T09:00:00-03:00", self.ctx.load(2)[0]["scored_at"])

    def test_pass1_locked_after_pass2_starts(self):
        self.fill_all_pass1()
        self.clock[0] = T0 + timedelta(hours=30)
        self.run_cli(["set", "--pass", "2", self.ids(2)[0], "trace_code=0"])
        code, _, err = self.run_cli(["set", "--pass", "1", self.ids(1)[0], "trace_code=1"])
        self.assertEqual(code, 1)
        self.assertIn("encerrada", err)

    def test_validate_refuses_interval_below_24h_via_records(self):
        self.fill_all_pass1()
        self.clock[0] = T0 + timedelta(hours=30)
        for bid in self.ids(2):
            self.assertEqual(self.run_cli(["set", "--pass", "2", bid] + [f"{c}=0" for c in records.SCORE_FIELDS])[0], 0)
        self.assertEqual(self.run_cli(["validate"])[0], 0)
        rows2 = self.ctx.load(2)  # edição manual indevida: carimbo adiantado
        rows2[0]["scored_at"] = (T0 + timedelta(hours=5)).isoformat()
        self.ctx.save(2, rows2)
        code, out, _ = self.run_cli(["validate", "--pass", "2"])
        self.assertEqual(code, 1)
        self.assertIn("intervalo entre passagens", out)
        self.assertIn("inferior ao mínimo de 24 h", out)
        self.assertIsNone(re.search(r"\bR\d{2}\b", out))


class TestConsolidate(CliCase):
    def test_end_to_end_valid(self):
        self.fill_all_pass1()
        code, out, _ = self.run_cli(["consolidate"])
        self.assertEqual(code, 0, out)
        recs = records.read_csv((self.ctx.results / "results.csv").read_text())
        self.assertEqual(len(recs), 18)
        key = self.ctx.key()["key"]
        self.assertTrue(all(r["auditability_total"] == 0 for r in recs))
        self.assertIn("passagem 2 ainda não feita", out)
        self.clock[0] = T0 + timedelta(hours=25)
        for bid in self.ids(2):
            self.run_cli(["set", "--pass", "2", bid] + [f"{c}=1" for c in records.SCORE_FIELDS])
        code, out, _ = self.run_cli(["consolidate"])
        self.assertEqual(code, 0, out)
        rows = records.read_reevaluation_csv((self.ctx.results / "reevaluation.csv").read_text())
        self.assertEqual(len(rows), 24)
        p2 = [r for r in rows if r["pass"] == 2]
        self.assertEqual({r["run_id"] for r in p2}, {key[b] for b in self.ids(2)})
        self.assertEqual(records.validate_reevaluation(rows), [])
        self.assertTrue((self.ctx.results / "scoring" / next(iter(key.values())) / "sensitivity_inputs.json").is_file())

    def test_consolidate_requires_closed_pass1(self):
        self.fill1(self.ids(1)[0])
        code, out, _ = self.run_cli(["consolidate"])
        self.assertEqual(code, 1)
        self.assertIn("ficha ainda vazia", out)
        self.assertFalse((self.ctx.results / "results.csv").exists())


if __name__ == "__main__":
    unittest.main()
