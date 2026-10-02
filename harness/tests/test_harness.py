import json
import os
import platform
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from harness import cli, mutation, oracle_index, registry, runner, workspace


class TmpMixin:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="tcc-test-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)


class WorkspaceContentTests(TmpMixin, unittest.TestCase):
    def test_workspace_contains_only_baseline_requirements_public_tests(self):
        for task_id in registry.task_ids():
            with self.subTest(task=task_id):
                ws = self.tmp / task_id
                workspace.build_workspace(task_id, ws)
                tdir = registry.task_dir(task_id)
                expected = {p.name for p in (tdir / "baseline").iterdir() if p.name != "__pycache__"}
                expected |= {"REQUIREMENTS.md", "tests"}
                self.assertEqual({p.name for p in ws.iterdir()}, expected)
                tests = {p.name for p in (ws / "tests").iterdir()}
                self.assertEqual(tests, {"__init__.py", "test_public.py"})

    def test_workspace_does_not_leak_oracles_or_solutions(self):
        """Prova de não vazamento: nenhum arquivo de evaluation/ aparece no workspace."""
        eval_hashes = workspace.evaluation_hashes()
        self.assertGreater(len(eval_hashes), 9)  # oráculos, referências, riscos, expectativas
        for task_id in registry.task_ids():
            with self.subTest(task=task_id):
                ws = self.tmp / task_id
                workspace.build_workspace(task_id, ws)
                self.assertEqual(workspace.find_leaks(ws), [])
                for path in workspace.tree_files(ws):
                    self.assertNotIn(workspace.sha256_file(path), eval_hashes)
                    text = path.read_text()
                    self.assertNotIn(registry.EVALUATION_MARKER, text)
                    self.assertNotIn("oracle", path.relative_to(ws).as_posix().lower())
                    self.assertNotIn("test_hidden", path.name)

    def test_every_evaluation_file_carries_marker(self):
        for path in workspace.tree_files(registry.EVALUATION_DIR):
            if path.suffix in {".py", ".md"} and path.name != "__init__.py":
                with self.subTest(path=path.name):
                    self.assertIn(registry.EVALUATION_MARKER, path.read_text())

    def test_leak_detector_catches_planted_leaks(self):
        task_id = registry.task_ids()[0]
        ws = self.tmp / "w"
        workspace.build_workspace(task_id, ws)
        ref = next((registry.evaluation_dir(task_id) / "reference").glob("*.py"))
        shutil.copy2(ref, ws / "copied.py")
        (ws / "notes.txt").write_text("trecho EVALUATION-ONLY copiado")
        (ws / "oracle").mkdir()
        (ws / "oracle" / "x.py").write_text("x = 1")
        leaks = "\n".join(workspace.find_leaks(ws))
        self.assertIn("copied.py: conteúdo idêntico", leaks)
        self.assertIn("notes.txt: contém marcador", leaks)
        self.assertIn("oracle", leaks)
        with self.assertRaises(RuntimeError):
            workspace.assert_no_leak(ws)

    def test_build_refuses_non_empty_destination(self):
        ws = self.tmp / "w"
        ws.mkdir()
        (ws / "x").write_text("1")
        with self.assertRaises(FileExistsError):
            workspace.build_workspace(registry.task_ids()[0], ws)

    def test_unknown_task(self):
        with self.assertRaises(KeyError):
            workspace.build_workspace("nope", self.tmp / "w")


class HashTests(TmpMixin, unittest.TestCase):
    def test_baseline_hash_stable_and_matches_workspace_manifest(self):
        for task_id in registry.task_ids():
            with self.subTest(task=task_id):
                a = workspace.build_workspace(task_id, self.tmp / (task_id + "a"))
                b = workspace.build_workspace(task_id, self.tmp / (task_id + "b"))
                self.assertEqual(a["baseline_hash"], b["baseline_hash"])
                self.assertEqual(a["workspace_hash"], b["workspace_hash"])
                self.assertEqual(a["baseline_hash"], workspace.baseline_hash(task_id))

    def test_tree_hash_changes_with_content_and_ignores_pycache(self):
        d = self.tmp / "d"
        d.mkdir()
        (d / "a.py").write_text("1")
        h1 = workspace.tree_hash(d)
        (d / "__pycache__").mkdir()
        (d / "__pycache__" / "a.pyc").write_bytes(b"x")
        self.assertEqual(workspace.tree_hash(d), h1)
        (d / "a.py").write_text("2")
        self.assertNotEqual(workspace.tree_hash(d), h1)


def reference_workspace(task_id, dest):
    """Workspace com a solução de referência já aplicada (usado como 'agente perfeito')."""
    workspace.build_workspace(task_id, dest)
    for f in (registry.evaluation_dir(task_id) / "reference").glob("*.py"):
        (Path(dest) / f.name).write_bytes(f.read_bytes())
    return Path(dest)


T1 = "t1_shipping"


class RunnerTests(TmpMixin, unittest.TestCase):
    def test_runs_do_not_modify_workspace(self):
        ws = self.tmp / "w"
        workspace.build_workspace(T1, ws)
        before = workspace.tree_hash(ws)
        runner.run_hidden_tests(T1, ws)
        runner.run_public_tests(T1, ws)
        self.assertEqual(workspace.tree_hash(ws), before)
        self.assertEqual(workspace.find_leaks(ws), [])

    def test_public_tests_side_effects_stay_out_of_workspace(self):
        ws = reference_workspace(T1, self.tmp / "w")
        mod = ws / "shipping.py"
        mod.write_text(mod.read_text() + "\nopen('side_effect.txt', 'w').write('x')\n")
        before = workspace.tree_hash(ws)
        runner.run_public_tests(T1, ws)
        runner.run_hidden_tests(T1, ws)
        self.assertFalse((ws / "side_effect.txt").exists())
        self.assertEqual(workspace.tree_hash(ws), before)

    def test_denominator_is_stable_for_syntax_error_crash_and_exit(self):
        ref = reference_workspace(T1, self.tmp / "ref")
        base = runner.run_hidden_tests(T1, ref)
        self.assertEqual(base["status"], "ok")
        total = base["total"]
        cases = {
            "syntax": ("def broken(:\n", "import_error"),
            "sysexit": ("import sys\nsys.exit(0)\n", "import_error"),
            "osexit": ("import os\nos._exit(0)\n", "runner_error"),
            "raises": ("raise RuntimeError('boom')\n", "import_error"),
        }
        for name, (code, status) in cases.items():
            with self.subTest(case=name):
                ws = self.tmp / name
                workspace.build_workspace(T1, ws)
                (ws / "shipping.py").write_text(code)
                for result in (runner.run_hidden_tests(T1, ws), runner.run_public_tests(T1, ws)):
                    self.assertEqual(result["status"], status)
                    self.assertEqual(result["passed"], 0)
                    self.assertEqual(result["failed"], result["total"])
                    self.assertEqual(len(result["failed_tests"]), result["total"])
                self.assertEqual(runner.run_hidden_tests(T1, ws)["total"], total)

    def test_failing_assertions_keep_same_denominator(self):
        ws = self.tmp / "w"
        workspace.build_workspace(T1, ws)  # baseline
        ref = runner.run_hidden_tests(T1, reference_workspace(T1, self.tmp / "ref"))
        base = runner.run_hidden_tests(T1, ws)
        self.assertEqual(base["total"], ref["total"])
        self.assertEqual(base["status"], "failed")

    def test_timeout_reports_fixed_total_and_kills_grandchildren(self):
        ws = reference_workspace(T1, self.tmp / "w")
        pidfile = self.tmp / "grandchild.pid"
        os.environ["TCC_PIDFILE"] = str(pidfile)
        self.addCleanup(os.environ.pop, "TCC_PIDFILE", None)
        mod = ws / "shipping.py"
        mod.write_text(
            "import os, subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
            "open(os.environ['TCC_PIDFILE'], 'w').write(str(child.pid))\n"
            "time.sleep(120)\n")
        result = runner.run_hidden_tests(T1, ws, timeout=3)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["passed"], 0)
        self.assertEqual(result["total"], len(oracle_index.expected_tests(registry.oracle_dir(T1))))
        pid = int(pidfile.read_text())
        deadline = time.time() + 5
        alive = True
        while alive and time.time() < deadline:
            try:
                os.kill(pid, 0)
                # zumbi também conta como morto para este propósito
                alive = "Z" not in Path(f"/proc/{pid}/stat").read_text().split(")")[-1][:3]
            except (ProcessLookupError, FileNotFoundError):
                alive = False
            time.sleep(0.1)
        self.assertFalse(alive, "processo-neto sobreviveu ao timeout")

    def test_stdout_cannot_forge_or_break_result_channel(self):
        ref = reference_workspace(T1, self.tmp / "ref")
        forged = {"total": 99, "passed": 99, "failed": 0, "failed_tests": [], "passed_tests": []}
        cases = {
            "forge": "import atexit, json\natexit.register(lambda: print(json.dumps(%r)))\n" % forged,
            "junkbrace": "import atexit\natexit.register(lambda: print('{not json'))\nprint('{also not json')\n",
        }
        for name, code in cases.items():
            with self.subTest(case=name):
                ws = self.tmp / name
                workspace.build_workspace(T1, ws)
                (ws / "shipping.py").write_text(code + "def calculate_shipping(*a, **k):\n    return 0\n")
                for result in (runner.run_hidden_tests(T1, ws), runner.run_public_tests(T1, ws)):
                    self.assertEqual(result["status"], "failed")
                    self.assertLess(result["passed"], result["total"])
        # solução correta que imprime lixo continua aprovada
        mod = ref / "shipping.py"
        mod.write_text("print('{ruido }')\n" + mod.read_text())
        self.assertEqual(runner.run_hidden_tests(T1, ref)["status"], "ok")

    def test_agent_created_tests_hidden_dir_does_not_break_evaluation(self):
        ws = reference_workspace(T1, self.tmp / "w")
        (ws / "tests_hidden").mkdir()
        (ws / "tests_hidden" / "test_x.py").write_text("raise SystemExit(3)\n")
        result = runner.run_hidden_tests(T1, ws)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["passed"], result["total"])

    def test_public_suite_is_official_even_if_agent_edits_tests(self):
        ws = self.tmp / "w"
        workspace.build_workspace(T1, ws)
        (ws / "tests" / "test_public.py").write_text(
            "import unittest\nclass PublicShippingTests(unittest.TestCase):\n    pass\n")
        result = runner.run_public_tests(T1, ws)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["total"], len(oracle_index.expected_tests(registry.public_tests_dir(T1))))

    def test_skipped_tests_count_as_not_passed(self):
        ws = reference_workspace(T1, self.tmp / "w")
        oracle = self.tmp / "oracle"
        oracle.mkdir()
        (oracle / "test_x.py").write_text(
            "import unittest\nclass X(unittest.TestCase):\n"
            "    def test_a(self):\n        pass\n"
            "    @unittest.skip('nao')\n    def test_b(self):\n        pass\n"
            "    @unittest.expectedFailure\n    def test_c(self):\n        raise AssertionError\n")
        result = runner.run_hidden_tests(T1, ws, oracle_dir=oracle)
        self.assertEqual((result["total"], result["passed"]), (3, 1))
        self.assertEqual(result["not_run_tests"], ["X.test_b", "X.test_c"])
        self.assertEqual(result["status"], "failed")

    def test_subtest_failure_counts_once(self):
        ws = self.tmp / "w"
        workspace.build_workspace(T1, ws)
        result = runner.run_hidden_tests(T1, ws)
        self.assertEqual(len(result["failed_tests"]), len(set(result["failed_tests"])))
        self.assertEqual(result["passed"] + result["failed"], result["total"])


class OracleIndexTests(unittest.TestCase):
    def test_static_index_matches_dynamic_discovery_on_reference(self):
        for task_id in registry.task_ids():
            with self.subTest(task=task_id), tempfile.TemporaryDirectory() as tmp:
                ws = reference_workspace(task_id, Path(tmp) / "w")
                hid = runner.run_hidden_tests(task_id, ws)
                self.assertEqual(hid["passed_tests"], oracle_index.expected_tests(registry.oracle_dir(task_id)))
                self.assertEqual(hid["unexpected_failures"], [])
                pub = runner.run_public_tests(task_id, ws)
                self.assertEqual(pub["passed_tests"], oracle_index.expected_tests(registry.public_tests_dir(task_id)))


class MutationRegressionTests(unittest.TestCase):
    def test_correct_alternatives_pass_and_mutants_die(self):
        for task_id in registry.task_ids():
            with self.subTest(task=task_id):
                ok, report = mutation.check(task_id)
                self.assertEqual(report["correct_alternatives_rejected"], [])
                self.assertEqual(report["surviving_mutants"], [])
                self.assertTrue(ok)
                self.assertGreaterEqual(len(report["mutants"]), 10)
                self.assertGreaterEqual(len(report["alternatives"]), 2)

    def test_mutation_check_detects_surviving_mutant_and_rejected_alternative(self):
        task_id = T1
        evaldir = registry.evaluation_dir(task_id)
        ref = evaldir / "reference" / "shipping.py"
        with tempfile.TemporaryDirectory() as tmp:
            # o mock substitui o diretório de variantes: referência como "mutante" sobrevive
            orig = mutation._variants
            fake = {"mutants": [ref], "alternatives": [evaldir / "mutants" / "M01_bankers.py"]}
            mutation._variants = lambda t, kind: fake[kind]
            try:
                ok, report = mutation.check(task_id)
            finally:
                mutation._variants = orig
        self.assertFalse(ok)
        self.assertEqual(report["surviving_mutants"], ["shipping.py"])
        self.assertEqual(report["correct_alternatives_rejected"], ["M01_bankers.py"])


class CliTests(TmpMixin, unittest.TestCase):
    def test_prepare_and_evaluate_write_metadata_outside_workspace(self):
        task_id = "t1_shipping"
        ws, runs = self.tmp / "ws", self.tmp / "runs"
        meta = cli.prepare(task_id, "R1", ws, runs)
        self.assertTrue((runs / "R1" / "prepare.json").is_file())
        self.assertEqual(workspace.find_leaks(ws), [])
        self.assertFalse(any("prepare.json" in str(p) for p in ws.rglob("*")))
        before = workspace.tree_hash(ws)
        ev = cli.evaluate(task_id, "R1", ws, runs)
        self.assertEqual(workspace.tree_hash(ws), before)
        self.assertEqual(ev["final_workspace_hash"], before)
        saved = json.loads((runs / "R1" / "evaluation.json").read_text())
        self.assertEqual(saved["baseline_hash"], meta["baseline_hash"])
        self.assertEqual(saved["hidden_tests_total"], ev["hidden_tests_total"])
        self.assertLess(ev["hidden_tests_passed"], ev["hidden_tests_total"])
        self.assertFalse(saved["agent_modified_public_tests"])
        for key in ("run_id", "task_id", "evaluation_started_at", "python", "python_pinned",
                    "final_workspace_hash", "requirements_hash", "public_tests_hash", "oracle_hash",
                    "harness_hash", "evaluation_bundle_hash", "task_evaluation_hash", "git_commit", "git_dirty",
                    "test_timeout_s"):
            self.assertIn(key, saved)
        for key in ("requirements_hash", "public_tests_hash", "oracle_hash", "harness_hash",
                    "evaluation_bundle_hash", "task_evaluation_hash"):
            self.assertRegex(saved[key], r"^[0-9a-f]{64}$")
            self.assertEqual(saved[key], meta[key])
        self.assertEqual(saved["requirements_hash"], workspace.sha256_file(registry.task_dir(task_id) / "REQUIREMENTS.md"))

    def test_evaluation_bundle_hash_covers_all_evaluation_material(self):
        import shutil
        from unittest import mock
        copy_root = self.tmp / "evaluation"
        shutil.copytree(registry.EVALUATION_DIR, copy_root, ignore=shutil.ignore_patterns("__pycache__"))
        with mock.patch.object(registry, "EVALUATION_DIR", copy_root):
            base = workspace.evaluation_bundle_hash()
            self.assertEqual(base, workspace.evaluation_bundle_hash())
            self.assertEqual(base, workspace.tree_hash(copy_root))
            task_base = {t: workspace.evaluation_bundle_hash(t) for t in registry.task_ids()}
            for rel in ("t2_order_pricing/mutants/M01_float_tax.py", "t2_order_pricing/reference/pricing.py",
                        "t3_inventory_reservation/alternatives/A1_snapshot_events.py",
                        "t1_shipping/RISKS.md", "t1_shipping/baseline_expectations.json",
                        "t3_inventory_reservation/oracle/test_hidden.py"):
                path = copy_root / rel
                original = path.read_bytes()
                path.write_bytes(original + b"\n# x\n")
                self.assertNotEqual(workspace.evaluation_bundle_hash(), base, rel)
                task = rel.split("/")[0]
                self.assertNotEqual(workspace.evaluation_bundle_hash(task), task_base[task], rel)
                path.write_bytes(original)
            self.assertEqual(workspace.evaluation_bundle_hash(), base)

    def test_evaluate_flags_modified_public_tests_and_fixed_denominator(self):
        task_id = T1
        ws, runs = self.tmp / "ws", self.tmp / "runs"
        cli.prepare(task_id, "R2", ws, runs)
        (ws / "tests" / "test_extra.py").write_text("import unittest\n")
        (ws / "shipping.py").write_text("def broken(:\n")
        ev = cli.evaluate(task_id, "R2", ws, runs)
        self.assertTrue(ev["agent_modified_public_tests"])
        ref_total = runner.run_hidden_tests(task_id, reference_workspace(task_id, self.tmp / "ref"))["total"]
        self.assertEqual((ev["hidden_tests_passed"], ev["hidden_tests_total"]), (0, ref_total))
        self.assertEqual(ev["hidden_status"], "import_error")

    def test_prepare_refuses_destination_inside_a_repository(self):
        runs = self.tmp / "runs"
        for inside in (registry.ROOT / "runs" / "ws-x", registry.ROOT / "ws-y",
                       registry.ROOT.parent / "usp-mba-eng-sftw-tcc" / "ws-z"):
            with self.subTest(dest=str(inside)):
                with self.assertRaises(ValueError):
                    cli.prepare(T1, "R3", inside, runs)
                self.assertFalse(inside.exists())

    def test_python_series_is_pinned(self):
        self.assertEqual(tuple(cli.check_python().split(".")[:2]), platform.python_version_tuple()[:2])
        pin = registry.PYTHON_VERSION_FILE
        self.assertRegex(pin.read_text().strip(), r"^3\.\d+\.\d+$")
        self.assertIn(pin.read_text().strip().rsplit(".", 1)[0], (registry.ROOT / "pyproject.toml").read_text())
        original = registry.pinned_python
        registry.pinned_python = lambda: "2.7.18"
        try:
            with self.assertRaises(RuntimeError):
                cli.check_python()
        finally:
            registry.pinned_python = original

    def test_verify_reference_baseline_and_mutation(self):
        ok, report = cli.verify()
        self.assertTrue(ok, report)
        self.assertEqual(len(report), 3)
        for row in report:
            self.assertTrue(row["reference_ok"] and row["baseline_as_expected"] and row["mutation_ok"], row)


if __name__ == "__main__":
    unittest.main()
