#!/usr/bin/env python3
"""prompt-rail structured ledger (registry.jsonl).

The companion to the human-readable LOG.md. One JSON object per line, one
line per prompt version, so the iteration history is machine-queryable:
"which version scored highest", "what was v3's hypothesis", "which scores
were measured against the same suite".

Why JSONL: append-only, git-diffable, zero dependencies, and `jq`-queryable.
LOG.md stays as the narrative ("why we did this"); registry.jsonl is the data
("what happened, measured"). They serve different readers.

Usage
-----
Record a version (usually right after run_eval.py produces runs/vN.json):

    python3 registry.py record <workdir> \
        --version v1 --parent v0 \
        --hypothesis "length drift <- no budget near output -> add cap last" \
        --decision KEPT --reason "length-drift 0.55->0.95, no regressions" \
        --run runs/v1.json

The score, per-case breakdown, and suite_hash are read straight out of the
--run JSON, so the ledger can never disagree with the actual eval result.

Query:

    python3 registry.py log   <workdir>            # full history, newest last
    python3 registry.py best  <workdir>            # highest-scoring KEPT version
    python3 registry.py show  <workdir> --version v3
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path


LEDGER = "registry.jsonl"


def _ledger_path(workdir: Path) -> Path:
    return workdir / LEDGER


def _read(workdir: Path) -> list[dict]:
    path = _ledger_path(workdir)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _append(workdir: Path, row: dict) -> None:
    path = _ledger_path(workdir)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_run(workdir: Path, run_rel: str) -> dict:
    run_path = (workdir / run_rel) if not Path(run_rel).is_absolute() else Path(run_rel)
    return json.loads(run_path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_record(args) -> int:
    workdir = Path(args.workdir)
    run = _load_run(workdir, args.run)

    per_case = {
        r["case"]: r.get("score")
        for r in run.get("results", [])
        if "score" in r
    }
    row = {
        "version": args.version,
        "timestamp": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "parent": args.parent,
        "hypothesis": args.hypothesis,
        "decision": args.decision,  # KEPT | REVERTED | BASELINE | OVERFIT
        "decision_reason": args.reason,
        "aggregate_score": run.get("aggregate_score"),
        "by_split": run.get("by_split"),
        "passed_cases": run.get("passed_cases"),
        "total_cases": run.get("total_cases"),
        "per_case": per_case,
        "suite_hash": run.get("suite_hash"),
        "prompt_file": run.get("prompt_file"),
        "run_file": args.run,
    }
    if args.train_run:
        train_run = _load_run(workdir, args.train_run)
        row["train_score"] = train_run.get("aggregate_score")
        row["train_run"] = args.train_run
    if args.test_run:
        test_run = _load_run(workdir, args.test_run)
        row["test_score"] = test_run.get("aggregate_score")
        row["test_run"] = args.test_run
    # de-dupe: if this version was already recorded, the newest line wins on
    # read (best/show scan in order), but warn so the user notices a re-record.
    existing = [r for r in _read(workdir) if r.get("version") == args.version]
    if existing:
        print(f"note: {args.version} already in ledger; appending a new record "
              f"(the latest wins on query).", file=sys.stderr)
    _append(workdir, row)
    print(f"recorded {args.version}  score={row['aggregate_score']}  "
          f"decision={args.decision}  suite={row['suite_hash']}")
    return 0


def _latest_by_version(rows: list[dict]) -> dict:
    """Collapse to the last-recorded row per version (handles re-records)."""
    out: dict[str, dict] = {}
    for r in rows:
        out[r.get("version")] = r
    return out


def cmd_log(args) -> int:
    rows = _read(Path(args.workdir))
    if not rows:
        print("(empty ledger)")
        return 0
    print(f"{'ver':<6} {'score':>6} {'cases':>7} {'decision':<9} {'suite':<13} hypothesis")
    print("-" * 78)
    for r in rows:
        score = r.get("aggregate_score")
        score_s = f"{score:.3f}" if isinstance(score, (int, float)) else "  —  "
        cases = f"{r.get('passed_cases','?')}/{r.get('total_cases','?')}"
        hyp = (r.get("hypothesis") or "")[:34]
        print(f"{r.get('version',''):<6} {score_s:>6} {cases:>7} "
              f"{r.get('decision',''):<9} {str(r.get('suite_hash',''))[:12]:<13} {hyp}")
    return 0


def cmd_best(args) -> int:
    ordered = list(_latest_by_version(_read(Path(args.workdir))).values())
    kept = [(i, r) for i, r in enumerate(ordered)
            if r.get("decision") in ("KEPT", "BASELINE")
            and isinstance(r.get("aggregate_score"), (int, float))]
    if not kept:
        print("(no KEPT versions yet)")
        return 1
    # warn if the kept versions span multiple suites — their scores aren't
    # all on the same ruler, so "best" across them could be apples-to-oranges.
    suites = {r.get("suite_hash") for _, r in kept}
    # tie-break on recency: when two versions score equal, the later-recorded
    # one wins — an iteration that matched the baseline is still the version
    # you carried forward, not the baseline itself.
    _, best = max(kept, key=lambda ir: (ir[1]["aggregate_score"], ir[0]))
    if len(suites) > 1:
        print("⚠  kept versions span multiple suite_hashes — scores below are not "
              "all on the same ruler:", ", ".join(str(s)[:12] for s in suites))
    print(f"best: {best['version']}  score={best['aggregate_score']:.3f}  "
          f"suite={best.get('suite_hash')}  ({best.get('decision_reason','')})")
    return 0


def cmd_show(args) -> int:
    rows = _latest_by_version(_read(Path(args.workdir)))
    row = rows.get(args.version)
    if not row:
        print(f"version {args.version} not in ledger")
        return 1
    print(json.dumps(row, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="prompt-rail structured ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("record", help="append a version record (reads score from --run)")
    p.add_argument("workdir")
    p.add_argument("--version", required=True)
    p.add_argument("--parent", default=None, help="version this was derived from")
    p.add_argument("--hypothesis", default="", help="cause -> edit -> expected")
    p.add_argument(
        "--decision",
        required=True,
        choices=["KEPT", "REVERTED", "BASELINE", "OVERFIT"],
    )
    p.add_argument("--reason", default="", help="why kept/reverted/overfit")
    p.add_argument("--run", required=True, help="path to the run_eval --out JSON")
    p.add_argument("--train-run", default=None, help="optional train-only run JSON")
    p.add_argument("--test-run", default=None, help="optional test-only run JSON")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("log", help="print the full version history")
    p.add_argument("workdir")
    p.set_defaults(func=cmd_log)

    p = sub.add_parser("best", help="print the highest-scoring KEPT version")
    p.add_argument("workdir")
    p.set_defaults(func=cmd_best)

    p = sub.add_parser("show", help="print one version's full record")
    p.add_argument("workdir")
    p.add_argument("--version", required=True)
    p.set_defaults(func=cmd_show)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
