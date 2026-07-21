#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prompt-rail eval engine (forked from prompt-smith).

Renders a prompt across a suite, scores with asserts + optional judge, and
supports train/test splits so rewrite loops can avoid memorizing the eval set.

Contracts
---------
runner: JSON stdin {"prompt","case","vars"} -> completion text on stdout
judge:  JSON stdin {"prompt","output","rubric","case","vars"}
        -> JSON stdout {"score": 0..1, "reasons": str}

Exit code:
  --split train|test : 0 if that split's aggregate >= its threshold
  --split all        : 0 only if train AND test both pass (dual gate)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


def load_suite(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except ImportError:
            sys.exit(
                "ERROR: suite is YAML but PyYAML is not installed.\n"
                "Run `pip install pyyaml`, or convert the suite to .json."
            )
        return yaml.safe_load(text)
    return json.loads(text)


def suite_fingerprint(suite: dict) -> str:
    """Hash score-affecting suite parts. Includes per-case split + dual thresholds."""
    material = {
        "cases": [
            {
                "name": c.get("name"),
                "split": c.get("split", "train"),
                "vars": c.get("vars", {}),
                "asserts": c.get("asserts", []),
                "rubric": c.get("rubric"),
            }
            for c in suite.get("cases", [])
        ],
        "runner": suite.get("runner"),
        "judge": suite.get("judge"),
        "weight_judge": suite.get("weight_judge"),
        "weight_asserts": suite.get("weight_asserts"),
        "threshold": suite.get("threshold"),
        "thresholds": suite.get("thresholds"),
        "dual_gate": suite.get("dual_gate", True),
    }
    blob = json.dumps(material, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def render(template: str, variables: dict) -> str:
    out = template
    for key, val in (variables or {}).items():
        out = out.replace("{{" + key + "}}", str(val))
        out = out.replace("#" + key + "#", str(val))
    return out


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def run_assert(spec: dict, output: str) -> tuple[bool, str]:
    kind = spec.get("type")
    val = spec.get("value")
    o = output if spec.get("case_sensitive") else output.lower()
    needle = str(val) if spec.get("case_sensitive") else str(val).lower()

    if kind == "contains":
        return (needle in o, f"contains {val!r}")
    if kind == "not_contains":
        return (needle not in o, f"not_contains {val!r}")
    if kind == "regex":
        flags = 0 if spec.get("case_sensitive") else re.IGNORECASE
        return (re.search(str(val), output, flags) is not None, f"regex {val!r}")
    if kind == "not_regex":
        flags = 0 if spec.get("case_sensitive") else re.IGNORECASE
        return (re.search(str(val), output, flags) is None, f"not_regex {val!r}")
    if kind == "max_words":
        wc = word_count(output)
        return (wc <= int(val), f"max_words {val} (got {wc})")
    if kind == "min_words":
        wc = word_count(output)
        return (wc >= int(val), f"min_words {val} (got {wc})")
    if kind == "max_chars":
        return (len(output) <= int(val), f"max_chars {val} (got {len(output)})")
    if kind == "json_valid":
        try:
            json.loads(output)
            return (True, "json_valid")
        except Exception as exc:  # noqa: BLE001
            return (False, f"json_valid failed: {exc}")
    if kind == "line_count_max":
        n = len([ln for ln in output.splitlines() if ln.strip()])
        return (n <= int(val), f"line_count_max {val} (got {n})")
    if kind == "json_field_eq":
        # value: {"field": "intent", "equals": "code_fix"}
        try:
            data = json.loads(output)
            field = spec["field"]
            expected = spec["equals"]
            actual = data.get(field) if isinstance(data, dict) else None
            return (actual == expected, f"json_field_eq {field}=={expected!r} (got {actual!r})")
        except Exception as exc:  # noqa: BLE001
            return (False, f"json_field_eq failed: {exc}")
    return (False, f"unknown assert type {kind!r}")


def call_cmd(command: str, payload: dict, timeout: int) -> str:
    proc = subprocess.run(
        command,
        shell=True,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {command}\n{proc.stderr.strip()}"
        )
    return proc.stdout


def run_judge(command: str, payload: dict, timeout: int) -> tuple[float, str]:
    raw = call_cmd(command, payload, timeout)
    try:
        data = json.loads(raw)
        return float(data["score"]), str(data.get("reasons", ""))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"judge returned unparseable output: {raw!r} ({exc})")


def resolve_thresholds(suite: dict) -> dict[str, float]:
    default = float(suite.get("threshold", 0.8))
    th = suite.get("thresholds") or {}
    return {
        "train": float(th.get("train", default)),
        "test": float(th.get("test", default)),
        "default": default,
    }


def filter_cases(cases: list[dict], split: str) -> list[dict]:
    if split == "all":
        return list(cases)
    out = []
    for case in cases:
        case_split = (case.get("split") or "train").lower()
        if case_split == split:
            out.append(case)
    return out


def summarize_split(results: list[dict], threshold: float) -> dict:
    scored = [r for r in results if "score" in r]
    agg = sum(r["score"] for r in scored) / len(scored) if scored else 0.0
    passed_cases = sum(1 for r in scored if r["score"] >= threshold)
    return {
        "aggregate_score": round(agg, 4),
        "threshold": threshold,
        "passed_cases": passed_cases,
        "total_cases": len(scored),
        "pass": agg >= threshold if scored else False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="prompt-rail eval engine")
    ap.add_argument("suite", help="path to suite .yaml/.json")
    ap.add_argument("--prompt", help="override prompt_file from the suite")
    ap.add_argument("--out", help="write full JSON results here")
    ap.add_argument(
        "--split",
        choices=["train", "test", "all"],
        default="all",
        help="which cases to run (default: all, dual-gated)",
    )
    ap.add_argument("--timeout", type=int, default=120, help="per-command timeout (s)")
    ap.add_argument("--quiet", action="store_true", help="only print the summary line")
    args = ap.parse_args()

    suite_path = Path(args.suite)
    suite = load_suite(suite_path)
    base = suite_path.parent

    prompt_file = args.prompt or suite["prompt_file"]
    prompt_path = (
        (base / prompt_file) if not Path(prompt_file).is_absolute() else Path(prompt_file)
    )
    template = prompt_path.read_text(encoding="utf-8")

    runner = suite["runner"]
    judge_cfg = suite.get("judge") or {}
    judge_cmd = judge_cfg.get("command")
    rubric = judge_cfg.get("rubric", "")

    w_judge = float(suite.get("weight_judge", 0.5 if judge_cmd else 0.0))
    w_assert = float(suite.get("weight_asserts", 1.0 - w_judge))
    if w_judge + w_assert == 0:
        w_assert = 1.0
    thresholds = resolve_thresholds(suite)
    dual_gate = bool(suite.get("dual_gate", True))

    all_cases = suite.get("cases") or []
    missing_split = [c.get("name", "?") for c in all_cases if not c.get("split")]
    if missing_split and not args.quiet:
        print(
            f"note: cases without split= default to train: {', '.join(missing_split[:8])}"
            + ("…" if len(missing_split) > 8 else ""),
            file=sys.stderr,
        )

    cases = filter_cases(all_cases, args.split)
    if not cases:
        sys.exit(f"ERROR: no cases for --split {args.split}")

    results: list[dict] = []
    for case in cases:
        name = case.get("name", "case")
        case_split = (case.get("split") or "train").lower()
        variables = case.get("vars", {})
        rendered = render(template, variables)

        try:
            output = call_cmd(
                runner,
                {"prompt": rendered, "case": name, "vars": variables},
                args.timeout,
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "case": name,
                    "split": case_split,
                    "error": str(exc),
                    "score": 0.0,
                }
            )
            if not args.quiet:
                print(f"  ✗ {name}[{case_split}]: RUNNER ERROR — {exc}")
            continue

        assert_specs = case.get("asserts", [])
        assert_details = [(*run_assert(s, output), s) for s in assert_specs]
        passed = sum(1 for ok, _, _ in assert_details if ok)
        assert_score = (passed / len(assert_specs)) if assert_specs else None

        judge_score = None
        judge_reasons = ""
        case_rubric = case.get("rubric", rubric)
        if judge_cmd and case_rubric:
            judge_score, judge_reasons = run_judge(
                judge_cmd,
                {
                    "prompt": rendered,
                    "output": output,
                    "rubric": case_rubric,
                    "case": name,
                    "vars": variables,
                },
                args.timeout,
            )

        parts, weights = [], []
        if assert_score is not None:
            parts.append(assert_score)
            weights.append(w_assert)
        if judge_score is not None:
            parts.append(judge_score)
            weights.append(w_judge)
        score = (
            sum(p * w for p, w in zip(parts, weights)) / sum(weights) if weights else 0.0
        )

        case_threshold = thresholds.get(case_split, thresholds["default"])
        results.append(
            {
                "case": name,
                "split": case_split,
                "score": round(score, 4),
                "assert_score": assert_score,
                "judge_score": judge_score,
                "judge_reasons": judge_reasons,
                "failed_asserts": [d for ok, d, _ in assert_details if not ok],
                "output": output,
            }
        )

        if not args.quiet:
            mark = "✓" if score >= case_threshold else "✗"
            bits = []
            if assert_score is not None:
                bits.append(f"asserts {passed}/{len(assert_specs)}")
            if judge_score is not None:
                bits.append(f"judge {judge_score:.2f}")
            print(f"  {mark} {name}[{case_split}]: {score:.2f} ({', '.join(bits)})")
            for d in (d for ok, d, _ in assert_details if not ok):
                print(f"      ✗ {d}")
            if judge_reasons and judge_score is not None and judge_score < case_threshold:
                print(f"      judge: {judge_reasons.strip()[:300]}")

    by_split: dict[str, dict] = {}
    for split_name in ("train", "test"):
        split_results = [r for r in results if r.get("split") == split_name]
        if split_results:
            by_split[split_name] = summarize_split(
                split_results, thresholds[split_name]
            )

    if args.split in ("train", "test"):
        overall = by_split.get(
            args.split,
            summarize_split([], thresholds[args.split]),
        )
        overall_pass = overall["pass"]
        agg = overall["aggregate_score"]
        thr = overall["threshold"]
        passed_cases = overall["passed_cases"]
        total = overall["total_cases"]
    else:
        # all: aggregate across run cases for backward-compatible field,
        # but dual_gate decides pass.
        overall = summarize_split(results, thresholds["default"])
        agg = overall["aggregate_score"]
        thr = thresholds["default"]
        passed_cases = overall["passed_cases"]
        total = overall["total_cases"]
        if dual_gate:
            train_ok = by_split.get("train", {}).get("pass", False)
            test_ok = by_split.get("test", {}).get("pass", False)
            # If a split is missing entirely, fail closed when dual_gate is on.
            if "train" not in by_split or "test" not in by_split:
                overall_pass = False
                if not args.quiet:
                    print(
                        "⚠  dual_gate requires both train and test cases in the suite",
                        file=sys.stderr,
                    )
            else:
                overall_pass = train_ok and test_ok
        else:
            overall_pass = overall["pass"]

    summary = {
        "prompt_file": str(prompt_path),
        "suite_hash": suite_fingerprint(suite),
        "split_filter": args.split,
        "aggregate_score": round(agg, 4),
        "threshold": thr,
        "thresholds": thresholds,
        "dual_gate": dual_gate,
        "by_split": by_split,
        "passed_cases": passed_cases,
        "total_cases": total,
        "pass": overall_pass,
        "results": results,
    }

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    verdict = "PASS" if summary["pass"] else "FAIL"
    split_bits = "  ".join(
        f"{name}={info['aggregate_score']:.3f}"
        f"({'✓' if info['pass'] else '✗'}≥{info['threshold']})"
        for name, info in by_split.items()
    )
    print(
        f"\n{verdict}  filter={args.split}  aggregate={agg:.3f}  "
        f"cases={passed_cases}/{total}  prompt={prompt_path.name}"
    )
    if split_bits:
        print(f"  splits: {split_bits}")
    return 0 if summary["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
