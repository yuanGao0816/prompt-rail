#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prompt-rail dual-gate + overfit detector.

Compares a candidate against a baseline using SEPARATE train and test runs.

Decisions
---------
KEEP     — train improved (or flat within noise) with no new train failures,
           AND test did not drop beyond --max-test-drop
REVERT   — train did not improve, or new train failures
OVERFIT  — train improved but test dropped (classic memorization signal)

Usage
-----
    python3 gate.py \\
        --base-train runs/v0.train.json --base-test runs/v0.test.json \\
        --cand-train runs/v1.train.json --cand-test runs/v1.test.json

Exit codes: 0=KEEP, 1=REVERT, 3=OVERFIT, 2=suite mismatch
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def index(summary: dict) -> dict:
    return {r["case"]: r for r in summary.get("results", []) if "score" in r}


def new_failures(base: dict, cand: dict) -> list[tuple[str, float, float]]:
    threshold = cand.get("threshold", base.get("threshold", 0.8))
    bi, ci = index(base), index(cand)
    out = []
    for name, brow in bi.items():
        brow_s = brow.get("score")
        crow = ci.get(name)
        if crow is None or brow_s is None:
            continue
        c_s = crow.get("score")
        if c_s is None:
            continue
        if brow_s >= threshold and c_s < threshold:
            out.append((name, brow_s, c_s))
    return out


def check_suite(*runs: dict) -> str | None:
    hashes = {r.get("suite_hash") for r in runs if r.get("suite_hash")}
    if len(hashes) > 1:
        return ", ".join(sorted(str(h) for h in hashes))
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="prompt-rail dual gate")
    ap.add_argument("--base-train", required=True)
    ap.add_argument("--base-test", required=True)
    ap.add_argument("--cand-train", required=True)
    ap.add_argument("--cand-test", required=True)
    ap.add_argument("--min-train-gain", type=float, default=0.0)
    ap.add_argument(
        "--max-test-drop",
        type=float,
        default=0.02,
        help="test aggregate drop larger than this → OVERFIT (default 0.02)",
    )
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    bt, bte = load(args.base_train), load(args.base_test)
    ct, cte = load(args.cand_train), load(args.cand_test)

    mismatch = check_suite(bt, bte, ct, cte)
    if mismatch and not args.force:
        print(f"⚠  SUITE MISMATCH across runs: {mismatch}")
        print("   Re-baseline before gating. Aborting.")
        return 2

    b_train = float(bt.get("aggregate_score", 0.0))
    c_train = float(ct.get("aggregate_score", 0.0))
    b_test = float(bte.get("aggregate_score", 0.0))
    c_test = float(cte.get("aggregate_score", 0.0))
    train_gain = c_train - b_train
    test_delta = c_test - b_test
    fails = new_failures(bt, ct)

    print(f"{'':18} {'base':>7} {'cand':>7} {'Δ':>8}")
    print("-" * 44)
    print(f"{'train':18} {b_train:>7.3f} {c_train:>7.3f} {train_gain:>+7.3f}")
    print(f"{'test':18} {b_test:>7.3f} {c_test:>7.3f} {test_delta:>+7.3f}")
    if fails:
        print("\n⚠  NEW TRAIN FAILURES:")
        for name, b, c in fails:
            print(f"     {name}: {b:.2f} → {c:.2f}")

    # Decision tree
    if fails:
        decision, why, code = "REVERT", "new failures on train", 1
    elif train_gain < args.min_train_gain:
        decision, why, code = (
            "REVERT",
            f"train gain {train_gain:+.3f} < min {args.min_train_gain}",
            1,
        )
    elif test_delta < -args.max_test_drop:
        decision, why, code = (
            "OVERFIT",
            f"train↑ ({train_gain:+.3f}) but test↓ ({test_delta:+.3f}) "
            f"beyond max drop {args.max_test_drop}",
            3,
        )
    else:
        decision, why, code = (
            "KEEP",
            "train improved/flat with no new train fails; test held",
            0,
        )

    print(f"\n{decision}  ({why})")
    return code


if __name__ == "__main__":
    sys.exit(main())
