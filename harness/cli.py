"""CLI do harness: prepare, evaluate, verify.

  python -m harness.cli prepare  --task t1_shipping --run-id R --out DIR [--runs-dir runs]
  python -m harness.cli evaluate --task t1_shipping --run-id R --workspace DIR [--runs-dir runs]
  python -m harness.cli verify   [--runs-dir PATH]   (referências 100%, baselines conforme esperado)

`prepare` e `evaluate` gravam metadados fora do workspace, em RUNS_DIR/RUN_ID/.
Nenhuma etapa executa o agente.
"""

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import mutation, registry, runner, workspace


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def check_python():
    """Exige a mesma série (major.minor) de Python fixada em .python-version."""
    pinned = registry.pinned_python()
    if ".".join(pinned.split(".")[:2]) != ".".join(platform.python_version_tuple()[:2]):
        raise RuntimeError(f"Python {platform.python_version()} != fixado {pinned} (.python-version)")
    return pinned


def _git_state():
    def git(*args):
        try:
            out = subprocess.run(["git", "-C", str(registry.ROOT), *args], capture_output=True, text=True,
                                 timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            return None
        return out.stdout.strip() if out.returncode == 0 else None
    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain")
    return {"git_commit": commit, "git_dirty": None if status is None else bool(status)}


def _provenance(task_id):
    """Hashes de tudo que define a medição (sem expor conteúdo de avaliação)."""
    return dict(
        baseline_hash=workspace.baseline_hash(task_id),
        requirements_hash=workspace.requirements_hash(task_id),
        public_tests_hash=workspace.public_tests_hash(task_id),
        oracle_hash=workspace.oracle_hash(task_id),
        evaluation_bundle_hash=workspace.evaluation_bundle_hash(),
        task_evaluation_hash=workspace.evaluation_bundle_hash(task_id),
        harness_hash=workspace.harness_hash(),
        python_pinned=registry.pinned_python(),
        python=platform.python_version(),
        platform=platform.platform(),
        **_git_state(),
    )


def prepare(task_id, run_id, out, runs_dir):
    check_python()
    manifest = workspace.build_workspace(task_id, out)
    meta = dict(manifest, **_provenance(task_id), run_id=run_id, prepared_at=_now(),
                workspace_path=str(Path(out).resolve()))
    workspace.write_json(Path(runs_dir) / run_id / "prepare.json", meta)
    return meta


def evaluate(task_id, run_id, ws, runs_dir, timeout=runner.DEFAULT_TIMEOUT_S):
    check_python()
    start = time.monotonic()
    started_at = _now()
    # hash e modificação de tests/ ANTES de executar qualquer coisa
    final_hash = workspace.tree_hash(ws)
    tests_dir = Path(ws) / "tests"
    tests_modified = (not tests_dir.is_dir()
                      or workspace.tree_hash(tests_dir) != workspace.public_tests_hash(task_id))
    public = runner.run_public_tests(task_id, ws, timeout)
    hidden = runner.run_hidden_tests(task_id, ws, timeout)
    meta = dict(
        _provenance(task_id),
        run_id=run_id,
        task_id=task_id,
        final_workspace_hash=final_hash,
        agent_modified_public_tests=tests_modified,
        evaluation_started_at=started_at,
        evaluation_duration_s=round(time.monotonic() - start, 3),
        test_timeout_s=timeout,
        public_tests_passed=public["passed"],
        public_tests_total=public["total"],
        hidden_tests_passed=hidden["passed"],
        hidden_tests_total=hidden["total"],
        hidden_failed_tests=hidden["failed_tests"],
        hidden_not_run_tests=hidden["not_run_tests"],
        public_failed_tests=public["failed_tests"],
        public_status=public["status"],
        hidden_status=hidden["status"],
    )
    workspace.write_json(Path(runs_dir) / run_id / "evaluation.json", meta)
    return meta


def verify(runs_dir=None):
    """Valida referências e baselines contra as expectativas documentadas."""
    import tempfile

    ok = True
    report = []
    for task_id in registry.task_ids():
        exp = json.loads((registry.evaluation_dir(task_id) / "baseline_expectations.json").read_text())
        with tempfile.TemporaryDirectory(prefix="tcc-verify-") as tmp:
            base_ws = Path(tmp) / "baseline"
            workspace.build_workspace(task_id, base_ws)
            pub_b = runner.run_public_tests(task_id, base_ws)
            hid_b = runner.run_hidden_tests(task_id, base_ws)
            ref_ws = Path(tmp) / "reference"
            workspace.build_workspace(task_id, ref_ws)
            ref_dir = registry.evaluation_dir(task_id) / "reference"
            for f in ref_dir.glob("*.py"):
                (ref_ws / f.name).write_bytes(f.read_bytes())
            pub_r = runner.run_public_tests(task_id, ref_ws)
            hid_r = runner.run_hidden_tests(task_id, ref_ws)
        ref_ok = pub_r["status"] == "ok" and hid_r["status"] == "ok"
        base_ok = (sorted(pub_b["failed_tests"]) == sorted(exp["public_fail"])
                   and sorted(hid_b["failed_tests"]) == sorted(exp["hidden_fail"]))
        mut_ok, mut_report = mutation.check(task_id)
        ok &= ref_ok and base_ok and mut_ok
        report.append({
            "task": task_id,
            "reference": f"public {pub_r['passed']}/{pub_r['total']}, hidden {hid_r['passed']}/{hid_r['total']}",
            "baseline": f"public {pub_b['passed']}/{pub_b['total']}, hidden {hid_b['passed']}/{hid_b['total']}",
            "reference_ok": ref_ok, "baseline_as_expected": base_ok,
            "alternatives": f"{len(mut_report['alternatives']) - len(mut_report['correct_alternatives_rejected'])}/{len(mut_report['alternatives'])} aceitas",
            "mutants": f"{len(mut_report['mutants']) - len(mut_report['surviving_mutants'])}/{len(mut_report['mutants'])} mortos",
            "mutation_ok": mut_ok,
            "correct_alternatives_rejected": mut_report["correct_alternatives_rejected"],
            "surviving_mutants": mut_report["surviving_mutants"],
        })
    return ok, report


def main(argv=None):
    p = argparse.ArgumentParser(prog="harness")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("prepare", "evaluate"):
        s = sub.add_parser(name)
        s.add_argument("--task", required=True, choices=registry.task_ids())
        s.add_argument("--run-id", required=True)
        s.add_argument("--runs-dir", default=str(registry.RUNS_DIR))
        s.add_argument("--out" if name == "prepare" else "--workspace", dest="path", required=True)
    sub.add_parser("verify")
    args = p.parse_args(argv)
    if args.cmd == "prepare":
        print(json.dumps(prepare(args.task, args.run_id, args.path, args.runs_dir), indent=2))
    elif args.cmd == "evaluate":
        print(json.dumps(evaluate(args.task, args.run_id, args.path, args.runs_dir), indent=2))
    else:
        ok, report = verify()
        print(json.dumps(report, indent=2))
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
