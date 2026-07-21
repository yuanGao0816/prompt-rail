"""run_eval.py scoring behavior — the engine's core contract.

These lock in: assertions pass/fail correctly, judge+assert weighting blends
as configured, the suite PASS/FAIL exit code matches the threshold, and a
broken runner is recorded as a per-case error rather than crashing the suite.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import make_workdir, run_eval, write, SCRIPTS  # noqa: E402


def _suite(workdir: Path, cases: str, *, judge: bool = False, extra: str = "") -> Path:
    runner = f"{sys.executable} {workdir / 'fake_runner.py'}"
    judge_block = (
        f"judge:\n"
        f"  command: {sys.executable} {workdir / 'fake_judge.py'}\n"
        f"  rubric: must be good\n"
        if judge else ""
    )
    text = (
        f"prompt_file: prompts/v0.md\n"
        f"runner: {runner}\n"
        f"{judge_block}"
        f"{extra}"
        f"cases:\n{cases}"
    )
    path = workdir / "suite.yaml"
    write(path, text)
    return path


def test_assert_pass_and_fail_exit_codes(tmp_path):
    wd = make_workdir(tmp_path)
    # one case the echo-runner passes (short), one it fails (too long).
    cases = (
        "  - name: short\n"
        "    vars: {reply: 'tiny'}\n"
        "    asserts: [{type: max_words, value: 5}]\n"
        "  - name: long\n"
        "    vars: {reply: 'one two three four five six seven'}\n"
        "    asserts: [{type: max_words, value: 5}]\n"
    )
    suite = _suite(wd, cases, extra="threshold: 0.8\n")
    proc, data = run_eval(wd, suite, wd / "runs.json")
    assert data is not None
    by = {r["case"]: r for r in data["results"]}
    assert by["short"]["score"] == 1.0
    assert by["long"]["score"] == 0.0
    # aggregate 0.5 < threshold 0.8 -> suite FAILs -> exit 1
    assert proc.returncode == 1
    assert data["pass"] is False


def test_judge_assert_weighting(tmp_path):
    wd = make_workdir(tmp_path)
    # assert passes (1.0), judge returns 0.0 -> blended by weights.
    cases = (
        "  - name: blend\n"
        "    vars: {reply: 'ok', judge: 0.0}\n"
        "    asserts: [{type: contains, value: 'ok'}]\n"
    )
    suite = _suite(
        wd, cases, judge=True,
        extra="weight_asserts: 0.75\nweight_judge: 0.25\nthreshold: 0.5\n",
    )
    _, data = run_eval(wd, suite, wd / "runs.json")
    # 1.0*0.75 + 0.0*0.25 = 0.75
    assert abs(data["results"][0]["score"] - 0.75) < 1e-9


def test_runner_error_is_isolated(tmp_path):
    wd = make_workdir(tmp_path)
    suite_text = (
        "prompt_file: prompts/v0.md\n"
        "runner: this_command_does_not_exist_12345\n"
        "threshold: 0.5\n"
        "cases:\n"
        "  - name: boom\n"
        "    vars: {reply: 'x'}\n"
        "    asserts: [{type: contains, value: 'x'}]\n"
    )
    write(wd / "suite.yaml", suite_text)
    proc, data = run_eval(wd, wd / "suite.yaml", wd / "runs.json")
    # the case records an error and scores 0; the suite still completes.
    assert data["results"][0]["score"] == 0.0
    assert "error" in data["results"][0]
    assert proc.returncode == 1


def test_prompt_override_changes_nothing_about_scoring(tmp_path):
    """--prompt swaps the template but the suite (the ruler) stays the same."""
    wd = make_workdir(tmp_path)
    write(wd / "prompts" / "v1.md", "different body {{reply}}")
    cases = (
        "  - name: c\n"
        "    vars: {reply: 'hello'}\n"
        "    asserts: [{type: contains, value: 'hello'}]\n"
    )
    suite = _suite(wd, cases, extra="threshold: 0.5\n")
    _, d0 = run_eval(wd, suite, wd / "r0.json", prompt=wd / "prompts" / "v0.md")
    _, d1 = run_eval(wd, suite, wd / "r1.json", prompt=wd / "prompts" / "v1.md")
    # same suite -> same fingerprint, even though the prompt differed.
    assert d0["suite_hash"] == d1["suite_hash"]
