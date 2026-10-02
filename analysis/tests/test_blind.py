import json
import re
import tempfile
import unittest
from pathlib import Path

from protocol import manifest

from analysis import blind, sanitize
from analysis.tests import fixtures

FORBIDDEN_FILES = {"evaluation.json", "run_meta.json", "prepare.json", "prompt.txt"}


class BuildCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.runs = fixtures.make_code_root(base / "code")
        cls.packs = base / "packs"
        cls.key_path = base / "key.json"
        cls.key = blind.build_all(base / "code", cls.packs, cls.key_path)
        cls.base = base

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def files(self):
        return [p for p in self.packs.rglob("*") if p.is_file()]


class TestNoLeaks(BuildCase):
    def test_counts(self):
        self.assertEqual(len(list((self.packs / "passagem1").iterdir())), 18)
        self.assertEqual(len(list((self.packs / "passagem2").iterdir())), 6)

    def test_no_identifier_in_any_file_or_path(self):
        forbidden = [r["run_id"] for r in self.runs] + [fixtures.thread_id(n) for n in range(1, 19)]
        forbidden += [fixtures.MODEL, "codex-cli", "tcc-scratch", "controle", "alguem"]
        for p in self.files() + [d for d in self.packs.rglob("*") if d.is_dir()]:
            rel = p.relative_to(self.packs).as_posix()
            self.assertEqual(sanitize.scan_leaks(rel), [], rel)
            for token in forbidden:
                self.assertNotIn(token, rel)
            if p.is_file():
                text = p.read_text(encoding="utf-8")
                self.assertEqual(sanitize.scan_leaks(text, forbidden), [], rel)

    def test_no_run_metadata_files(self):
        self.assertFalse({p.name for p in self.files()} & FORBIDDEN_FILES)

    def test_no_hidden_test_data_or_durations(self):
        blob = "".join(p.read_text(encoding="utf-8") for p in self.files())
        for r in range(1, 19):
            self.assertNotIn(f"2026-10-02T06:{r:02d}", blob)
        self.assertNotIn("hidden_tests", blob)
        self.assertNotIn("duration_s", blob)

    def test_mtimes_constant(self):
        for p in list(self.packs.rglob("*")):
            if len(p.relative_to(self.packs).parts) >= 2:  # pacotes e tudo dentro deles
                self.assertEqual(int(p.stat().st_mtime), blind.FIXED_MTIME, str(p))

    def test_workspace_paths_neutralised(self):
        reports = [p.read_text(encoding="utf-8") for p in self.packs.rglob("relatorio_final.md")]
        self.assertTrue(any("<WORKSPACE>/" in t for t in reports))
        self.assertFalse(any("tcc-scratch" in t for t in reports))

    def test_leak_makes_build_fail(self):
        base = self.base / "leaky"
        fixtures.make_code_root(base / "code")
        run_dir = base / "code" / "runs" / "R01"
        (run_dir / "final_message.md").write_text("veja a execução R07 e o modelo gpt-5.6", encoding="utf-8")
        with self.assertRaises(ValueError):
            blind.build_all(base / "code", base / "packs", base / "key.json")


class TestKey(BuildCase):
    def test_key_matches_protocol_blind_plan(self):
        plan = manifest.blind_plan(self.runs, manifest.SEED)
        self.assertEqual(self.key["key"], plan["key"])
        self.assertEqual(self.key["blinding_seed"], manifest.SEED + 1)
        self.assertEqual(json.loads(self.key_path.read_text(encoding="utf-8"))["key"], plan["key"])

    def test_pack_content_belongs_to_keyed_run(self):
        for passage in ("passagem1", "passagem2"):
            for d in (self.packs / passage).iterdir():
                run_id = self.key["key"][d.name]
                original = (self.base / "code" / "runs" / run_id / "final_message.md").read_text(encoding="utf-8")
                self.assertEqual((d / "relatorio_final.md").read_text(encoding="utf-8"), sanitize.sanitize_text(original))
                mod = fixtures.MODULES[next(r["task_id"] for r in self.runs if r["run_id"] == run_id)]
                self.assertTrue((d / "workspace" / f"{mod}.py").is_file())

    def test_design(self):
        ids = [e["blind_id"] for e in self.key["pass1"] + self.key["pass2"]]
        self.assertEqual(len(set(ids)), 24)
        self.assertTrue(all(re.fullmatch(r"S\d{2}", i) for i in ids))
        self.assertEqual(len({e["run_id"] for e in self.key["pass1"]}), 18)
        by_run = {r["run_id"]: (r["task_id"], r["condition"]) for r in self.runs}
        self.assertEqual(sorted(by_run[e["run_id"]] for e in self.key["pass2"]), sorted(manifest.cells()))
        self.assertNotEqual([e["run_id"] for e in self.key["pass1"]], [r["run_id"] for r in self.runs])
        self.assertNotEqual([e["blind_id"] for e in self.key["pass1"]], sorted(e["blind_id"] for e in self.key["pass1"]))

    def test_pass2_new_ids_same_content(self):
        p1 = {e["run_id"]: e["blind_id"] for e in self.key["pass1"]}
        for e in self.key["pass2"]:
            self.assertNotEqual(p1[e["run_id"]], e["blind_id"])


class TestDeterminism(unittest.TestCase):
    def test_same_seed_same_everything_other_seed_differs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            fixtures.make_code_root(base / "code")
            k1 = blind.build_all(base / "code", base / "a", base / "a.json")
            k2 = blind.build_all(base / "code", base / "b", base / "b.json")
            self.assertEqual((base / "a.json").read_text(), (base / "b.json").read_text())
            self.assertEqual(k1["pack_sha256"], k2["pack_sha256"])
            k3 = blind.build_all(base / "code", base / "c", base / "c.json", seed=1234)
            self.assertNotEqual(k1["key"], k3["key"])
            self.assertEqual(k3["blinding_seed"], 1235)


class TestSanitize(unittest.TestCase):
    def test_workspace_path_and_events(self):
        t = sanitize.sanitize_text("ver /home/x/.cache/tcc-scratch/R12/workspace/a.py e /home/x/.cache/tcc-scratch/R12/workspace")
        self.assertEqual(t, "ver <WORKSPACE>/a.py e <WORKSPACE>")
        e = sanitize.sanitize_event({"type": "thread.started", "thread_id": "01a0fb49-ce32-7832-9352-5be0ae3c8c1e"})
        self.assertNotIn("01a0", json.dumps(e))
        self.assertEqual(sanitize.sanitize_event({"type": "turn.completed", "usage": {"a": 1}}), {"type": "turn.completed"})

    def test_scan_finds_patterns(self):
        kinds = {k for k, _ in sanitize.scan_leaks("R05 /home/x gpt-5.6 2026-10-02T06:25 codex-cli")}
        self.assertTrue({"run_id", "caminho_home", "modelo", "carimbo_de_tempo", "ferramenta"} <= kinds)
        self.assertEqual(sanitize.scan_leaks("R5 e S07 estão limpos"), [])


class TestFreeSummary(unittest.TestCase):
    MSG = "## 1. Resumo da solução: o que.\n\n- a\n- b\n\n## 2. Premissas\n\n- c\n"

    def test_explicacao_only_section_1_without_title(self):
        out = blind.free_summary(self.MSG, "explicacao")
        self.assertEqual(out, "- a\n- b\n")

    def test_controle_whole_message(self):
        self.assertEqual(blind.free_summary("texto\n\nmais\n", "controle"), "texto\n\nmais\n")

    def test_fallback_first_block(self):
        out = blind.free_summary("Primeiro bloco.\nOutra linha.\n\n| a | b |\n|--|--|\n", "explicacao")
        self.assertIn("Primeiro bloco.", out)
        self.assertNotIn("|", out)


if __name__ == "__main__":
    unittest.main()
