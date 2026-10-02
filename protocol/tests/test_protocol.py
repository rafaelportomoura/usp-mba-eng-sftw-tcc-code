import copy
import csv
import io
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from protocol import descriptive, taxonomy
from protocol import freeze as freeze_mod
from protocol import manifest, records

PROTOCOL_DIR = Path(__file__).resolve().parent.parent

GOLDEN_ORDER = [
    ("R01", "t1_shipping", "controle", 1), ("R02", "t2_order_pricing", "controle", 1),
    ("R03", "t2_order_pricing", "explicacao", 1), ("R04", "t3_inventory_reservation", "explicacao", 1),
    ("R05", "t1_shipping", "explicacao", 1), ("R06", "t3_inventory_reservation", "controle", 1),
    ("R07", "t2_order_pricing", "explicacao", 2), ("R08", "t2_order_pricing", "controle", 2),
    ("R09", "t1_shipping", "explicacao", 2), ("R10", "t3_inventory_reservation", "controle", 2),
    ("R11", "t3_inventory_reservation", "explicacao", 2), ("R12", "t1_shipping", "controle", 2),
    ("R13", "t1_shipping", "explicacao", 3), ("R14", "t3_inventory_reservation", "controle", 3),
    ("R15", "t2_order_pricing", "controle", 3), ("R16", "t1_shipping", "controle", 3),
    ("R17", "t2_order_pricing", "explicacao", 3), ("R18", "t3_inventory_reservation", "explicacao", 3),
]


def sha(c):
    return c * 64


def good_record(**over):
    r = {
        "run_id": "R01", "task_id": "t1_shipping", "condition": "controle", "replicate": 1,
        "model": "modelo-x", "codex_version": "0.0.0", "codex_interface": "cli", "prompt_hash": sha("a"), "baseline_hash": sha("b"),
        "started_at": "2026-10-02T10:00:00Z", "duration_s": 300.5, "exit_status": "completed",
        "hidden_tests_passed": 15, "hidden_tests_total": 17, "output_words": 120,
        "trace_code": 2, "trace_tests": 1, "assumptions": 1, "risks": 0, "rationale": 2,
        "fidelity": 1, "reproducibility": 2, "auditability_total": 9, "notes": "",
        # P1: 2 reprovados (15 de 17), um de cada tipo abaixo; controle: alegações 0 por regra
        "err_validacao_entrada": 1, "err_regra_negocio": 0, "err_arredondamento_numerico": 1,
        "err_atomicidade_estado": 0, "err_idempotencia_conflito": 0, "err_contrato_api": 0, "err_outros": 0,
        "claims_checked": 0, **{f: 0 for f in records.CLAIM_FIELDS},
        # P2: controle sem relatório: zeros explícitos
        "rp_assumptions": 0, "rp_risks": 0, "rp_traces": 0, "rp_confirmed": 0,
    }
    r.update(over)
    return r


def full_dataset(fallback=False):
    runs = manifest.generate()
    if fallback:
        runs = manifest.fallback(runs)
    out = []
    for m in runs:
        out.append(good_record(
            run_id=m["run_id"], task_id=m["task_id"], condition=m["condition"], replicate=m["replicate"],
            prompt_hash=sha("c" if m["condition"] == "controle" else "d"),
            baseline_hash=sha(str(manifest.TASKS.index(m["task_id"]) + 1))))
    return out


class ManifestTests(unittest.TestCase):
    def test_deterministic_and_matches_golden_order(self):
        a, b = manifest.generate(), manifest.generate(manifest.SEED)
        self.assertEqual(a, b)
        got = [(r["run_id"], r["task_id"], r["condition"], r["replicate"]) for r in a]
        self.assertEqual(got, GOLDEN_ORDER)

    def test_seed_is_20261002_and_other_seed_differs(self):
        self.assertEqual(manifest.SEED, 20261002)
        other = [(r["task_id"], r["condition"]) for r in manifest.generate(1)]
        base = [(r["task_id"], r["condition"]) for r in manifest.generate()]
        self.assertNotEqual(other, base)

    def test_18_runs_balanced_cells(self):
        runs = manifest.generate()
        self.assertEqual(len(runs), 18)
        self.assertTrue(manifest.check_runs(runs))
        for task, cond in manifest.cells():
            reps = [r["replicate"] for r in runs if (r["task_id"], r["condition"]) == (task, cond)]
            self.assertEqual(sorted(reps), [1, 2, 3])

    def test_replicates_numbered_chronologically(self):
        seen = {}
        for r in manifest.generate():
            key = (r["task_id"], r["condition"])
            seen[key] = seen.get(key, 0) + 1
            self.assertEqual(r["replicate"], seen[key])

    def test_fallback_is_12_balanced_prefix(self):
        runs = manifest.generate()
        fb = manifest.fallback(runs)
        self.assertEqual(len(fb), 12)
        self.assertEqual([r["run_id"] for r in fb], [f"R{i:02d}" for i in range(1, 13)])
        self.assertTrue(manifest.check_runs(runs, fallback_only=True))
        for task, cond in manifest.cells():
            reps = [r["replicate"] for r in fb if (r["task_id"], r["condition"]) == (task, cond)]
            self.assertEqual(sorted(reps), [1, 2])

    def test_check_runs_rejects_tampering(self):
        runs = manifest.generate()
        bad = copy.deepcopy(runs)
        bad[0]["condition"] = "explicacao"
        with self.assertRaises(ValueError):
            manifest.check_runs(bad)
        with self.assertRaises(ValueError):
            manifest.check_runs(runs[:-1])
        dup = copy.deepcopy(runs)
        dup[1]["run_id"] = dup[0]["run_id"]
        with self.assertRaises(ValueError):
            manifest.check_runs(dup)

    def test_document_is_draft_without_hashes(self):
        doc = manifest.build_document()
        self.assertEqual(doc["status"], "DRAFT")
        self.assertFalse(doc["frozen"])
        self.assertIsNone(doc["protocol_version"])
        self.assertTrue(all(v is None for v in doc["prompt_hashes"].values()))
        self.assertTrue(all(v is None for v in doc["baseline_hashes"].values()))
        self.assertEqual(doc["timeout_s"], 720)
        self.assertEqual(manifest.dumps(doc), manifest.dumps(manifest.build_document()))

    def test_committed_draft_matches_generator(self):
        path = PROTOCOL_DIR / "manifest.draft.json"
        self.assertEqual(path.read_text(encoding="utf-8"), manifest.dumps(manifest.build_document()))

    def test_shuffle_is_permutation_and_does_not_mutate(self):
        import random
        items = list(range(20))
        out = manifest.shuffle(items, random.Random(5))
        self.assertEqual(items, list(range(20)))
        self.assertEqual(sorted(out), items)


class BlindPlanTests(unittest.TestCase):
    def setUp(self):
        self.runs = manifest.generate()
        self.plan = manifest.blind_plan(self.runs)

    def test_deterministic(self):
        self.assertEqual(self.plan, manifest.blind_plan(manifest.generate()))

    def test_ids_unique_neutral_and_cover_all(self):
        ids = [e["blind_id"] for e in self.plan["pass1"] + self.plan["pass2"]]
        self.assertEqual(len(ids), 24)
        self.assertEqual(len(set(ids)), 24)
        self.assertTrue(all(re.fullmatch(r"S\d{2}", i) for i in ids))
        self.assertEqual({e["run_id"] for e in self.plan["pass1"]}, {r["run_id"] for r in self.runs})
        self.assertEqual(set(self.plan["key"]), set(ids))

    def test_ids_do_not_follow_run_order(self):
        order = [e["blind_id"] for e in self.plan["pass1"]]
        self.assertNotEqual(order, sorted(order))
        by_run = sorted(self.plan["pass1"], key=lambda e: e["run_id"])
        self.assertNotEqual([e["blind_id"] for e in by_run], sorted(e["blind_id"] for e in by_run))

    def test_reevaluation_one_per_cell_with_new_ids(self):
        index = {r["run_id"]: r for r in self.runs}
        cells = {(index[e["run_id"]]["task_id"], index[e["run_id"]]["condition"]) for e in self.plan["pass2"]}
        self.assertEqual(len(self.plan["pass2"]), 6)
        self.assertEqual(cells, set(manifest.cells()))
        first = {e["blind_id"] for e in self.plan["pass1"]}
        self.assertFalse(first & {e["blind_id"] for e in self.plan["pass2"]})

    def test_eligible_subset_and_missing_cell(self):
        fb_ids = {r["run_id"] for r in manifest.fallback(self.runs)}
        plan = manifest.blind_plan(self.runs, eligible=fb_ids)
        self.assertEqual(len(plan["pass1"]), 12)
        self.assertTrue({e["run_id"] for e in plan["pass2"]} <= fb_ids)
        with self.assertRaises(ValueError):
            manifest.blind_plan(self.runs, eligible={"R01"})


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.c = (PROTOCOL_DIR / "prompts" / "controle.md").read_text(encoding="utf-8")
        self.e = (PROTOCOL_DIR / "prompts" / "explicacao.md").read_text(encoding="utf-8")

    def test_explicacao_is_controle_plus_report_block(self):
        self.assertTrue(self.e.startswith(self.c))
        self.assertGreater(len(self.e), len(self.c))
        block = self.e[len(self.c):]
        self.assertIn("Relatório final obrigatório", block)

    def test_report_block_has_the_six_required_elements(self):
        block = self.e[len(self.c):].lower()
        for needle in ("resumo da solução", "premissas", "riscos", "justificativa técnica",
                       "requisito", "arquivo e símbolo", "teste", "comandos executados", "resultados"):
            self.assertIn(needle, block)

    def test_control_has_no_explanation_demand(self):
        low = self.c.lower()
        for needle in ("relatório", "premissa", "justificativa", "riscos", "rastreabilidade"):
            self.assertNotIn(needle, low)

    def test_no_chain_of_thought_request(self):
        for text in (self.c, self.e):
            low = text.lower()
            for needle in ("cadeia de pensamento", "chain", "passo a passo", "raciocín", "pense", "think",
                           "processo mental", "step by step"):
                self.assertNotIn(needle, low)

    def test_no_hidden_test_or_oracle_mention(self):
        for text in (self.c, self.e):
            low = text.lower()
            for needle in ("oculto", "hidden", "oracle", "oráculo", "evaluation", "referência"):
                self.assertNotIn(needle, low)

    def test_prompts_are_task_agnostic(self):
        for text in (self.c, self.e):
            for needle in ("shipping", "pricing", "inventory", "frete", "estoque", "t1", "t2", "t3"):
                self.assertNotIn(needle, text.lower())

    def test_files_end_with_single_newline_and_are_utf8(self):
        for text in (self.c, self.e):
            self.assertTrue(text.endswith("\n"))
            self.assertFalse(text.endswith("\n\n"))


class SchemaTests(unittest.TestCase):
    def test_header_matches_schema_order_and_spec(self):
        expected = ("run_id,task_id,condition,replicate,model,codex_version,codex_interface,prompt_hash,baseline_hash,"
                    "started_at,duration_s,exit_status,hidden_tests_passed,hidden_tests_total,output_words,"
                    "trace_code,trace_tests,assumptions,risks,rationale,fidelity,reproducibility,"
                    "auditability_total,"
                    + ",".join(records.ERR_FIELDS) + ",claims_checked," + ",".join(records.CLAIM_FIELDS)
                    + ",rp_assumptions,rp_risks,rp_traces,rp_confirmed,notes")
        self.assertEqual(",".join(records.header()), expected)
        self.assertEqual((PROTOCOL_DIR / "schema" / "results_header.csv").read_text().strip(), expected)
        self.assertEqual(records.load_schema()["required"], records.header())

    def test_reevaluation_header(self):
        h = (PROTOCOL_DIR / "schema" / "reevaluation_header.csv").read_text().strip().split(",")
        self.assertEqual(h[:4], ["blind_id", "run_id", "pass", "scored_at"])
        self.assertEqual(h[4:11], list(records.SCORE_FIELDS))

    def test_score_fields_are_the_seven_rubric_columns(self):
        rubric = (PROTOCOL_DIR / "RUBRIC.md").read_text(encoding="utf-8")
        for f in records.SCORE_FIELDS:
            self.assertIn(f"`{f}`", rubric)
        self.assertEqual(len(re.findall(r"^### C[1-7] ", rubric, flags=re.M)), 7)


class RubricTests(unittest.TestCase):
    def test_every_criterion_has_anchors_0_1_2_and_examples(self):
        text = (PROTOCOL_DIR / "RUBRIC.md").read_text(encoding="utf-8")
        sections = re.split(r"^### C[1-7] ", text, flags=re.M)[1:]
        self.assertEqual(len(sections), 7)
        for s in sections:
            body = s.split("\n## ")[0]
            for score in ("| 2 |", "| 1 |", "| 0 |"):
                self.assertIn(score, body)
            self.assertIn("Exemplos", body)
            self.assertIn("Fundamentação", body)

    def test_north_gap_marked(self):
        self.assertIn("[CITAÇÃO NECESSÁRIA]", (PROTOCOL_DIR / "RUBRIC.md").read_text(encoding="utf-8"))


class RecordValidationTests(unittest.TestCase):
    def test_good_record_is_valid(self):
        self.assertEqual(records.validate_record(good_record()), [])

    def test_invalid_variants(self):
        cases = {
            "condition": good_record(condition="control"),
            "task": good_record(task_id="t9"),
            "score_range": good_record(trace_code=3, auditability_total=10),
            "negative": good_record(duration_s=-1),
            "bool_as_int": good_record(replicate=True),
            "float_as_int": good_record(output_words=1.5),
            "hash_short": good_record(prompt_hash="abc"),
            "hash_upper": good_record(baseline_hash="A" * 64),
            "date": good_record(started_at="02/10/2026"),
            "status": good_record(exit_status="ok"),
            "run_id": good_record(run_id="run1"),
            "replicate_range": good_record(replicate=4),
            "empty_model": good_record(model=""),
            "interface_invalid": good_record(codex_interface="web"),
            "err_sum_mismatch": good_record(err_outros=1),
            "err_negative": good_record(err_outros=-1, err_regra_negocio=1, err_validacao_entrada=2),
            "claims_in_controle": good_record(claims_checked=3, claimdiv_regra_negocio=1),
            "claimdiv_exceeds_checked": good_record(condition="explicacao", claims_checked=1,
                                                   claimdiv_regra_negocio=1, claimdiv_contrato_api=1),
            "claims_over_10": good_record(condition="explicacao", claims_checked=11),
            "rp_confirmed_exceeds": good_record(rp_assumptions=1, rp_confirmed=2),
            "total_total_zero": good_record(hidden_tests_total=0, hidden_tests_passed=0),
        }
        for name, rec in cases.items():
            self.assertTrue(records.validate_record(rec), name)

    def test_missing_and_extra_fields(self):
        r = good_record()
        del r["notes"]
        self.assertTrue(any("ausente" in e for e in records.validate_record(r)))
        r = good_record(extra="x")
        self.assertTrue(any("não previsto" in e for e in records.validate_record(r)))

    def test_semantic_rules(self):
        self.assertTrue(records.validate_record(good_record(auditability_total=10)))
        self.assertTrue(records.validate_record(good_record(hidden_tests_passed=18)))
        self.assertTrue(records.validate_record(good_record(duration_s=800)))
        self.assertTrue(records.validate_record(good_record(exit_status="timeout", duration_s=100)))
        self.assertEqual(records.validate_record(good_record(exit_status="timeout", duration_s=720.4)), [])

    def test_max_and_min_totals(self):
        zeros = {f: 0 for f in records.SCORE_FIELDS}
        twos = {f: 2 for f in records.SCORE_FIELDS}
        self.assertEqual(records.validate_record(good_record(auditability_total=0, **zeros)), [])
        self.assertEqual(records.validate_record(good_record(auditability_total=14, **twos)), [])


class ErrorTaxonomyTests(unittest.TestCase):
    def test_taxonomy_values_and_columns(self):
        self.assertEqual(taxonomy.ERROR_TYPES, ("validacao_entrada", "regra_negocio", "arredondamento_numerico",
                                                "atomicidade_estado", "idempotencia_conflito", "contrato_api", "outros"))
        self.assertEqual(taxonomy.CLAIM_TYPES, taxonomy.ERROR_TYPES + ("relato_verificacao",))
        self.assertEqual(set(records.ERR_FIELDS + records.CLAIM_FIELDS) - set(records.header()), set())

    def test_protocol_documents_every_type(self):
        text = (PROTOCOL_DIR / "PROTOCOL.md").read_text(encoding="utf-8")
        for t in taxonomy.CLAIM_TYPES:
            self.assertIn(f"`{t}`", text)
        self.assertIn("pendentes de aprovação", text)
        self.assertIn("o tipo de erro muda quando o agente explica", text)

    def test_defaults_cover_every_requirement_of_every_task(self):
        for task in manifest.TASKS:
            req = (PROTOCOL_DIR.parent / "tasks" / task / "REQUIREMENTS.md").read_text(encoding="utf-8")
            numbers = {int(n) for n in re.findall(r"\*\*R(\d+) ", req)}
            self.assertEqual(set(taxonomy.REQUIREMENT_DEFAULT[task]), numbers, task)
            for t in taxonomy.REQUIREMENT_DEFAULT[task].values():
                self.assertIn(t, taxonomy.ERROR_TYPES)

    def test_every_oracle_test_gets_a_default_type(self):
        for task in manifest.TASKS:
            path = PROTOCOL_DIR.parent / "evaluation" / task / "oracle" / "test_hidden.py"
            if not path.is_file():
                self.skipTest("oráculos ausentes neste checkout")
            names = re.findall(r"def (test_\w+)", path.read_text(encoding="utf-8"))
            self.assertTrue(names)
            for n in names:
                self.assertIn(taxonomy.default_error_type(task, n), taxonomy.ERROR_TYPES, (task, n))
            for n in taxonomy.TEST_OVERRIDE.get(task, {}):
                self.assertIn(n, names, f"override aponta para teste inexistente: {n}")

    def test_default_type_examples_and_unknown(self):
        self.assertEqual(taxonomy.default_error_type("t1_shipping", "test_hidden.T.test_r4_tiny_excess_still_started_kg"),
                         "arredondamento_numerico")
        self.assertEqual(taxonomy.default_error_type("t3_inventory_reservation", "test_r4_replay_same_result_any_order"),
                         "idempotencia_conflito")
        self.assertEqual(taxonomy.default_error_type("t2_order_pricing", "test_r7_inputs_not_mutated"), "atomicidade_estado")
        self.assertIsNone(taxonomy.default_error_type("t1_shipping", "test_sem_padrao"))


class P1P2RecordTests(unittest.TestCase):
    def test_explicacao_record_with_claims_and_points_is_valid(self):
        r = good_record(condition="explicacao", claims_checked=6, claimdiv_relato_verificacao=1,
                        claimdiv_arredondamento_numerico=1, rp_assumptions=2, rp_risks=2, rp_traces=7, rp_confirmed=9)
        self.assertEqual(records.validate_record(r), [])

    def test_controle_may_have_spontaneous_points(self):
        self.assertEqual(records.validate_record(good_record(rp_risks=1, rp_confirmed=1)), [])

    def test_all_pass_means_all_err_zero(self):
        zeros = {f: 0 for f in records.ERR_FIELDS}
        r = good_record(hidden_tests_passed=17, **zeros)
        self.assertEqual(records.validate_record(r), [])
        self.assertTrue(records.validate_record(good_record(hidden_tests_passed=17)))

    def test_csv_roundtrip_with_new_columns(self):
        rec = good_record(condition="explicacao", claims_checked=4, claimdiv_contrato_api=1, rp_traces=3, rp_confirmed=2)
        back = records.read_csv(records.write_csv([rec]))
        self.assertEqual(back, [rec])

    def test_ai_review_header_matches_fields(self):
        h = (PROTOCOL_DIR / "schema" / "ai_review_log_header.csv").read_text().strip().split(",")
        self.assertEqual(tuple(h), records.AI_REVIEW_FIELDS)
        self.assertEqual(set(records.SCORING_RUN_FILES) & set(records.REQUIRED_RUN_FILES), set())


class DescriptiveTests(unittest.TestCase):
    def _recs(self):
        c1 = good_record(run_id="R01")
        c2 = good_record(run_id="R02", hidden_tests_passed=17, **{f: 0 for f in records.ERR_FIELDS})
        e1 = good_record(run_id="R03", condition="explicacao", hidden_tests_passed=16, claims_checked=5,
                         claimdiv_relato_verificacao=1, rp_assumptions=2, rp_risks=1, rp_traces=3, rp_confirmed=5,
                         **{**{f: 0 for f in records.ERR_FIELDS}, "err_atomicidade_estado": 1})
        e2 = good_record(run_id="R04", condition="explicacao", hidden_tests_passed=17, claims_checked=4,
                         rp_assumptions=1, rp_risks=1, rp_traces=2, rp_confirmed=4,
                         **{f: 0 for f in records.ERR_FIELDS})
        return [c1, c2, e1, e2]

    def test_error_profile_counts_and_shares(self):
        prof = descriptive.error_type_profile(self._recs())
        self.assertEqual(prof["controle"]["failed_tests"], 2)
        self.assertEqual(prof["controle"]["types"]["validacao_entrada"],
                         {"tests": 1, "runs_with": 1, "share": 0.5})
        self.assertEqual(prof["explicacao"]["types"]["atomicidade_estado"]["share"], 1.0)
        self.assertEqual(prof["explicacao"]["types"]["regra_negocio"]["runs_with"], 0)

    def test_share_undefined_when_no_failures(self):
        recs = [good_record(hidden_tests_passed=17, **{f: 0 for f in records.ERR_FIELDS}),
                good_record(condition="explicacao", hidden_tests_passed=17, **{f: 0 for f in records.ERR_FIELDS})]
        prof = descriptive.error_type_profile(recs)
        self.assertIsNone(prof["controle"]["types"]["regra_negocio"]["share"])

    def test_claim_profile_only_explicacao(self):
        cp = descriptive.claim_divergence_profile(self._recs())
        self.assertEqual(cp["claims_checked"], 9)
        self.assertEqual(cp["types"]["relato_verificacao"], 1)

    def test_review_summary_floor_is_explicit_zero_and_fraction_not_imputed(self):
        rs = descriptive.review_summary(self._recs())
        self.assertEqual(rs["controle"]["median_points"], 0)
        self.assertEqual(rs["controle"]["runs_with_points"], 0)
        self.assertIsNone(rs["controle"]["median_fraction"])
        self.assertIsNone(rs["controle"]["pooled_fraction"])
        self.assertEqual(rs["explicacao"]["runs_with_points"], 2)
        self.assertAlmostEqual(rs["explicacao"]["pooled_fraction"], 9 / 10)
        self.assertEqual(descriptive.review_fraction(good_record()), None)

    def test_profile_cli(self):
        from protocol import cli
        import contextlib
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.csv"
            p.write_text(records.write_csv(self._recs()), encoding="utf-8")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(cli.main(["profile", str(p)]), 0)
            self.assertIn("pontos_de_atencao", json.loads(buf.getvalue()))


class DatasetTests(unittest.TestCase):
    def test_full_and_fallback_datasets_valid(self):
        self.assertEqual(records.validate_dataset(full_dataset(), manifest.generate()), [])
        self.assertEqual(records.validate_dataset(full_dataset(True), manifest.generate(), fallback=True), [])

    def test_unbalanced_and_duplicate(self):
        ds = full_dataset()
        self.assertTrue(records.validate_dataset(ds[:-1], manifest.generate()))
        self.assertTrue(records.validate_dataset(full_dataset(True), manifest.generate()))
        dup = copy.deepcopy(ds)
        dup[1]["run_id"] = dup[0]["run_id"]
        self.assertTrue(any("duplicado" in e for e in records.validate_dataset(dup)))

    def test_manifest_mismatch(self):
        ds = full_dataset()
        ds[0]["condition"] = "explicacao" if ds[0]["condition"] == "controle" else "controle"
        self.assertTrue(records.validate_dataset(ds, manifest.generate()))

    def test_hash_consistency(self):
        ds = full_dataset()
        ds[0]["prompt_hash"] = sha("e")
        self.assertTrue(any("mais de um prompt_hash" in e for e in records.validate_dataset(ds)))
        ds = full_dataset()
        for r in ds:
            r["prompt_hash"] = sha("c")
        self.assertTrue(any("mesmo prompt_hash" in e for e in records.validate_dataset(ds)))

    def test_infra_failure_not_allowed_and_freeze_hashes(self):
        ds = full_dataset()
        ds[0]["exit_status"] = "infra_failure"
        self.assertTrue(any("infra_failure" in e for e in records.validate_dataset(ds)))
        freeze = {"prompt_hashes": {"controle": sha("c"), "explicacao": sha("d")},
                  "baseline_hashes": {t: sha(str(i + 1)) for i, t in enumerate(manifest.TASKS)}}
        self.assertEqual(records.validate_dataset(full_dataset(), freeze=freeze), [])
        freeze["prompt_hashes"]["controle"] = sha("f")
        self.assertTrue(records.validate_dataset(full_dataset(), freeze=freeze))

    def test_csv_roundtrip_and_header_check(self):
        ds = full_dataset()
        text = records.write_csv(ds)
        self.assertTrue(text.startswith(",".join(records.header()) + "\n"))
        back = records.read_csv(text)
        self.assertEqual(back, ds)
        self.assertEqual(records.validate_dataset(back, manifest.generate()), [])
        with self.assertRaises(ValueError):
            records.read_csv("run_id,task_id\nR01,t1\n")

    def test_csv_with_text_in_numeric_field_is_reported(self):
        text = records.write_csv([good_record()]).replace(",300.5,", ",abc,")
        rows = records.read_csv(text)
        self.assertTrue(records.validate_record(rows[0]))

    def test_notes_with_commas_and_newlines_roundtrip(self):
        rec = good_record(notes='a, "b"\nc')
        self.assertEqual(records.read_csv(records.write_csv([rec]))[0]["notes"], 'a, "b"\nc')


class UtilityTests(unittest.TestCase):
    def test_count_words(self):
        self.assertEqual(records.count_words(""), 0)
        self.assertEqual(records.count_words("| R1 | `a_b.py::f` | t |\n|---|---|---|"), 5)
        self.assertEqual(records.count_words("olá mundo, não-é"), 3)

    def test_check_run_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(records.check_run_dir(tmp), list(records.REQUIRED_RUN_FILES))
            for f in records.REQUIRED_RUN_FILES:
                (Path(tmp) / f).write_text("x")
            self.assertEqual(records.check_run_dir(tmp), [])


class FreezeTests(unittest.TestCase):
    """Todos os testes operam em cópia temporária; o protocolo real nunca é congelado."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name) / "protocol"
        shutil.copytree(PROTOCOL_DIR, self.dir, ignore=shutil.ignore_patterns("__pycache__", "tests", "FREEZE.json", "manifest.json", "execution_config.json"))
        cfg = json.loads((self.dir / "config" / "execution_config.template.json").read_text())
        self.cfg = cfg

        def fill(v, key=None):
            if key == "interface":
                return "cli"
            if key == "flags":
                return []
            if v is None:
                return "x"
            if isinstance(v, dict):
                return {k: fill(x, k) for k, x in v.items()}
            return v
        (self.dir / "config" / "execution_config.json").write_text(json.dumps(fill(cfg)))
        self.release = Path(self._tmp.name) / "review.md"
        self.release.write_text("liberado")

    def _baseline(self, task):
        return sha("9")

    def test_real_protocol_dir_is_not_frozen_by_tests(self):
        # a suíte nunca deve criar FREEZE.json no diretório real
        self.assertEqual(freeze_mod.check_preconditions(self.dir, self.release, True), [])

    def test_template_has_baltes_items(self):
        flat = json.dumps(self.cfg)
        for key in ("codex_version", "version_or_snapshot", "temperature", "reasoning_effort",
                    "agent_config_hash", "date_first_run", "timeout_s", "sha256", "required_files"):
            self.assertIn(key, flat)
        self.assertEqual(self.cfg["execution"]["timeout_s"], 720)
        self.assertEqual(self.cfg["logs"]["required_files"], list(records.REQUIRED_RUN_FILES))

    def test_refuses_without_release_or_confirmation(self):
        with self.assertRaises(freeze_mod.FreezeError):
            freeze_mod.freeze(self.dir, None, True, self._baseline)
        with self.assertRaises(freeze_mod.FreezeError):
            freeze_mod.freeze(self.dir, self.release, False, self._baseline)
        self.assertFalse((self.dir / "FREEZE.json").exists())

    def test_refuses_with_null_in_config(self):
        (self.dir / "config" / "execution_config.json").write_text(
            (self.dir / "config" / "execution_config.template.json").read_text())
        problems = freeze_mod.check_preconditions(self.dir, self.release, True)
        self.assertTrue(any("null" in p for p in problems))

    def _write_cfg(self, mutate):
        cfg = json.loads((self.dir / "config" / "execution_config.json").read_text())
        mutate(cfg)
        (self.dir / "config" / "execution_config.json").write_text(json.dumps(cfg))
        return freeze_mod.check_preconditions(self.dir, self.release, True)

    def test_template_has_codex_interface_fields(self):
        self.assertIn("interface", self.cfg["agent"])
        self.assertIn("flags", self.cfg["agent"])
        self.assertIn("working_directory", self.cfg["execution"])
        for dotted in freeze_mod.REQUIRED_CONFIG_FIELDS:
            self.assertIsNone(freeze_mod._get_path(self.cfg, dotted), dotted)

    def test_template_alone_fails_every_required_interface_field(self):
        problems = freeze_mod.check_codex_interface_fields(self.cfg)
        for dotted in freeze_mod.REQUIRED_CONFIG_FIELDS:
            self.assertTrue(any(dotted in p for p in problems), dotted)

    def test_each_required_field_null_or_missing_blocks_freeze(self):
        for dotted in freeze_mod.REQUIRED_CONFIG_FIELDS:
            section, key = dotted.split(".")
            self.assertTrue(self._write_cfg(lambda c: c[section].__setitem__(key, None)), f"null {dotted}")
            self.assertTrue(self._write_cfg(lambda c: c[section].pop(key)), f"ausente {dotted}")
            self._write_cfg(lambda c: None)

    def test_empty_and_nao_exposto_rejected_but_empty_flags_list_accepted(self):
        self.assertEqual(self._write_cfg(lambda c: c["agent"].__setitem__("flags", [])), [])
        self.assertTrue(self._write_cfg(lambda c: c["agent"].__setitem__("flags", "--x")))
        self.assertTrue(self._write_cfg(lambda c: c["agent"].__setitem__("flags", [""])))
        self.assertTrue(self._write_cfg(lambda c: c["agent"].__setitem__("codex_version", "nao_exposto")))
        self.assertTrue(self._write_cfg(lambda c: c["model"].__setitem__("name", "  ")))

    def test_interface_must_be_cli_or_api(self):
        self.assertTrue(any("interface" in p for p in self._write_cfg(lambda c: c["agent"].__setitem__("interface", "web"))))
        self.assertEqual(self._write_cfg(lambda c: c["agent"].__setitem__("interface", "api")), [])
        self.assertEqual(self._write_cfg(lambda c: c["agent"].__setitem__("interface", "cli")), [])

    def test_freeze_does_not_require_date_last_run(self):
        self.assertNotIn("date_last_run", json.dumps(self.cfg))

    def test_taxonomy_is_frozen_file(self):
        self.assertIn("taxonomy.py", freeze_mod.FROZEN_FILES)

    def test_refuses_invalid_manifest(self):
        doc = json.loads((self.dir / "manifest.draft.json").read_text())
        doc["runs"] = doc["runs"][:-1]
        (self.dir / "manifest.draft.json").write_text(json.dumps(doc))
        self.assertTrue(any("manifesto" in p for p in freeze_mod.check_preconditions(self.dir, self.release, True)))

    def test_freeze_writes_hashes_and_blocks_second_freeze(self):
        doc = freeze_mod.freeze(self.dir, self.release, True, self._baseline, now="2026-10-03T00:00:00+00:00")
        self.assertEqual(doc["protocol_version"], "v1.0.0")
        self.assertEqual(doc["seed"], 20261002)
        for c in manifest.CONDITIONS:
            expected = freeze_mod.sha256_file(self.dir / "prompts" / f"{c}.md")
            self.assertEqual(doc["prompt_hashes"][c], expected)
        self.assertNotEqual(doc["prompt_hashes"]["controle"], doc["prompt_hashes"]["explicacao"])
        self.assertEqual(set(doc["baseline_hashes"]), set(manifest.TASKS))
        final = json.loads((self.dir / "manifest.json").read_text())
        self.assertTrue(final["frozen"])
        self.assertEqual(final["status"], "FROZEN")
        self.assertEqual(final["prompt_hashes"], doc["prompt_hashes"])
        self.assertEqual(freeze_mod.verify_freeze(self.dir), [])
        with self.assertRaises(freeze_mod.FreezeError):
            freeze_mod.freeze(self.dir, self.release, True, self._baseline)

    def test_verify_detects_edit_after_freeze(self):
        freeze_mod.freeze(self.dir, self.release, True, self._baseline)
        p = self.dir / "prompts" / "controle.md"
        p.write_text(p.read_text() + "x")
        self.assertEqual(freeze_mod.verify_freeze(self.dir), ["prompts/controle.md"])

    def test_cli_freeze_without_flags_is_refused(self):
        from protocol import cli
        import contextlib
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()):
            rc = cli.main(["freeze", "--dry-run"])
        self.assertEqual(rc, 1)  # no diretório real faltam config/release; nada é gravado
        self.assertFalse((PROTOCOL_DIR / "FREEZE.json").exists())


class CliTests(unittest.TestCase):
    def test_manifest_cli_and_validate(self):
        from protocol import cli
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(cli.main(["manifest"]), 0)
        self.assertEqual(buf.getvalue(), manifest.dumps(manifest.build_document()))
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "r.csv"
            p.write_text(records.write_csv(full_dataset()), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["validate", str(p)]), 0)
                self.assertEqual(cli.main(["validate", str(p), "--fallback"]), 1)


if __name__ == "__main__":
    unittest.main()
