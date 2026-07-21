"""Shared helpers for the prompt-smith test suite.

Tests drive the bundled scripts as subprocesses (that's how the skill uses
them), with a fake Python runner/judge so nothing hits a real model. The fake
runner reflects each case's `vars.reply` back as the completion, so a test
fully controls what the "model" returns and therefore every score.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

# A runner that echoes vars.reply — lets a case dictate its own output.
FAKE_RUNNER = (
    "import sys, json\n"
    "d = json.load(sys.stdin)\n"
    "sys.stdout.write(d['vars'].get('reply', ''))\n"
)

# A judge that returns vars.judge (or 1.0) — lets a case dictate its judge score.
FAKE_JUDGE = (
    "import sys, json\n"
    "d = json.load(sys.stdin)\n"
    "score = float(d['vars'].get('judge', 1.0)) if isinstance(d.get('vars'), dict) else 1.0\n"
    "sys.stdout.write(json.dumps({'score': score, 'reasons': 'fake'}))\n"
)


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def run_eval(workdir: Path, suite: Path, out: Path, prompt: Path | None = None):
    """Invoke run_eval.py; return (CompletedProcess, parsed_out_json)."""
    cmd = [sys.executable, str(SCRIPTS / "run_eval.py"), str(suite), "--out", str(out)]
    if prompt is not None:
        cmd += ["--prompt", str(prompt)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
    return proc, data


def run_diff(baseline: Path, candidate: Path, *extra: str):
    cmd = [sys.executable, str(SCRIPTS / "diff_runs.py"), str(baseline), str(candidate), *extra]
    return subprocess.run(cmd, capture_output=True, text=True)


def registry(workdir: Path, *args: str):
    cmd = [sys.executable, str(SCRIPTS / "registry.py"), *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def make_workdir(tmp_path: Path) -> Path:
    """A workdir with a fake runner, a prompt, and prompts/ dir ready."""
    (tmp_path / "fake_runner.py").write_text(FAKE_RUNNER, encoding="utf-8")
    (tmp_path / "fake_judge.py").write_text(FAKE_JUDGE, encoding="utf-8")
    (tmp_path / "prompts").mkdir(exist_ok=True)
    write(tmp_path / "prompts" / "v0.md", "template body {{reply}}")
    return tmp_path
