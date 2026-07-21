# The iteration loop in depth

This is the engine room of prompt-rail (forked from prompt-smith). SKILL.md
gives the loop; this file covers judgment calls. For train/test dual-gate and
OVERFIT, also read `anti-overfit.md` and use `scripts/gate.py`.

## What "one hypothesis" actually means

A hypothesis is a falsifiable triple:

```
CAUSE   — why the model produces the bad output (stated about the model's behavior, not the prompt text)
EDIT    — the single change you predict fixes it
EFFECT  — which case scores you expect to move, and in which direction
```

If you can't write all three, you're not ready to edit — you're guessing. "The
prompt feels cluttered" is not a cause. "The length cap appears on line 3, 600
tokens before the output instruction, so the model has forgotten it by
generation time → move the cap to the final instruction → expect length-drift
cases to rise, others flat" is.

The EFFECT clause is what makes the loop self-correcting. When the measured
result contradicts your predicted effect, you've learned something real about
the model, and that updates the *next* hypothesis. A kept change that moved a
different case than you predicted is suspicious — understand why before trusting it.

## Reading run JSON during DIAGNOSE

`runs/vN.json` has a `results` array; each entry carries the full `output`,
`failed_asserts`, `judge_score`, and `judge_reasons`. Diagnose from these, not
from re-reading the prompt:

- Sort cases by `score` ascending. The lowest is your target.
- Read its `output` verbatim. The failure is usually obvious once you see the
  actual text — and is often *not* what you assumed from the prompt.
- `failed_asserts` tells you the deterministic misses (too long, forbidden
  phrase present). `judge_reasons` tells you the subjective misses.
- Look for a pattern *across* low cases. One edit that fixes a pattern shared by
  three cases beats three edits each fixing one.

## Noise: the silent loop-killer

If the runner samples (temperature > 0), the same prompt scores differently run
to run. Acting on noise makes you "keep" changes that did nothing and "revert"
changes that helped.

- **Estimate the noise floor once.** Run the baseline suite 3× without changing
  anything. The spread in aggregate is your noise floor δ.
- **Only trust deltas larger than δ.** A move of +0.02 when δ is 0.05 is noise.
- **For near-threshold decisions, run 2–3× and average.** The engine writes one
  JSON per run; average the aggregates manually, or lower the runner temperature
  for eval (a good practice — eval with temperature 0 if the production use is
  also low-temperature, or if you only care about instruction-following).
- **Deterministic asserts are noise-free** when the output is stable; judge
  scores carry both runner noise and judge noise. Weight your confidence toward
  the asserts when they disagree.

## KEEP / REVERT decision table

| Aggregate | Any case regressed below threshold? | Action |
|-----------|-------------------------------------|--------|
| up by > δ | no  | **KEEP** — new best |
| up by > δ | yes | **REVERT** — you traded failures; re-target the original more surgically |
| within δ  | —   | **REVERT** — no real effect; don't accumulate inert complexity |
| down      | —   | **REVERT** — hypothesis wrong; record why |

Two subtleties:

- **Inert complexity is a cost.** A change that's within noise but adds three
  rules to the prompt is a *revert*, not a "harmless keep" — every added rule
  dilutes attention and risks future regressions. Keep the prompt as small as
  the score allows.
- **A regression below threshold is worse than a non-improvement above it.**
  Raising case A from 0.6→0.8 while dropping case B 0.9→0.75 (threshold 0.8) is a
  net loss even if the aggregate rose, because B now fails. The table treats any
  sub-threshold regression as a revert trigger for this reason.

## The break-the-loop protocol (two consecutive failures)

When two hypotheses in a row fail to produce a kept change, stop editing the
prompt. Continuing will just pile on patches. Work through this checklist in
order — each step questions a different layer:

1. **Re-read raw outputs with fresh eyes.** Is the failure actually what you've
   been targeting? A "repetition" problem is sometimes a "the model only has one
   thing to say given this input" problem — a content gap, not a phrasing rule.

2. **Audit the suite.** Is an assert testing something the task doesn't require?
   Is the judge rubric punishing good output or rewarding bad? A miscalibrated
   suite makes *every* hypothesis fail because you're optimizing the wrong target.
   - If the suite is wrong, fix it in its **own iteration**, then **re-baseline
     every kept version** against the corrected suite (scores before the fix are
     void). Mark this loudly in `LOG.md` — it's a reset, not a normal iteration.

3. **Audit the runner.** Truncated outputs (max_tokens too low), wrong stop
   sequences, temperature too high, a system/user role mismatch — these read as
   prompt failures but are harness bugs. Smoke-test the runner on a known-good
   input.

4. **Question the frame.** Maybe the prompt's whole structure fights the task.
   Consider a *structural rewrite* — different ordering, decomposition into
   stages, a different instruction paradigm — as a single deliberate hypothesis,
   rather than another one-line patch. Structural rewrites are the exception to
   "small edits"; make them consciously and measure the same way.

5. **Question feasibility.** Some failure modes can't be fully fixed by prompting
   — a small model may be incapable of the constraint, or two requirements may
   genuinely conflict (maximal creativity *and* a hard 20-word cap). Name the
   tradeoff to the user instead of burning iterations on an impossible target.

## When to stop (CONVERGE)

Converge when continuing costs more than it returns:

- All cases at/above threshold, and the last 1–2 hypotheses yielded no gain > δ.
- The only remaining failures are judge-subjective and within noise — further
  movement isn't reliably measurable, so you'd be optimizing noise.
- Two iterations of sub-δ improvement: diminishing returns. Ship the best.

Converging is a decision, not giving up. Record the final state honestly: which
failure modes the suite actually covers and verifies as fixed, and which remain.

## Resumability

Because every version, every run JSON, and the ledger are on disk, an
optimization run survives context loss. To resume: read `LOG.md` for the trail,
find the current best version (highest kept aggregate), and re-enter at DIAGNOSE.
Nothing about the loop depends on conversation memory.
