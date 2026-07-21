#!/usr/bin/env python3
"""Compare two prompt-rail result files (same split) for keep-vs-revert.

For train/test dual-gate decisions, prefer scripts/gate.py instead.


Reads two --out JSON files (baseline, candidate) and prints a per-case
delta plus an overall verdict. A change is only worth keeping if it
improves the aggregate WITHOUT regressing any case below threshold —
this guards against the classic trap of fixing one case while silently
breaking another.

Exit code: 0 = candidate is a safe improvement (keep), 1 = revert.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def index(summary: dict) -> dict:
    return {r["case"]: r for r in summary.get("results", []) if "score" in r}


def main() -> int:
    ap = argparse.ArgumentParser(description="diff two prompt-rail runs (same split)")
    ap.add_argument("baseline", help="baseline results JSON (--out from prior run)")
    ap.add_argument("candidate", help="candidate results JSON")
    ap.add_argument("--min-gain", type=float, default=0.0,
                    help="min aggregate gain to count as improvement")
    ap.add_argument("--force", action="store_true",
                    help="diff even if the two runs used different suites (unsafe)")
    args = ap.parse_args()

    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    cand = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    threshold = cand.get("threshold", base.get("threshold", 0.8))

    # Suite-fingerprint guard: comparing scores from two different suites is
    # meaningless. If the suite changed between these runs, the deltas below
    # are noise, not signal — refuse to render a misleading verdict.
    bh = base.get("suite_hash")
    ch = cand.get("suite_hash")
    if bh and ch and bh != ch:
        print("⚠  SUITE MISMATCH — these runs were scored against different suites:")
        print(f"     baseline suite_hash = {bh}")
        print(f"     candidate suite_hash = {ch}")
        print("   Their scores are NOT comparable. The suite changed, so you must")
        print("   re-baseline: re-run the prior best version against the current")
        print("   suite, then diff against that. Aborting.")
        if not args.force:
            return 2
        print("   (--force given: continuing anyway; treat the diff as untrustworthy.)\n")

    bi, ci = index(base), index(cand)
    cases = sorted(set(bi) | set(ci))

    regressions, improvements, new_fails = [], [], []
    print(f"{'case':<28} {'base':>6} {'cand':>6} {'Δ':>7}")
    print("-" * 50)
    for name in cases:
        b = bi.get(name, {}).get("score")
        c = ci.get(name, {}).get("score")
        bs = f"{b:.2f}" if b is not None else "  — "
        cs = f"{c:.2f}" if c is not None else "  — "
        if b is not None and c is not None:
            delta = c - b
            arrow = "↑" if delta > 1e-6 else ("↓" if delta < -1e-6 else " ")
            print(f"{name:<28} {bs:>6} {cs:>6} {delta:>+6.2f}{arrow}")
            if delta < -1e-6:
                regressions.append((name, b, c))
            elif delta > 1e-6:
                improvements.append((name, b, c))
            # newly dropped below threshold while it was passing before
            if b >= threshold and c < threshold:
                new_fails.append((name, b, c))
        else:
            print(f"{name:<28} {bs:>6} {cs:>6}    n/a")

    bg = base.get("aggregate_score", 0.0)
    cg = cand.get("aggregate_score", 0.0)
    gain = cg - bg
    print("-" * 50)
    print(f"{'AGGREGATE':<28} {bg:>6.2f} {cg:>6.2f} {gain:>+6.2f}")

    keep = gain >= args.min_gain and not new_fails
    print()
    if new_fails:
        print("⚠  NEW FAILURES (passing → failing):")
        for name, b, c in new_fails:
            print(f"     {name}: {b:.2f} → {c:.2f}")
    if regressions and not new_fails:
        print("•  Regressions (still above threshold, watch these):")
        for name, b, c in regressions:
            print(f"     {name}: {b:.2f} → {c:.2f}")

    verdict = "KEEP" if keep else "REVERT"
    why = (
        "improves aggregate with no new failures" if keep
        else ("introduces new failures" if new_fails else f"gain {gain:+.3f} < min {args.min_gain}")
    )
    print(f"\n{verdict}  ({why})")
    return 0 if keep else 1


if __name__ == "__main__":
    sys.exit(main())
