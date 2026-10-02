"""Valida as soluções de referência e as falhas esperadas dos baselines."""
import json
import tempfile
import unittest
from pathlib import Path

from harness import registry, runner, workspace


def _ws(task_id, tmp, with_reference):
    ws = Path(tmp) / ("ref" if with_reference else "base")
    workspace.build_workspace(task_id, ws)
    if with_reference:
        for f in (registry.evaluation_dir(task_id) / "reference").glob("*.py"):
            (ws / f.name).write_bytes(f.read_bytes())
    return ws


class ReferenceTests(unittest.TestCase):
    def test_reference_passes_all_public_and_hidden(self):
        for task_id in registry.task_ids():
            with self.subTest(task=task_id), tempfile.TemporaryDirectory() as tmp:
                ws = _ws(task_id, tmp, True)
                pub = runner.run_public_tests(task_id, ws)
                hid = runner.run_hidden_tests(task_id, ws)
                self.assertGreater(pub["total"], 0)
                self.assertGreater(hid["total"], pub["total"])
                self.assertEqual((pub["failed"], hid["failed"]), (0, 0), (pub, hid))

    def test_baseline_fails_as_documented(self):
        for task_id in registry.task_ids():
            with self.subTest(task=task_id), tempfile.TemporaryDirectory() as tmp:
                exp = json.loads((registry.evaluation_dir(task_id) / "baseline_expectations.json").read_text())
                ws = _ws(task_id, tmp, False)
                pub = runner.run_public_tests(task_id, ws)
                hid = runner.run_hidden_tests(task_id, ws)
                self.assertEqual(sorted(pub["failed_tests"]), exp["public_fail"])
                self.assertEqual(sorted(hid["failed_tests"]), exp["hidden_fail"])
                self.assertGreater(hid["failed"], 0)

    def test_every_requirement_has_hidden_coverage(self):
        import re
        for task_id in registry.task_ids():
            with self.subTest(task=task_id):
                req = (registry.task_dir(task_id) / "REQUIREMENTS.md").read_text()
                ids = set(re.findall(r"\*\*(R\d+)", req))
                oracle = (registry.evaluation_dir(task_id) / "oracle" / "test_hidden.py").read_text()
                covered = set(r.upper() for r in re.findall(r"def test_(r\d+)_", oracle))
                self.assertEqual(ids - covered, set())


if __name__ == "__main__":
    unittest.main()
