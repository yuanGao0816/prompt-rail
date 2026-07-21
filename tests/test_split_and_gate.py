# -*- coding: utf-8 -*-
"""Offline tests for prompt-rail split filtering and dual gate (no model calls)."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gate  # noqa: E402
import run_eval  # noqa: E402


def test_filter_cases() -> None:
    cases = [
        {"name": "a", "split": "train"},
        {"name": "b", "split": "test"},
        {"name": "c"},  # default train
    ]
    train = run_eval.filter_cases(cases, "train")
    test = run_eval.filter_cases(cases, "test")
    assert [c["name"] for c in train] == ["a", "c"]
    assert [c["name"] for c in test] == ["b"]


def test_json_field_eq_assert() -> None:
    ok, _ = run_eval.run_assert(
        {"type": "json_field_eq", "field": "intent", "equals": "code_fix"},
        '{"intent":"code_fix"}',
    )
    bad, _ = run_eval.run_assert(
        {"type": "json_field_eq", "field": "intent", "equals": "code_fix"},
        '{"intent":"chat_consultation"}',
    )
    assert ok and not bad


def test_fingerprint_includes_split() -> None:
    s1 = {
        "cases": [{"name": "a", "split": "train", "vars": {}, "asserts": []}],
        "runner": "bash x",
        "threshold": 0.8,
    }
    s2 = {
        "cases": [{"name": "a", "split": "test", "vars": {}, "asserts": []}],
        "runner": "bash x",
        "threshold": 0.8,
    }
    assert run_eval.suite_fingerprint(s1) != run_eval.suite_fingerprint(s2)


def _run_json(agg: float, cases: list[tuple[str, float]], threshold: float = 0.8) -> dict:
    return {
        "suite_hash": "abc123",
        "aggregate_score": agg,
        "threshold": threshold,
        "results": [{"case": n, "score": s} for n, s in cases],
    }


def test_gate_overfit(tmp_path: Path | None = None) -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        files = {
            "bt": _run_json(0.60, [("t1", 0.60)]),
            "bte": _run_json(0.70, [("e1", 0.70)]),
            "ct": _run_json(0.90, [("t1", 0.90)]),
            "cte": _run_json(0.50, [("e1", 0.50)]),
        }
        paths = {}
        for key, payload in files.items():
            p = d / f"{key}.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            paths[key] = str(p)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "gate.py"),
                "--base-train",
                paths["bt"],
                "--base-test",
                paths["bte"],
                "--cand-train",
                paths["ct"],
                "--cand-test",
                paths["cte"],
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 3, proc.stdout + proc.stderr
        assert "OVERFIT" in proc.stdout


def test_gate_keep() -> None:
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        files = {
            "bt": _run_json(0.60, [("t1", 0.60)]),
            "bte": _run_json(0.70, [("e1", 0.70)]),
            "ct": _run_json(0.80, [("t1", 0.80)]),
            "cte": _run_json(0.72, [("e1", 0.72)]),
        }
        paths = {}
        for key, payload in files.items():
            p = d / f"{key}.json"
            p.write_text(json.dumps(payload), encoding="utf-8")
            paths[key] = str(p)

        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "gate.py"),
                "--base-train",
                paths["bt"],
                "--base-test",
                paths["bte"],
                "--cand-train",
                paths["ct"],
                "--cand-test",
                paths["cte"],
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert "KEEP" in proc.stdout


if __name__ == "__main__":
    test_filter_cases()
    test_json_field_eq_assert()
    test_fingerprint_includes_split()
    test_gate_overfit()
    test_gate_keep()
    print("ok")
