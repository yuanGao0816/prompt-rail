# Runners & judges — the pluggable contract

The eval engine never talks to a model directly. It shells out to two commands you provide, so the same suite works against any model or API. Both read JSON on stdin and write to stdout.

## Runner contract
```
stdin  (JSON):  {"prompt": "<fully rendered prompt>", "case": "<name>", "vars": {...}}
stdout (text):  the model completion, raw. Nothing else.
exit 0 on success; non-zero makes the engine record a RUNNER ERROR for that case (scores 0).
```
The runner's only job: take a finished prompt string and return what the model said. All templating already happened — don't re-render. Print **only** the completion to stdout; send logs/debug to stderr or the engine will score your debug text.

## Judge contract (optional)
```
stdin  (JSON):  {"prompt", "output", "rubric", "case", "vars"}
stdout (JSON):  {"score": 0.0..1.0, "reasons": "<short why>"}
```
`score` must be a float in [0,1]. The engine blends it with the assert score by the suite's `weight_judge`/`weight_asserts`.

---

## You don't edit these scripts to switch models — you edit `config.env`

The bundled `assets/runner.sh` and `assets/judge.sh` are already written to **source `<workdir>/config.env` and branch on a provider field**, so switching from xAI to a local llama.cpp to the Claude CLI is a config edit, not a script edit. Copy `assets/config.template.env` to `<workdir>/config.env` and fill it in:

```bash
# RUNNER — runs the prompt under test
RUNNER_PROVIDER=openai_compatible    # openai_compatible | claude_cli
RUNNER_BASE=https://api.x.ai/v1
RUNNER_MODEL=grok-2-latest
RUNNER_API_KEY_ENV=XAI_API_KEY       # the NAME of the env var, never the key itself
RUNNER_TEMPERATURE=0

# JUDGE — scores output (optional; omit if scoring on asserts alone)
JUDGE_PROVIDER=claude_cli            # claude_cli | openai_compatible
JUDGE_MODEL=
JUDGE_TEMPERATURE=0
```

Key points:
- **Two independent models.** The runner is the model you're optimizing the prompt *for*; the judge is a (usually stronger) model that scores. They have separate provider/model/key settings — judge a weak runner with a strong judge.
- **Keys by env-var name only.** `config.env` stores `XAI_API_KEY` (the name), never `sk-...` (the value). Export the real key in your shell. This keeps `config.env` safe to commit.
- **`PROMPT_SMITH_CONFIG`** overrides the config path if you keep it somewhere other than `<workdir>/config.env`.
- **Temperature 0** for both, so scores are repeatable. Raise the runner's only to test production behavior, and then run the suite 2–3× (see `iteration-loop.md` on noise).

The implementations below are what those provider branches expand to — read them if you need to add a provider the scripts don't cover.

---

## Runner: Claude CLI
```bash
#!/usr/bin/env bash
# runner.sh — pipe the rendered prompt to the claude CLI, print the reply.
set -euo pipefail
payload=$(cat)
prompt=$(printf '%s' "$payload" | python3 -c 'import sys,json;print(json.load(sys.stdin)["prompt"])')
printf '%s' "$prompt" | claude -p --output-format text
```

## Runner: OpenAI-compatible (curl)
```bash
#!/usr/bin/env bash
# Works for OpenAI, xAI, llama.cpp server, Azure-style endpoints.
set -euo pipefail
: "${API_BASE:?set API_BASE}"; : "${API_KEY:?set API_KEY}"; : "${MODEL:?set MODEL}"
payload=$(cat)
body=$(printf '%s' "$payload" | python3 -c '
import sys, json
p = json.load(sys.stdin)["prompt"]
print(json.dumps({"model":"'"$MODEL"'","temperature":0,
  "messages":[{"role":"user","content":p}]}))')
curl -sS "$API_BASE/chat/completions" \
  -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" \
  -d "$body" \
| python3 -c 'import sys,json;print(json.load(sys.stdin)["choices"][0]["message"]["content"])'
```
Set `temperature:0` for repeatable scores. If you must test at production temperature, see `iteration-loop.md` on noise and run the suite 2–3×.

## Runner: wrap an existing harness or tool
If your project already has a tool that renders a prompt and calls a model (a replay
harness, an internal CLI, a batch evaluator), you usually don't need to talk to the API
directly — wrap it. The runner just has to turn the JSON on stdin into completion text on
stdout, however it gets there:
```bash
#!/usr/bin/env bash
set -euo pipefail
payload=$(cat)
prompt=$(printf '%s' "$payload" | python3 -c 'import sys,json;print(json.load(sys.stdin)["prompt"])')
# hand the prompt to whatever your project already uses to call the model:
printf '%s' "$prompt" | your-existing-tool run --stdin
```

**Two-tier validation.** prompt-smith is a *fast inner loop*: one prompt, a handful of
focused failure cases, seconds per iteration. If your project also has a heavier
acceptance gate (a full regression suite, a many-sample benchmark, an HTML report), use
that as the *outer gate*: optimize with prompt-smith until it converges, then run the
winning version through the full benchmark before shipping. Inner loop for speed, outer
gate for confidence — they answer different questions.

---

## Judge: Claude CLI
```bash
#!/usr/bin/env bash
# judge.sh — score one output against the rubric, return strict JSON.
set -euo pipefail
payload=$(cat)
read -r -d '' INSTR <<'EOF' || true
You are a strict prompt-output judge. You will receive JSON with keys
output and rubric. Score how well `output` satisfies `rubric` from 0.0 to 1.0.
Reply with ONLY compact JSON: {"score": <float>, "reasons": "<=30 words"}.
Be calibrated: 1.0 only for flawless; 0.5 for partial; 0.0 for total miss.
EOF
printf '%s\n\n%s' "$INSTR" "$payload" | claude -p --output-format text \
  | python3 -c '
import sys, json, re
raw = sys.stdin.read()
m = re.search(r"\{.*\}", raw, re.S)         # tolerate stray prose around the JSON
d = json.loads(m.group(0))
print(json.dumps({"score": float(d["score"]), "reasons": str(d.get("reasons",""))}))'
```
The regex salvage matters — judges sometimes wrap JSON in prose. The engine rejects unparseable judge output loudly, so normalize here.

## Judge design notes
- **One rubric = one quality.** A judge scoring "tone AND length AND persona" gives mush. Put length in a deterministic assert; let the judge own the one thing asserts can't measure. Use per-case `rubric` overrides for case-specific qualities.
- **Calibrate or it's noise.** Tell the judge what 0.0/0.5/1.0 mean. An uncalibrated judge clusters everything at 0.7–0.9 and can't distinguish your versions.
- **Judge with a strong model even when testing a weak one.** The judge's job is discrimination, not speed. A cheap judge that can't tell good from great makes your whole loop blind.
- **Determinism:** run the judge at temperature 0. A jittery judge manufactures fake score movement.

## Smoke test before trusting anything
```bash
echo '{"prompt":"Say exactly: hello world","case":"smoke","vars":{}}' | bash runner.sh
echo '{"output":"hello world","rubric":"says hello world","prompt":"","case":"smoke","vars":{}}' | bash judge.sh
```
First should print a completion; second valid `{"score":...}`. A broken runner reads as a terrible prompt and will send you chasing phantom failures.
