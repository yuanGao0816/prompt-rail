"""registry.py ledger behavior.

These lock in: a recorded version reads its score straight from the run JSON
(ledger can't disagree with the eval), `best` ignores REVERTED versions, and
the tie-break returns the *later* iteration rather than the baseline when two
versions score equally — the bug found during the original smoke test.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from conftest import registry  # noqa: E402


def _run_json(workdir: Path, name: str, score: float, suite_hash: str = "aaa") -> str:
    """Write a minimal run_eval-style result and return its relative path."""
    (workdir / "runs").mkdir(exist_ok=True)
    rel = f"runs/{name}.json"
    (workdir / rel).write_text(json.dumps({
        "prompt_file": f"prompts/{name}.md",
        "aggregate_score": score,
        "passed_cases": 1,
        "total_cases": 1,
        "suite_hash": suite_hash,
        "results": [{"case": "c", "score": score}],
    }), encoding="utf-8")
    return rel


def test_record_reads_score_from_run(tmp_path):
    r = _run_json(tmp_path, "v0", 0.62)
    proc = registry(tmp_path, "record", str(tmp_path),
                    "--version", "v0", "--decision", "BASELINE", "--run", r)
    assert proc.returncode == 0
    # show should reflect the score read from the run file, not anything passed in
    show = registry(tmp_path, "show", str(tmp_path), "--version", "v0")
    row = json.loads(show.stdout)
    assert row["aggregate_score"] == 0.62
    assert row["suite_hash"] == "aaa"


def test_best_ignores_reverted(tmp_path):
    registry(tmp_path, "record", str(tmp_path), "--version", "v0",
             "--decision", "BASELINE", "--run", _run_json(tmp_path, "v0", 0.60))
    registry(tmp_path, "record", str(tmp_path), "--version", "v1",
             "--decision", "KEPT", "--run", _run_json(tmp_path, "v1", 0.71))
    # a higher-scoring but REVERTED version must NOT win
    registry(tmp_path, "record", str(tmp_path), "--version", "v2",
             "--decision", "REVERTED", "--run", _run_json(tmp_path, "v2", 0.95))
    best = registry(tmp_path, "best", str(tmp_path))
    assert "v1" in best.stdout
    assert "v2" not in best.stdout


def test_best_tiebreak_prefers_later_version(tmp_path):
    """Equal scores: the later iteration wins over the baseline (the fixed bug)."""
    registry(tmp_path, "record", str(tmp_path), "--version", "v0",
             "--decision", "BASELINE", "--run", _run_json(tmp_path, "v0", 1.0))
    registry(tmp_path, "record", str(tmp_path), "--version", "v1",
             "--decision", "KEPT", "--run", _run_json(tmp_path, "v1", 1.0))
    best = registry(tmp_path, "best", str(tmp_path))
    assert "v1" in best.stdout
    # explicitly: not the baseline
    assert "best: v0" not in best.stdout


def test_best_warns_on_mixed_suites(tmp_path):
    registry(tmp_path, "record", str(tmp_path), "--version", "v0",
             "--decision", "BASELINE", "--run", _run_json(tmp_path, "v0", 0.6, "aaa"))
    registry(tmp_path, "record", str(tmp_path), "--version", "v1",
             "--decision", "KEPT", "--run", _run_json(tmp_path, "v1", 0.8, "bbb"))
    best = registry(tmp_path, "best", str(tmp_path))
    # kept versions span two suite_hashes -> the scores aren't on one ruler
    assert "multiple suite_hashes" in best.stdout or "not" in best.stdout.lower()
