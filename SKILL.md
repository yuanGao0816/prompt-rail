---
name: prompt-rail
description: >-
  Optimize prompts with a measured train/test dual-gate loop that resists
  memorizing eval cases. Use when the user wants to write or improve a prompt,
  tune a system prompt, build prompt evals with holdout, prevent prompt
  overfitting/背题, run prompt-rail, or iterate intent-classification prompts
  with separate train and test suites. Fork of prompt-smith plus anti-overfit rails.
---

# Prompt Rail

可度量的 prompt 迭代闭环，并加上**防背题护栏（rails）**：

- 继承 prompt-smith：冻结评测集、每轮一假设、分数不升则回退、`suite_hash` 守卫
- 新增：`train` / `test` 切开、双门槛、`OVERFIT` 门禁、改写四纪律

```
FRAME → RULES → PLAN(suite with train|test) → DRAFT/ADOPT v0
     → BASELINE(train+test)
     → [ DIAGNOSE(train only) → HYPOTHESIZE → EDIT(one change, anti-overfit)
         → MEASURE(train) → MEASURE(test) → GATE(KEEP|REVERT|OVERFIT) ]*
     → CONVERGE(dual thresholds)
```

> **Non-negotiable**
> 1. Never change prompt and suite in the same iteration.
> 2. One hypothesis per iteration.
> 3. **Rewrite signals come only from train.** Test is holdout.
> 4. Never paste train/test case surface forms into the prompt to chase score.
> 5. `train↑` + `test↓` ⇒ **OVERFIT** ⇒ revert, even if train looks great.

Load `references/anti-overfit.md` before the first rewrite. Load other refs as needed.

## Workspace layout

```
<workdir>/                          # default: ./prompt-rail/<name>/
  config.env
  suite.yaml                        # every case has split: train|test — FROZEN after baseline
  runner.sh / judge.sh
  prompts/v0.md, v1.md, ...
  runs/v0.train.json, v0.test.json, ...
  registry.jsonl
  LOG.md
```

Skill root (scripts live here): resolve from this skill's install path, e.g.
`~/.agents/skills/prompt-rail/scripts/` (or wherever your agent installed the skill).

## Step 1 — FRAME / RULES / PLAN

Same intent alignment as prompt-smith (task, failure modes, hard vs soft rules).
Additionally:

1. Collect **gold cases** with expected labels/outputs. Prefer real logs.
2. **Split before baseline** (~60–80% train / remainder test). Stratify by label.
   Put high-cost failure modes (dangerous misroutes) into **test** as a gate.
3. Draft `suite.yaml` from `assets/suite.template.yaml`. Every case needs `split:`.
4. Set `thresholds.train` / `thresholds.test` and `dual_gate: true`.
5. Copy `assets/config.template.env` → `config.env`, `runner.sh`, `judge.sh`.
6. Smoke-test runner/judge on one case.
7. **Show the user the train vs test case lists for approval** before baselining.

Classification tasks: prefer `json_valid` + `json_field_eq` over LLM-as-judge.
See `references/test-cases.md`.

## Step 1c — DRAFT v0

If a prompt exists → `prompts/v0.md`. Else draft the **shortest** prompt that
could pass the suite (`references/authoring.md`). Do not embed eval case text.

## Step 2 — BASELINE

```bash
SK=~/.agents/skills/prompt-rail   # or this skill's install path
python3 $SK/scripts/run_eval.py <workdir>/suite.yaml \
  --prompt <workdir>/prompts/v0.md --split train --out <workdir>/runs/v0.train.json
python3 $SK/scripts/run_eval.py <workdir>/suite.yaml \
  --prompt <workdir>/prompts/v0.md --split test  --out <workdir>/runs/v0.test.json
python3 $SK/scripts/registry.py record <workdir> --version v0 --decision BASELINE \
  --reason "initial dual baseline" --run runs/v0.train.json \
  --train-run runs/v0.train.json --test-run runs/v0.test.json
```

Record both scores in `LOG.md`. Suite + runner are now frozen.

If both splits already pass: suite is probably too lax → tighten, re-baseline.

## Step 3 — ITERATION LOOP

Each pass:

1. **DIAGNOSE (train only)** — Open lowest train cases in `runs/vBEST.train.json`.
   Do **not** mine test failures for edit ideas (test informs gate only).
2. **HYPOTHESIZE** — In `LOG.md`: cause → one edit → expected train cases to move.
   Apply the four disciplines in `references/anti-overfit.md`.
3. **EDIT** — Copy best → `prompts/v{N+1}.md`; one change only.
   Prefer abstract rules over exemplars; ≤1 placeholder few-shot per round.
4. **MEASURE**
   ```bash
   python3 $SK/scripts/run_eval.py <workdir>/suite.yaml \
     --prompt <workdir>/prompts/v{N+1}.md --split train --out <workdir>/runs/v{N+1}.train.json
   python3 $SK/scripts/run_eval.py <workdir>/suite.yaml \
     --prompt <workdir>/prompts/v{N+1}.md --split test  --out <workdir>/runs/v{N+1}.test.json
   ```
5. **GATE**
   ```bash
   python3 $SK/scripts/gate.py \
     --base-train <workdir>/runs/vBEST.train.json --base-test <workdir>/runs/vBEST.test.json \
     --cand-train <workdir>/runs/v{N+1}.train.json --cand-test <workdir>/runs/v{N+1}.test.json
   ```
   - exit 0 `KEEP` → new best  
   - exit 1 `REVERT` → discard  
   - exit 3 `OVERFIT` → discard; next hypothesis must abstract a rule, not add cases
6. **LOG** — `registry.py record` with decision `KEPT` / `REVERTED` / `OVERFIT`,
   plus train/test run paths. Append narrative to `LOG.md`.

Same-split case diffs: `diff_runs.py` (optional). Dual decision authority is `gate.py`.

Stuck after two failed rounds → break-the-loop protocol in `references/iteration-loop.md`,
plus re-check whether the suite itself is teaching memorization.

## Step 4 — CONVERGE

Stop when:

- `thresholds.train` and `thresholds.test` both cleared, and last 1–2 gates gave no KEEP, or
- diminishing returns / noise floor, or
- remaining misses are model-capability limits (say so explicitly).

Deliver:

1. Winning prompt path (`registry.py best`)
2. Final train/test scores and residual failures
3. Confirmation: prompt contains **no** verbatim holdout/train case strings
4. `LOG.md` + `registry.jsonl`

Update any live prompt pointer **only after user confirmation**.

## LOG.md template

```markdown
# Prompt-rail log: <name>

Task: <one line>
Suite: train=N / test=M  • thresholds train/test  • Runner: <what>

## Baseline v0 — train 0.62 / test 0.58
- train ✗ ...
- test  ✗ ... (holdout — do not rewrite from these yet)

## v1 — train 0.80 / test 0.55  [OVERFIT]
Hypothesis: ...
Result: train↑ test↓. Reverted. Next: abstract boundary rule, no case paste.

## v2 — train 0.78 / test 0.76  [KEPT]
...
```

## Bundled resources

| Path | Role |
|------|------|
| `scripts/run_eval.py` | Eval engine; `--split train\|test\|all`; `by_split` in JSON |
| `scripts/gate.py` | Dual-gate KEEP / REVERT / OVERFIT |
| `scripts/diff_runs.py` | Same-split per-case diff |
| `scripts/registry.py` | Ledger incl. OVERFIT + train/test scores |
| `references/anti-overfit.md` | Train/test + rewrite four disciplines |
| `references/test-cases.md` | Suite schema + asserts |
| `references/iteration-loop.md` | Noise, keep/revert edges |
| `references/authoring.md` | Drafting v0 |
| `references/optimization-techniques.md` | Edit moves (still subject to anti-overfit) |
| `references/runners.md` | Runner/judge providers |
| `assets/*` | Templates to copy into workdir |

Engine lineage: forked from Banner-Wang/prompt-smith; anti-overfit rails are prompt-rail specific.
