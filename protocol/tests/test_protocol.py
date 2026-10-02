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
        # Q06: pontos do artefato (sem relatório); zeros explícitos
        "ap_decisions": 0, "ap_risks": 0, "ap_links": 0, "ap_confirmed": 0, "ap_from_summary": 0,
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
                    + ",rp_assumptions,rp_risks,rp_traces,rp_confirmed,"
                    + ",".join(records.AP_FIELDS) + ",ap_confirmed,ap_from_summary,notes")
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
            "ap_confirmed_exceeds": good_record(ap_decisions=1, ap_confirmed=2),
            "ap_from_summary_exceeds": good_record(ap_links=1, ap_from_summary=2),
            "ap_negative": good_record(ap_risks=-1),
            "ap_missing_in_explicacao_too": good_record(condition="explicacao", ap_links=2, ap_confirmed=3),
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


class ArtifactAttentionTests(unittest.TestCase):
    """Q06: medida de pontos de atenção do artefato, igual nas duas condições."""

    def test_same_rules_both_conditions(self):
        for cond in ("controle", "explicacao"):
            ok = good_record(condition=cond, ap_decisions=1, ap_risks=1, ap_links=2, ap_confirmed=3, ap_from_summary=2)
            self.assertEqual(records.validate_record(ok), [], cond)
            self.assertTrue(records.validate_record({**ok, "ap_confirmed": 5}), cond)
            self.assertTrue(records.validate_record({**ok, "ap_from_summary": 5}), cond)

    def test_controle_may_have_points_and_zero_is_valid(self):
        self.assertEqual(records.validate_record(good_record(ap_links=3, ap_confirmed=2)), [])
        self.assertEqual(records.validate_record(good_record()), [])

    def test_fields_in_schema_header_and_scoring_files(self):
        self.assertEqual(set(records.AP_FIELDS + ("ap_confirmed", "ap_from_summary")) - set(records.header()), set())
        self.assertIn("artifact_attention.json", records.SCORING_RUN_FILES)
        self.assertNotIn("artifact_attention.json", records.REQUIRED_RUN_FILES)

    def test_csv_roundtrip(self):
        rec = good_record(ap_decisions=2, ap_risks=1, ap_links=1, ap_confirmed=3, ap_from_summary=1)
        self.assertEqual(records.read_csv(records.write_csv([rec])), [rec])

    def test_summary_fraction_not_imputed_and_summary_split(self):
        c1 = good_record(run_id="R01")
        c2 = good_record(run_id="R02", ap_decisions=1, ap_links=1, ap_confirmed=1, ap_from_summary=1)
        e1 = good_record(run_id="R03", condition="explicacao", ap_decisions=2, ap_risks=1, ap_links=1,
                         ap_confirmed=4, ap_from_summary=0)
        e2 = good_record(run_id="R04", condition="explicacao", ap_links=2, ap_confirmed=1, ap_from_summary=1)
        s = descriptive.attention_summary([c1, c2, e1, e2])
        self.assertEqual(s["controle"]["runs_with_points"], 1)
        self.assertEqual(s["controle"]["median_points"], 1)          # mediana de [0, 2]
        self.assertEqual(s["controle"]["median_fraction"], 0.5)      # só a execução com pontos
        self.assertEqual(s["controle"]["median_points_without_summary"], 0.5)  # [0, 1]
        self.assertEqual(s["explicacao"]["pooled_fraction"], 5 / 6)
        self.assertEqual(s["explicacao"]["median_from_summary"], 0.5)
        self.assertIsNone(descriptive.attention_fraction(c1))
        self.assertEqual(descriptive.attention_difference([c1, c2, e1, e2])["median_points"], 3.0 - 1)

    def test_summary_none_when_no_points(self):
        s = descriptive.attention_summary([good_record(), good_record(condition="explicacao")])
        self.assertIsNone(s["controle"]["median_fraction"])
        self.assertIsNone(s["explicacao"]["pooled_fraction"])
        self.assertEqual(s["controle"]["median_points"], 0)

    def test_difference_none_without_both_conditions(self):
        self.assertIsNone(descriptive.attention_difference([good_record()]))

    def test_validator_has_no_condition_branch_for_ap(self):
        import inspect
        src = inspect.getsource(records.validate_record)
        ap_block = src[src.index("# Q06"):src.index('record["exit_status"] == "timeout"')]
        self.assertNotIn('record["condition"]', ap_block)

    def test_prompts_differ_only_by_report_block(self):
        c = (PROTOCOL_DIR / "prompts" / "controle.md").read_text(encoding="utf-8")
        e = (PROTOCOL_DIR / "prompts" / "explicacao.md").read_text(encoding="utf-8")
        self.assertTrue(e.startswith(c))
        self.assertTrue(e[len(c):].lstrip().startswith("Relatório final obrigatório"))

    def test_protocol_records_q03_q04_q06_decisions(self):
        text = (PROTOCOL_DIR / "PROTOCOL.md").read_text(encoding="utf-8")
        for needle in ("Q03=A", "Q04=A", "Q06=B", "## 22.", "## 21.", "sem LLM avaliador", "Benchmarking",
                       "por analogia", "repetição ou deriva", "Q05"):
            self.assertIn(needle, text, needle)
        sec22 = text[text.index("## 22."):]
        for item in ("5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7", "5.8"):
            self.assertIn(f"({item})", sec22, item)

    def test_q05_thresholds_untouched(self):
        rubric = (PROTOCOL_DIR / "RUBRIC.md").read_text(encoding="utf-8")
        for needle in ("Pelo menos 75% dos requisitos", "Pelo menos 5 alegações", "Pelo menos 50% dos requisitos",
                       "são **decisões metodológicas do autor** (Q12.1=A)"):
            self.assertIn(needle, rubric, needle)

    def test_protocol_documents_ap_measure(self):
        text = (PROTOCOL_DIR / "PROTOCOL.md").read_text(encoding="utf-8")
        for f in records.AP_FIELDS + ("ap_confirmed", "ap_from_summary"):
            self.assertIn(f, text)


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
        filled = fill(cfg)
        filled["model"]["name"] = cfg["author_choices"]["model_name"]
        filled["generation_parameters"]["reasoning_effort"] = cfg["author_choices"]["reasoning_effort"]
        (self.dir / "config" / "execution_config.json").write_text(json.dumps(filled))
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
        self._write_cfg(lambda c: c["model"].__setitem__("name", "gpt-5.6-luna"))

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



def reeval_row(blind_id, run_id, pass_no, scored_at, scores=(2, 1, 1, 0, 2, 1, 1), notes=""):
    row = {"blind_id": blind_id, "run_id": run_id, "pass": pass_no, "scored_at": scored_at}
    row.update(dict(zip(records.SCORE_FIELDS, scores)))
    row["auditability_total"] = sum(scores)
    row["notes"] = notes
    return row


def full_reeval_rows(gap_hours=24, scores2=None):
    """Passagem 1 de todas as 18 execuções e passagem 2 de uma por célula, `gap_hours` depois."""
    runs = manifest.generate()
    plan = manifest.blind_plan(runs)
    rows = []
    t1 = "2026-10-02T20:00:00-03:00"
    for e in plan["pass1"]:
        rows.append(reeval_row(e["blind_id"], e["run_id"], 1, t1))
    from datetime import datetime, timedelta
    t2 = (datetime.fromisoformat(t1) + timedelta(hours=gap_hours)).isoformat()
    for e in plan["pass2"]:
        rows.append(reeval_row(e["blind_id"], e["run_id"], 2, t2, scores=scores2 or (2, 1, 1, 0, 2, 1, 1)))
    return rows


class ReevaluationIntervalTests(unittest.TestCase):
    """Q12.2=B: passagem 2 no mínimo 24 h depois, com data/hora das duas passagens."""

    def test_minimum_interval_is_24_hours(self):
        self.assertEqual(manifest.MIN_REEVAL_INTERVAL_H, 24)

    def test_valid_at_exactly_24h(self):
        self.assertEqual(records.validate_reevaluation(full_reeval_rows(24), manifest.generate()), [])

    def test_valid_next_day(self):
        self.assertEqual(records.validate_reevaluation(full_reeval_rows(30), manifest.generate()), [])

    def test_rejects_old_60_minute_interval(self):
        errs = records.validate_reevaluation(full_reeval_rows(1), manifest.generate())
        self.assertTrue(errs and all("inferior ao mínimo de 24 h" in e for e in errs))
        self.assertEqual(len(errs), 6)

    def test_rejects_just_under_24h(self):
        errs = records.validate_reevaluation(full_reeval_rows(23.99), manifest.generate())
        self.assertEqual(len(errs), 6)

    def test_requires_time_and_timezone_of_both_passes(self):
        for bad in ("2026-10-02", "2026-10-03T20:00:00", "", "ontem"):
            rows = full_reeval_rows(24)
            rows[-1]["scored_at"] = bad
            self.assertTrue(any("scored_at" in e for e in records.validate_reevaluation(rows)), bad)
        rows = full_reeval_rows(24)
        rows[0]["scored_at"] = "2026-10-02"
        self.assertTrue(any("scored_at" in e for e in records.validate_reevaluation(rows)))

    def test_accepts_z_and_offset_forms(self):
        self.assertEqual(records.parse_timestamp("2026-10-02T23:00:00Z").utcoffset().total_seconds(), 0)
        self.assertEqual(records.parse_timestamp("2026-10-02T20:00:00-03:00").utcoffset().total_seconds(), -3 * 3600)

    def test_interval_is_computed_across_time_zones(self):
        rows = full_reeval_rows(24)
        pass2 = [r for r in rows if r["pass"] == 2]
        pass2[0]["scored_at"] = "2026-10-03T22:30:00Z"  # 19:30 -03:00 do dia 3: 23,5 h depois de 20:00 -03:00 do dia 2
        errs = records.validate_reevaluation(rows)
        self.assertEqual(len(errs), 1)

    def test_rejects_reused_blind_id_and_missing_pass1(self):
        rows = full_reeval_rows(24)
        pass2 = [r for r in rows if r["pass"] == 2]
        pass2[0]["blind_id"] = rows[0]["blind_id"]
        self.assertTrue(any("blind_id repetido" in e for e in records.validate_reevaluation(rows)))
        rows = [r for r in full_reeval_rows(24) if not (r["pass"] == 1 and r["run_id"] == next(x for x in full_reeval_rows(24) if x["pass"] == 2)["run_id"])]
        self.assertTrue(any("sem pontuação na passagem 1" in e for e in records.validate_reevaluation(rows)))

    def test_rejects_bad_scores_and_total(self):
        rows = full_reeval_rows(24)
        rows[0]["trace_code"] = 3
        self.assertTrue(any("trace_code" in e for e in records.validate_reevaluation(rows)))
        rows = full_reeval_rows(24)
        rows[0]["auditability_total"] += 1
        self.assertTrue(any("soma" in e for e in records.validate_reevaluation(rows)))

    def test_requires_one_artifact_per_cell(self):
        rows = full_reeval_rows(24)
        last = [i for i, r in enumerate(rows) if r["pass"] == 2][-1]
        del rows[last]
        self.assertTrue(any("um artefato por célula" in e for e in records.validate_reevaluation(rows, manifest.generate())))

    def test_csv_round_trip_and_header(self):
        header = records.reevaluation_header()
        self.assertEqual(header[:4], ["blind_id", "run_id", "pass", "scored_at"])
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=header, lineterminator="\n")
        w.writeheader()
        rows = full_reeval_rows(24)
        w.writerows(rows)
        back = records.read_reevaluation_csv(buf.getvalue())
        self.assertEqual(back, rows)
        self.assertEqual(records.validate_reevaluation(back, manifest.generate()), [])
        with self.assertRaises(ValueError):
            records.read_reevaluation_csv("a,b\n1,2\n")

    def test_summary_reports_distribution_matrix_and_intervals(self):
        rows = full_reeval_rows(26, scores2=(2, 2, 1, 0, 1, 1, 1))
        s = descriptive.reevaluation_summary(rows)
        self.assertEqual(s["pairs"], 6)
        self.assertEqual(set(s["intervals_h"].values()), {26.0})
        tt = s["criteria"]["trace_tests"]  # passagem 1 = 1, passagem 2 = 2 em todos
        self.assertEqual(tt["distribution_pass1"], [0, 6, 0])
        self.assertEqual(tt["distribution_pass2"], [0, 0, 6])
        self.assertEqual(tt["matrix_pass1_rows_pass2_cols"][1][2], 6)
        self.assertEqual(tt["exact_agreement"], 0.0)
        self.assertEqual(tt["mean_abs_difference"], 1.0)
        self.assertEqual(s["criteria"]["trace_code"]["exact_agreement"], 1.0)
        self.assertEqual(s["total_mean_abs_difference"], 0.0)  # +1 em C2 compensa -1 em C5; por isso se relata por critério
        self.assertEqual(s["criteria"]["rationale"]["mean_abs_difference"], 1.0)
        for c in records.SCORE_FIELDS:
            self.assertEqual(sum(s["criteria"][c]["distribution_pass2"]), 6)

    def test_summary_without_pairs(self):
        s = descriptive.reevaluation_summary([r for r in full_reeval_rows(24) if r["pass"] == 1])
        self.assertEqual(s["pairs"], 0)
        self.assertIsNone(s["total_mean_abs_difference"])

    def test_cli_reeval_ok_and_rejects(self):
        import contextlib
        from protocol import cli
        with tempfile.TemporaryDirectory() as d:
            for gap, expected in ((30, 0), (1, 1)):
                path = Path(d) / f"r{gap}.csv"
                buf = io.StringIO()
                w = csv.DictWriter(buf, fieldnames=records.reevaluation_header(), lineterminator="\n")
                w.writeheader()
                w.writerows(full_reeval_rows(gap))
                path.write_text(buf.getvalue())
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    self.assertEqual(cli.main(["reeval", str(path)]), expected)
                if expected:
                    self.assertIn("inferior ao mínimo de 24 h", out.getvalue())
                else:
                    self.assertIn("distribution_pass1", out.getvalue())

    def test_blind_plan_unchanged_by_interval(self):
        plan = manifest.blind_plan(manifest.generate())
        self.assertEqual(len(plan["pass1"]), 18)
        self.assertEqual(len(plan["pass2"]), 6)

    def test_docs_state_24h_and_no_60_minutes_as_current_rule(self):
        proto = (PROTOCOL_DIR / "PROTOCOL.md").read_text()
        rubric = (PROTOCOL_DIR / "RUBRIC.md").read_text()
        for text in (proto, rubric):
            self.assertIn("24 h", text)
            self.assertIn("distribuição", text)
            self.assertNotIn("intervalo mínimo de 60 minutos", text)
        self.assertIn("fora do sprint", proto)
        self.assertIn("Cronograma da avaliação", proto)
        self.assertIn("scored_at", proto)


class SensitivityTests(unittest.TestCase):
    def inp(self, **over):
        d = {"n_requirements": 7, "c2_valid_refs": 6, "c2_rest_declared": 1,
             "c6_claims": 5, "c6_material": 0, "c6_minor": 0}
        d.update(over)
        return d

    def test_official_cuts_reproduce_rubric_anchors(self):
        from protocol import sensitivity as sens
        self.assertEqual(sens.OFFICIAL, {"c2_high": 0.75, "c2_low": 0.50, "c6_min2": 5, "c6_min1": 3})
        self.assertEqual(sens.c2_score(self.inp(n_requirements=7, c2_valid_refs=6)), 2)
        self.assertEqual(sens.c2_score(self.inp(n_requirements=7, c2_valid_refs=5)), 1)   # 75% de 7 = 6 (para cima)
        self.assertEqual(sens.c2_score(self.inp(n_requirements=8, c2_valid_refs=6)), 2)
        self.assertEqual(sens.c2_score(self.inp(n_requirements=7, c2_valid_refs=6, c2_rest_declared=0)), 1)
        self.assertEqual(sens.c2_score(self.inp(n_requirements=7, c2_valid_refs=4)), 1)
        self.assertEqual(sens.c2_score(self.inp(n_requirements=7, c2_valid_refs=3)), 0)
        self.assertEqual(sens.c6_score(self.inp()), 2)
        self.assertEqual(sens.c6_score(self.inp(c6_claims=3, c6_minor=1)), 1)
        self.assertEqual(sens.c6_score(self.inp(c6_claims=2)), 0)
        self.assertEqual(sens.c6_score(self.inp(c6_material=1)), 0)
        self.assertEqual(sens.c6_score(self.inp(c6_minor=2)), 0)

    def test_variants_are_the_prespecified_ones(self):
        from protocol import sensitivity as sens
        self.assertEqual(set(sens.VARIANTS), {"oficial", "c2_high_70", "c2_high_80", "c2_low_40", "c2_low_60",
                                              "c6_min2_4", "c6_min2_6", "c6_min1_2", "c6_min1_4"})

    def test_alternative_cuts_change_scores(self):
        from protocol import sensitivity as sens
        i = self.inp(n_requirements=7, c2_valid_refs=5)  # 71%: nota 1 a 75%, nota 2 a 70%
        self.assertEqual(sens.c2_score(i, c2_high=0.75), 1)
        self.assertEqual(sens.c2_score(i, c2_high=0.70), 2)
        self.assertEqual(sens.c2_score(i, c2_high=0.80), 1)
        self.assertEqual(sens.c6_score(self.inp(c6_claims=4)), 1)
        self.assertEqual(sens.c6_score(self.inp(c6_claims=4), c6_min2=4), 2)
        self.assertEqual(sens.c6_score(self.inp(c6_claims=5), c6_min2=6), 1)
        self.assertEqual(sens.c6_score(self.inp(c6_claims=2), c6_min1=2), 1)

    def _recs(self):
        out = {}
        recs = []
        for n, (cond, c2in, c6in) in enumerate((
            ("controle", self.inp(c2_valid_refs=0, c2_rest_declared=0, c6_claims=0), None),
            ("explicacao", self.inp(c2_valid_refs=5), None),
        ), start=1):
            r = good_record(run_id=f"R{n:02d}", condition=cond)
            from protocol import sensitivity as sens
            r["trace_tests"] = sens.c2_score(c2in)
            r["fidelity"] = sens.c6_score(c2in)
            r["auditability_total"] = sum(r[f] for f in records.SCORE_FIELDS)
            recs.append(r)
            out[r["run_id"]] = c2in
        return recs, out

    def test_report_does_not_touch_official_scores_and_flags_changes(self):
        from protocol import sensitivity as sens
        recs, inputs = self._recs()
        before = copy.deepcopy(recs)
        self.assertEqual(sens.consistency_errors(recs, inputs), [])
        rep = sens.sensitivity_report(recs, inputs)
        self.assertEqual(recs, before)
        self.assertEqual(set(rep), set(sens.VARIANTS))
        self.assertFalse(rep["oficial"]["conclusion_changes"])
        self.assertTrue(rep["oficial"]["h1_direction"])
        self.assertIn("conclusion_changes", rep["c2_high_70"])

    def test_consistency_detects_wrong_c2(self):
        from protocol import sensitivity as sens
        recs, inputs = self._recs()
        recs[1]["trace_tests"] = 0
        recs[1]["auditability_total"] = sum(recs[1][f] for f in records.SCORE_FIELDS)
        self.assertTrue(any("C2 registrada" in e for e in sens.consistency_errors(recs, inputs)))
        self.assertTrue(any("sem sensitivity_inputs" in e for e in sens.consistency_errors(recs, {})))

    def test_check_inputs(self):
        from protocol import sensitivity as sens
        self.assertEqual(sens.check_inputs(self.inp()), [])
        self.assertTrue(sens.check_inputs(self.inp(c2_valid_refs=8)))
        self.assertTrue(sens.check_inputs(self.inp(c6_claims=11)))
        self.assertTrue(sens.check_inputs(self.inp(c2_rest_declared=2)))
        self.assertTrue(sens.check_inputs({}))

    def test_sensitivity_is_frozen_and_scoring_file_declared(self):
        self.assertIn("sensitivity.py", freeze_mod.FROZEN_FILES)
        self.assertIn("sensitivity_inputs.json", records.SCORING_RUN_FILES)


class AuthorDecisionsTests(unittest.TestCase):
    """Q08, Q09, Q10, Q11, Q12.1 registrados no protocolo e no template."""

    def setUp(self):
        self.proto = (PROTOCOL_DIR / "PROTOCOL.md").read_text()
        self.rubric = (PROTOCOL_DIR / "RUBRIC.md").read_text()
        self.cfg = json.loads((PROTOCOL_DIR / "config" / "execution_config.template.json").read_text())

    def test_q11_choices_in_template_and_agent_fields_still_null(self):
        c = self.cfg["author_choices"]
        self.assertEqual((c["model_name"], c["reasoning_effort"]), ("gpt-5.6-luna", "medium"))
        self.assertIsNone(self.cfg["model"]["name"])
        self.assertIsNone(self.cfg["model"]["version_or_snapshot"])
        self.assertIsNone(self.cfg["generation_parameters"]["reasoning_effort"])
        for key in ("codex_version", "interface", "invocation_command", "flags", "sandbox_mode", "approval_policy"):
            self.assertIsNone(self.cfg["agent"][key], key)

    def test_q11_documented_without_inventing_snapshot(self):
        self.assertIn("`gpt-5.6-luna`", self.proto)
        self.assertIn("`medium`", self.proto)
        self.assertIn("author_choices", self.proto)
        self.assertIn("sem execução", self.proto)
        self.assertNotRegex(self.proto, r"gpt-5\.5-\d")

    def test_freeze_rejects_divergence_from_author_choices(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["model"]["name"] = "gpt-5.6-sol"
        cfg["generation_parameters"]["reasoning_effort"] = "high"
        problems = freeze_mod.check_author_choices(cfg)
        self.assertEqual(len(problems), 2)
        cfg["model"]["name"] = "gpt-5.6-luna"
        cfg["generation_parameters"]["reasoning_effort"] = "medium"
        self.assertEqual(freeze_mod.check_author_choices(cfg), [])
        self.assertEqual(freeze_mod.check_author_choices({"model": {"name": "x"}}), [])

    def test_freeze_precondition_blocks_divergent_filled_config(self):
        with tempfile.TemporaryDirectory() as d:
            proto = Path(d) / "protocol"
            shutil.copytree(PROTOCOL_DIR, proto, ignore=shutil.ignore_patterns("__pycache__", "tests", "FREEZE.json", "manifest.json", "execution_config.json"))
            cfg = copy.deepcopy(self.cfg)

            def fill(v, key=None):
                if key == "interface":
                    return "cli"
                if key == "flags":
                    return []
                if v is None:
                    return "x"
                return {k: fill(x, k) for k, x in v.items()} if isinstance(v, dict) else v
            filled = fill(cfg)  # model.name = "x": diverge de gpt-5.6-luna
            (proto / "config" / "execution_config.json").write_text(json.dumps(filled))
            ref = Path(d) / "rev.md"
            ref.write_text("ok")
            self.assertTrue(any("author_choices" in p for p in freeze_mod.check_preconditions(proto, ref, True)))
            self.assertFalse((proto / "FREEZE.json").exists())

    def test_real_dir_freeze_state_is_consistent(self):
        """Estado reverso do rascunho: ou não há congelamento, ou os dois artefatos existem."""
        frozen = (PROTOCOL_DIR / "FREEZE.json").exists()
        self.assertEqual(frozen, (PROTOCOL_DIR / "manifest.json").exists())
        if frozen:
            self.assertTrue((PROTOCOL_DIR / "config" / "execution_config.json").exists())

    def test_q12_1_threshold_list_with_exact_wording(self):
        self.assertIn("## 23.", self.proto)
        self.assertIn("não foi localizado apoio nas fontes inspecionadas", self.proto)
        self.assertIn("não foi localizado apoio nas fontes inspecionadas", self.rubric)
        self.assertNotIn("sem respaldo na literatura", self.proto)
        self.assertNotIn("sem respaldo na literatura", self.rubric)
        for tag in ["L%d" % i for i in range(1, 15)]:
            self.assertIn(f"| {tag} |", self.proto)
        self.assertIn("plano de busca", self.proto)
        self.assertIn("não foi executado", self.proto)

    def test_q12_1_principle_support_has_locators_and_pending_citation(self):
        for needle in ("Baltes et al. (2025, seção 5.5, p. 36 e 38–39)", "EMA/CHMP (2005, seção 1, p. 3; seção 2, p. 4–5)",
                       "Laenen et al. (2006", "Bjarnason, Silva e Monperrus (2026", "Krippendorff (2018)"):
            self.assertIn(needle, self.proto)
        self.assertRegex(self.proto, r"\[CITAÇÃO NECESSÁRIA\][^\n]*Krippendorff|Krippendorff[^\n]*\[CITAÇÃO NECESSÁRIA\]")
        self.assertIn("[CITAÇÃO NECESSÁRIA]", self.rubric)

    def test_q12_1_sensitivity_prespecified_and_thresholds_unchanged(self):
        for needle in ("70%", "80%", "sensitivity.py", "Não altera nenhuma nota oficial", "sensitivity_inputs.json"):
            self.assertIn(needle, self.proto)
        self.assertIn("0,10", self.proto)
        self.assertIn("Pelo menos 75% dos requisitos", self.rubric)
        self.assertIn("Pelo menos 5 alegações verificáveis", self.rubric)
        self.assertEqual(manifest.TIMEOUT_S, 720)

    def test_q10_single_rater_limitation_declared(self):
        self.assertIn("Avaliador único (Q10=A)", self.proto)
        lim = self.proto.split("## 14.")[1].split("## 15.")[0]
        self.assertIn("avaliador único", lim)
        self.assertIn("sem avaliador externo", lim)
        self.assertIn("cegamento parcial", lim)

    def test_q08_and_q09_notes_in_protocol(self):
        sec20 = self.proto.split("## 20.")[1].split("## 21.")[0]
        for needle in ("f934ab8", "declaração do autor; método não detalhado", "será escrito por ele",
                       "URL do repositório experimental será citada", "agentes de IA", "AI-REVIEW-LOG.csv"):
            self.assertIn(needle, sec20)
        sec24 = self.proto.split("## 24.")[1]
        for needle in ("versão 8 do arXiv", "10.48550/arXiv.2508.15503", "antes da entrega final"):
            self.assertIn(needle, sec24)

    def test_ai_review_log_header_is_unchanged(self):
        h = (PROTOCOL_DIR / "schema" / "ai_review_log_header.csv").read_text().strip().split(",")
        self.assertEqual(tuple(h), records.AI_REVIEW_FIELDS)


if __name__ == "__main__":
    unittest.main()