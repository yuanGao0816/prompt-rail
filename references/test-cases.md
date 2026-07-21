# Test cases & the eval suite

The suite is the authority your iteration loop obeys. If the suite is wrong, every decision built on it is wrong — so this file is about building a suite that actually measures what "good" means for your task.

**prompt-rail addition:** every case declares `split: train | test`. Train drives rewrite; test is holdout. See `anti-overfit.md`.

## Suite schema

A suite is YAML (or JSON) with this shape. `run_eval.py` reads it directly.

```yaml
prompt_file: prompts/v0.md      # path relative to the suite file; --prompt overrides it
runner: bash runner.sh           # command; gets JSON on stdin, prints completion on stdout
dual_gate: true
threshold: 0.8                   # fallback
thresholds:
  train: 0.90
  test: 0.92

# Scoring weights. If a judge is configured, default split is 0.5/0.5;
# with no judge, asserts get full weight. Set explicitly to be safe.
weight_asserts: 0.6
weight_judge: 0.4

judge:                           # optional — omit the whole block for assert-only suites
  command: bash judge.sh
  rubric: |                      # default rubric; a case can override with its own `rubric:`
    Score 0..1. Reward outputs that stay in the character's first-person voice,
    advance the scene by one concrete beat, and never speak/act for the user.
    Penalize repetition of the previous turn's opener, actions, or phrasing.

cases:
  - name: repeat-opener          # unique, kebab-case; shows up in reports and diffs
    split: train                 # REQUIRED in prompt-rail: train | test
    vars:                        # substituted into the template: {{key}} and #key#
      chat_histories: '[{"role":"user","content":"..."},{"role":"assistant","content":"I lean in..."}]'
      language_type: "en"
    asserts:
      - {type: max_words, value: 45}
      - {type: not_regex, value: "^I lean in", case_sensitive: true}
    # optional per-case rubric override:
    rubric: |
      In addition to the default rubric, heavily penalize any opener that
      echoes "I lean in" from the history above.
```

`vars` are rendered into the template with both `{{key}}` and `#key#` placeholders, so the same suite works whether the prompt uses Handlebars-style or this repo's `#chatHistories#`-style markers.

## Assert types (deterministic, fast, free)

These run with no model call. Prefer them for anything mechanically checkable — they're the cheap, stable backbone of the suite.

| type | passes when | use for |
|---|---|---|
| `contains` | value is a substring | required token, required section header |
| `not_contains` | value is absent | forbidden word, leaked instruction text |
| `regex` | pattern matches | format shape, required structure |
| `not_regex` | pattern does **not** match | forbidden opener, banned pattern |
| `max_words` / `min_words` | whitespace word count in range | length-drift control |
| `max_chars` | char length ≤ value | hard output budgets |
| `line_count_max` | non-empty lines ≤ value | "≤3 sentences", reply-count caps |
| `json_valid` | output parses as JSON | structured-output prompts |
| `json_field_eq` | `json.loads(output)[field] == equals` | intent / label classification |

`json_field_eq` example: `{type: json_field_eq, field: intent, equals: code_fix}`

All string matches are case-insensitive unless you pass `case_sensitive: true`. A case can hold any number of asserts; the assert sub-score is `passed / total`.

## Turning a vague quality into a testable case

This is the skill. The user says "make it less repetitive" — that's not testable until you decompose it:

1. **Find a concrete instance.** Pull a real failing output. "It repeated the opener *I lean in closer* two turns running."
2. **Split mechanical from subjective.**
   - Mechanical → assert. `{type: not_regex, value: "I lean in", case_sensitive: false}` for the specific phrase; or a structural check.
   - Subjective ("feels samey even when words differ") → judge rubric line: *"Penalize outputs whose rhythm, action, or emotional beat duplicates the previous assistant turn, even if wording differs."*
3. **Anchor with the real history.** Put the actual prior turn in `vars` so the case reproduces the exact condition that triggered the failure.
4. **Add a regression guard.** Include a case the prompt already handles well, so an over-aggressive anti-repetition edit that flattens persona gets caught.

A failure mode without a case is a failure mode you are not fixing — you're just hoping.

## Judge rubric design

The judge is for qualities no assert can capture: voice, coherence, persona fidelity, helpfulness, tone. Keep rubrics:

- **Scored 0..1 with described anchors.** Tell the judge what 0, 0.5, 1 look like. "1.0 = stays fully in persona and advances the scene; 0.5 = in persona but static/no progression; 0.0 = breaks persona or acts for the user."
- **Specific to the failure.** A generic "is this good?" rubric returns noise. Name the exact thing: subject anchoring, opener diversity, escalation pacing.
- **One concern per rubric line.** Mirrors the one-hypothesis rule — lets you see which dimension moved.
- **Calibrated against the baseline.** Before trusting judge scores, eyeball 2–3 cases: does the judge's score match your read? If not, the rubric — not the prompt — is what to fix first.

Asserts catch *did it break a rule*; the judge catches *is it actually good*. You usually want both, which is why the default weight split exists.

## Coverage checklist

Before you trust a baseline, confirm the suite has:
- [ ] Every case has `split: train` or `split: test`.
- [ ] Each label / failure mode appears in **both** splits when possible.
- [ ] Dangerous misroutes are represented in **test**.
- [ ] One case per named failure mode from FRAME.
- [ ] At least one regression-guard case the prompt already passes.
- [ ] Real input samples in `vars`, not invented ones, where they exist.
- [ ] Deterministic asserts for every hard constraint.
- [ ] A judge rubric only for genuinely subjective qualities (don't judge what you can assert).
- [ ] Train/test thresholds that the baseline does **not** already clear (else nothing to optimize).
