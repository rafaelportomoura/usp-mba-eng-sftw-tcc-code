import json
import os
import re
import signal
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from executor import cli, command, config, diffing, events, isolation, run as run_mod
from executor.tests.stub_codex import make_stub
from harness import registry

SECRET = "SEGREDO-FALSO-" + "x9Zk" * 8
CFG = {"model": {"name": "modelo-de-teste"}, "generation_parameters": {"reasoning_effort": "nivel-teste"},
       "execution": {"timeout_s": 720}, "agent": {"codex_version": "0.154.0"}}


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="tcc-exec-test-")
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        self.auth = self.tmp / "fonte" / "auth.json"
        self.auth.parent.mkdir()
        self.auth.write_text(json.dumps({"tokens": {"access_token": SECRET, "id": "curto"}}))
        self.runs = self.tmp / "runs"
        self.scratch = self.tmp / "scratch"
        self.scratch.mkdir()
        self.record = self.tmp / "record.json"
        # Isola o estado de congelamento do diretório real: os testes valem antes e depois do `freeze`.
        self.noprotocol = self.tmp / "protocol_sem_freeze"
        self.noprotocol.mkdir()
        patcher = mock.patch.object(run_mod, "PROTOCOL_DIR", self.noprotocol)
        patcher.start()
        self.addCleanup(patcher.stop)

    def stub(self, **cfg):
        return make_stub(self.tmp / "codex", record=str(self.record), **cfg)

    def params(self, timeout=720.0, version="0.154.0"):
        return config.ExecParams("modelo-de-teste", "nivel-teste", timeout, version)

    def run_exec(self, run_id="T1", condition="controle", evaluate=False, params=None, **kw):
        return run_mod.run_one("t1_shipping", condition, run_id, params or self.params(), self.runs,
                               self.scratch, self.auth, codex_bin=kw.pop("codex_bin"),
                               allow_unfrozen=True, evaluate=evaluate, **kw)

    def rec(self):
        return json.loads(self.record.read_text())


class CommandTests(unittest.TestCase):
    HELP_FLAGS = {"--json", "--output-last-message", "--sandbox", "--cd", "--model", "-c",
                  "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check", "--color"}

    def test_only_documented_flags_and_required_ones_present(self):
        argv = command.build_argv("codex", "/w", "/m.md", "mod", "high")
        flags = {a for a in argv if a.startswith("-") and a != "-"}
        self.assertEqual(flags, self.HELP_FLAGS)
        self.assertEqual(argv[:2], ["codex", "exec"])
        self.assertEqual(argv[argv.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(argv[argv.index("-c") + 1], 'model_reasoning_effort="high"')
        self.assertEqual(argv[argv.index("--model") + 1], "mod")
        self.assertEqual(argv[-1], "-")
        for banned in ("--dangerously-bypass-approvals-and-sandbox", "--ephemeral", "--profile"):
            self.assertNotIn(banned, argv)

    def test_flags_exist_in_installed_codex_help_when_available(self):
        import shutil
        import subprocess
        if not shutil.which("codex"):
            self.skipTest("codex ausente")
        out = subprocess.run(["codex", "exec", "--help"], capture_output=True, text=True, timeout=60).stdout
        for f in self.HELP_FLAGS:
            self.assertIn(f, out)  # somente `--help`; não executa nenhuma sessão


class ConfigTests(Base):
    def write(self, cfg):
        p = self.tmp / "cfg.json"
        p.write_text(json.dumps(cfg))
        return p

    def test_loads_explicit_values(self):
        p = config.load(self.write(CFG))
        self.assertEqual((p.model, p.reasoning_effort, p.timeout_s, p.codex_version_expected),
                         ("modelo-de-teste", "nivel-teste", 720.0, "0.154.0"))

    def test_template_is_rejected_model_and_effort_pending(self):
        tpl = registry.ROOT / "protocol" / "config" / "execution_config.template.json"
        with self.assertRaises(config.ConfigError):
            config.load(tpl)

    def test_missing_null_or_nao_exposto_model_or_effort_rejected(self):
        for dotted, bad in (("model.name", None), ("model.name", ""), ("model.name", "nao_exposto"),
                            ("generation_parameters.reasoning_effort", None),
                            ("generation_parameters.reasoning_effort", "  ")):
            cfg = json.loads(json.dumps(CFG))
            a, b = dotted.split(".")
            cfg[a][b] = bad
            with self.subTest(dotted=dotted, bad=bad), self.assertRaises(config.ConfigError):
                config.load(self.write(cfg))


class RunTests(Base):
    def test_successful_run_captures_everything_and_flags(self):
        meta = self.run_exec(codex_bin=self.stub(), evaluate=True)
        run_dir = self.runs / "T1"
        for name in ("prompt.txt", "agent_events.jsonl", "final_message.md", "workspace.diff", "prepare.json",
                     "evaluation.json", "run_meta.json", "stderr.txt"):
            self.assertTrue((run_dir / name).is_file(), name)
        from protocol import records
        self.assertEqual(records.check_run_dir(run_dir), [])
        self.assertEqual(meta["exit_status"], "completed")
        self.assertFalse(meta["classification_required"])
        self.assertEqual((run_dir / "final_message.md").read_text(), "mensagem final sintetica")
        self.assertIn("alterado pelo stub", (run_dir / "workspace.diff").read_text())
        self.assertIn("+# alterado pelo stub", (run_dir / "workspace.diff").read_text())
        self.assertTrue((run_dir / "codex_home_sessions" / "rollout-synthetic.jsonl").is_file())
        self.assertIn("alterado pelo stub", (run_dir / "workspace_final" / "shipping.py").read_text())
        # prompt exato (bytes) e hash
        data = (registry.ROOT / "protocol" / "prompts" / "controle.md").read_bytes()
        self.assertEqual((run_dir / "prompt.txt").read_bytes(), data)
        import hashlib
        self.assertEqual(meta["prompt_sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(bytes.fromhex(self.rec()["stdin_hex"]), data)
        # eventos brutos preservados, inclusive a linha inválida
        raw = (run_dir / "agent_events.jsonl").read_text()
        self.assertIn("linha que nao e json", raw)
        self.assertEqual(meta["events_summary"]["invalid_json_lines"], 1)
        # metadados
        saved = json.loads((run_dir / "run_meta.json").read_text())
        self.assertTrue(saved["finished"])
        self.assertEqual(saved["codex_version_reported"], "codex-cli 0.154.0")
        self.assertEqual(saved["model_passed"], "modelo-de-teste")
        self.assertEqual(saved["reasoning_effort_passed"], "nivel-teste")
        self.assertEqual(saved["sandbox_mode"], "workspace-write")
        self.assertEqual(saved["timeout_s"], 720.0)
        self.assertFalse(saved["timed_out"])
        self.assertIn("evaluation_started_at", json.loads((run_dir / "evaluation.json").read_text()))
        self.assertIsNotNone(saved.get("hidden_tests"))
        self.assertFalse(saved["protocol_frozen"])
        self.assertTrue(saved["allow_unfrozen_used"])

    def test_flags_passed_to_codex_and_no_user_config_inheritance(self):
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "chave-do-usuario", "SEGREDO_X": "y"}):
            self.run_exec(codex_bin=self.stub())
        r = self.rec()
        argv = r["argv"]
        self.assertEqual(argv[0], "exec")
        for flag in ("--json", "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(argv[argv.index("--model") + 1], "modelo-de-teste")
        self.assertEqual(argv[argv.index("-c") + 1], 'model_reasoning_effort="nivel-teste"')
        ws = argv[argv.index("--cd") + 1]
        self.assertEqual(r["cwd"], ws)
        self.assertEqual(os.path.realpath(ws), ws)
        env = r["env"]
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("SEGREDO_X", env)
        self.assertNotEqual(env["HOME"], os.path.expanduser("~"))
        self.assertNotEqual(env["CODEX_HOME"], os.path.expanduser("~/.codex"))
        for key in ("HOME", "CODEX_HOME"):
            isolation.assert_scratch_outside_repos(env[key])
        # apenas credencial no CODEX_HOME no início; modo 0600
        self.assertEqual(r["codex_home_files"], ["auth.json"])
        self.assertEqual(r["auth_mode"], "0o600")
        # config do usuário jamais citada nos argumentos
        self.assertFalse(any(".codex" in a for a in argv))

    def test_pass_env_is_explicit_allowlist(self):
        with mock.patch.dict(os.environ, {"TCC_EXTRA": "1"}):
            self.run_exec(run_id="T2", codex_bin=self.stub(), pass_env=("TCC_EXTRA",))
        self.assertEqual(self.rec()["env"]["TCC_EXTRA"], "1")

    def test_credentials_never_persisted_and_codex_home_removed(self):
        meta = self.run_exec(codex_bin=self.stub(mode="ok"), keep_scratch=True)
        scratch = self.scratch / "T1"
        self.assertFalse((scratch / "codex_home").exists())  # apagado mesmo com keep_scratch
        for root in (self.runs, scratch):
            for p in root.rglob("*"):
                if p.is_file():
                    self.assertNotIn(SECRET.encode(), p.read_bytes(), p)
                    self.assertNotEqual(p.name, "auth.json")
        self.assertNotIn("auth.json", json.dumps(meta["codex_home_files_after"]))

    def test_secret_echoed_by_agent_is_redacted_and_flagged(self):
        meta = self.run_exec(codex_bin=self.stub(mode="leak", secret=SECRET))
        for p in (self.runs / "T1").rglob("*"):
            if p.is_file():
                self.assertNotIn(SECRET.encode(), p.read_bytes(), p)
        self.assertIn("agent_events.jsonl", meta["secrets_redacted_in"])
        self.assertIn("stderr.txt", meta["secrets_redacted_in"])

    def test_auth_inside_repository_refused(self):
        bad = registry.ROOT / "executor" / "_auth_teste.json"
        with self.assertRaises(isolation.IsolationError):
            isolation.install_credentials(bad, self.tmp)
        # inexistente também é recusado, sem criar nada
        self.assertFalse(bad.exists())

    def test_scratch_inside_repositories_refused(self):
        for repo in (registry.ROOT, isolation.ACADEMIC_REPO):
            with self.assertRaises(Exception):
                isolation.assert_scratch_outside_repos(repo / "scratch")

    def test_timeout_kills_process_group_and_is_valid_result(self):
        pidfile = self.tmp / "pid"
        t0 = time.monotonic()
        meta = self.run_exec(codex_bin=self.stub(mode="hang", pidfile=str(pidfile)),
                             params=self.params(timeout=2.0), evaluate=True)
        self.assertLess(time.monotonic() - t0, 60)
        self.assertEqual(meta["exit_status"], "timeout")
        self.assertTrue(meta["timed_out"])
        self.assertFalse(meta["classification_required"])
        self.assertIsNone(meta["returncode"])
        pid = int(pidfile.read_text())
        time.sleep(0.3)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)  # neto morto (zumbi reaparecido por init não responde após kill do grupo)
        self.assertTrue((self.runs / "T1" / "evaluation.json").is_file())  # avalia mesmo após timeout
        self.assertEqual(meta["final_message_bytes"], 0)
        self.assertTrue(meta["final_message_missing"])

    def test_nonzero_exit_requires_human_classification(self):
        meta = self.run_exec(codex_bin=self.stub(mode="fail"))
        self.assertEqual(meta["returncode"], 3)
        self.assertEqual(meta["exit_status"], "unclassified_nonzero_exit")
        self.assertTrue(meta["classification_required"])

    def test_version_mismatch_and_missing_binary_abort(self):
        with self.assertRaises(run_mod.ExecutorError):
            self.run_exec(codex_bin=self.stub(version="codex-cli 9.9.9"))
        self.assertFalse((self.scratch / "T1").exists())
        saved = json.loads((self.runs / "T1" / "run_meta.json").read_text())
        self.assertIn("executor_error", saved)
        self.assertFalse(saved["finished"])

    def test_refuses_unfrozen_protocol_by_default(self):
        with self.assertRaises(run_mod.ExecutorError):
            run_mod.run_one("t1_shipping", "controle", "T9", self.params(), self.runs, self.scratch,
                            self.auth, codex_bin=self.stub())
        self.assertFalse((self.runs / "T9").exists())

    def test_rerun_refused_unless_archived_with_log_preserved(self):
        stub = self.stub()
        self.run_exec(codex_bin=stub)
        with self.assertRaises(run_mod.ExecutorError):
            self.run_exec(codex_bin=stub)
        self.run_exec(codex_bin=stub, archive_previous=True)
        self.assertTrue((self.runs / "_excluded" / "T1.attempt1" / "agent_events.jsonl").is_file())

    def test_oracle_probe_flags_mentions_without_claiming_proof(self):
        meta = self.run_exec(codex_bin=self.stub(mode="peek"))
        self.assertIn("agent_events.jsonl", meta["evaluation_probe"]["suspected_evaluation_mentions"])

    def test_explicacao_prompt_is_the_condition_file(self):
        meta = self.run_exec(run_id="T3", condition="explicacao", codex_bin=self.stub())
        data = (registry.ROOT / "protocol" / "prompts" / "explicacao.md").read_bytes()
        self.assertEqual(bytes.fromhex(self.rec()["stdin_hex"]), data)
        self.assertIn("Relatório final obrigatório", data.decode())
        self.assertEqual(meta["condition"], "explicacao")

    def test_workspace_given_to_agent_has_no_evaluation_material(self):
        self.run_exec(codex_bin=self.stub())
        # o workspace final copiado contém apenas baseline/REQUIREMENTS/tests
        names = {p.name for p in (self.runs / "T1" / "workspace_final").iterdir()}
        self.assertEqual(names, {"shipping.py", "REQUIREMENTS.md", "tests"})


class CliTests(Base):
    def cfg_file(self):
        p = self.tmp / "cfg.json"
        p.write_text(json.dumps(CFG))
        return p

    def test_dry_run_executes_nothing_and_writes_nothing(self):
        before = set(self.runs.glob("*")) if self.runs.exists() else set()
        stub = self.stub()
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli.main(["dry-run", "--config", str(self.cfg_file()), "--task", "t1_shipping",
                           "--condition", "explicacao", "--codex-bin", str(stub)])
        self.assertEqual(rc, 0)
        out = json.loads(buf.getvalue())
        self.assertIn("--ignore-user-config", out["argv"])
        self.assertEqual(out["sandbox_mode"], "workspace-write")
        self.assertFalse(self.record.exists())  # o stub não foi chamado nem para --version
        self.assertFalse(Path(self.auth.parent / "x").exists())
        after = set(self.runs.glob("*")) if self.runs.exists() else set()
        self.assertEqual(before, after)
        self.assertFalse((registry.ROOT / "runs" / "DRY").exists())

    def test_dry_run_fails_without_model_config(self):
        bad = self.tmp / "bad.json"
        bad.write_text(json.dumps({"model": {"name": None}}))
        self.assertEqual(cli.main(["dry-run", "--config", str(bad), "--task", "t1_shipping",
                                   "--condition", "controle"]), 1)

    def test_run_all_follows_manifest_order_and_stops_on_unclassified(self):
        man = self.tmp / "manifest.json"
        man.write_text(json.dumps({"runs": [
            {"run_id": "M1", "task_id": "t1_shipping", "condition": "controle"},
            {"run_id": "M2", "task_id": "t1_shipping", "condition": "explicacao"}]}))
        stub = self.stub(mode="fail")
        rc = cli.main(["run-all", "--config", str(self.cfg_file()), "--manifest", str(man),
                       "--auth-file", str(self.auth), "--scratch-dir", str(self.scratch),
                       "--runs-dir", str(self.runs), "--codex-bin", str(stub), "--allow-unfrozen"])
        self.assertEqual(rc, 2)
        self.assertTrue((self.runs / "M1" / "run_meta.json").is_file())
        self.assertFalse((self.runs / "M2").exists())


class EventsAndDiffTests(Base):
    def test_events_summary_is_tolerant(self):
        p = self.tmp / "e.jsonl"
        p.write_bytes(b'{"type":"a"}\n\nnao json\n[1,2]\n{"x":1}\n\xff\xfe\n')
        s = events.summarize(p)
        self.assertEqual((s["lines"], s["blank_lines"], s["invalid_json_lines"], s["non_object_lines"]),
                         (5, 1, 2, 1))
        self.assertEqual(s["top_level_type_counts"], {"a": 1})

    def test_diff_handles_add_delete_modify_binary_and_no_newline(self):
        a, b = self.tmp / "a", self.tmp / "b"
        for d in (a, b):
            d.mkdir()
        (a / "mod.py").write_text("x = 1\n")
        (b / "mod.py").write_text("x = 2")
        (a / "del.py").write_text("old\n")
        (b / "new.py").write_text("new\n")
        (a / "bin.dat").write_bytes(b"\0\1")
        (b / "bin.dat").write_bytes(b"\0\2")
        (b / "__pycache__").mkdir()
        (b / "__pycache__" / "z.pyc").write_bytes(b"1")
        d = diffing.workspace_diff(a, b)
        for expected in ("--- a/mod.py", "+x = 2", "No newline at end of file", "--- a/del.py", "+++ /dev/null",
                         "--- /dev/null", "+++ b/new.py", "Binary files a/bin.dat and b/bin.dat differ"):
            self.assertIn(expected, d)
        self.assertNotIn("pyc", d)
        self.assertEqual(diffing.workspace_diff(a, a), "")


class RepositoryGuardTests(unittest.TestCase):
    """Guardas estáticas contra credenciais nos repositórios."""
    SKIP = {".git", "__pycache__", ".venv", "runs"}
    PATTERNS = [re.compile(r'"(access_token|refresh_token|id_token)"\s*:\s*"[A-Za-z0-9._-]{20,}'),
                re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
                re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.")]

    def test_no_credential_files_or_tokens_in_repository(self):
        for path in registry.ROOT.rglob("*"):
            if set(path.relative_to(registry.ROOT).parts) & self.SKIP or not path.is_file():
                continue
            self.assertNotEqual(path.name.lower(), "auth.json", path)
            if path.suffix in (".py", ".json", ".md", ".txt", ".toml", ".jsonl", ".csv", ""):
                if path.name == "test_executor.py":
                    continue  # este arquivo contém os padrões
                text = path.read_text(encoding="utf-8", errors="replace")
                for pat in self.PATTERNS:
                    self.assertIsNone(pat.search(text), f"{path}: {pat.pattern}")

    def test_gitignore_blocks_credentials_and_codex_home(self):
        text = (registry.ROOT / ".gitignore").read_text()
        for entry in ("auth.json", "*.auth.json", ".codex/", "codex_home/", "runs/*/codex_home*/"):
            self.assertIn(entry, text)

    def test_executor_source_never_writes_to_repo_credentials(self):
        src = "".join(p.read_text() for p in (registry.ROOT / "executor").glob("*.py"))
        self.assertNotIn("Path.home", src)  # nenhum caminho padrão para o home do usuário
        self.assertNotIn(".codex/auth", src)
        self.assertNotIn("os.environ.get(\"CODEX_HOME", src)


if __name__ == "__main__":
    unittest.main()
