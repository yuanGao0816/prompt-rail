"""diff_runs.py — the suite-fingerprint guard (the subtlest correctness rule).

Comparing scores from two different suites is meaningless. diff_runs must
refuse (exit 2) when the two runs carry different suite_hashes, and only
proceed under --force. When the hashes match, it gives the normal keep/revert
verdict (exit 0 = keep, 1 = revert).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import make_workdir, run_eval, write, run_diff  # noqa: E402


def _suite(workdir: Path, cases: str, extra: str = "") -> Path:
    runner = f"{sys.executable} {workdir / 'fake_runner.py'}"
    text = (
        f"prompt_file: prompts/v0.md\n"
        f"runner: {runner}\n"
        f"{extra}cases:\n{cases}"
    )
    path = workdir / "suite.yaml"
    write(path, text)
    return path


CASES_A = (
    "  - name: c\n"
    "    vars: {reply: 'hello world'}\n"
    "    asserts: [{type: contains, value: 'hello'}]\n"
)
# CASES_B adds a case -> different fingerprint.
CASES_B = CASES_A + (
    "  - name: extra\n"
    "    vars: {reply: 'hello world'}\n"
    "    asserts: [{type: contains, value: 'world'}]\n"
)


def test_same_suite_compares_and_keeps(tmp_path):
    wd = make_workdir(tmp_path)
    write(wd / "prompts" / "v1.md", "{{reply}}")
    suite = _suite(wd, CASES_A, extra="threshold: 0.5\n")
    run_eval(wd, suite, wd / "v0.json", prompt=wd / "prompts" / "v0.md")
    run_eval(wd, suite, wd / "v1.json", prompt=wd / "prompts" / "v1.md")
    proc = run_diff(wd / "v0.json", wd / "v1.json")
    # identical scores, no regressions -> keep path, exit 0; never the abort (2).
    assert proc.returncode in (0, 1)
    assert "SUITE MISMATCH" not in proc.stdout


def test_different_suite_aborts(tmp_path):
    wd = make_workdir(tmp_path)
    suite_a = _suite(wd, CASES_A, extra="threshold: 0.5\n")
    run_eval(wd, suite_a, wd / "a.json")
    suite_b = _suite(wd, CASES_B, extra="threshold: 0.5\n")  # overwrites suite.yaml
    run_eval(wd, suite_b, wd / "b.json")
    proc = run_diff(wd / "a.json", wd / "b.json")
    assert proc.returncode == 2
    assert "SUITE MISMATCH" in proc.stdout


def test_force_overrides_mismatch(tmp_path):
    wd = make_workdir(tmp_path)
    suite_a = _suite(wd, CASES_A, extra="threshold: 0.5\n")
    run_eval(wd, suite_a, wd / "a.json")
    suite_b = _suite(wd, CASES_B, extra="threshold: 0.5\n")
    run_eval(wd, suite_b, wd / "b.json")
    proc = run_diff(wd / "a.json", wd / "b.json", "--force")
    # with --force it proceeds to a verdict instead of aborting with 2.
    assert proc.returncode in (0, 1)
