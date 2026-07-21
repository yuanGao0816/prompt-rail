#!/usr/bin/env bash
# judge.sh — pluggable LLM-as-judge for prompt-rail.
#
# Contract: JSON on stdin {"prompt","output","rubric","case","vars"}
#           -> JSON on stdout {"score": 0.0..1.0, "reasons": "..."}
#
# Reads <workdir>/config.env and branches on JUDGE_PROVIDER — you don't edit
# this file to switch judge models. Keep the strict-JSON normalization at the
# end regardless of provider. See references/runners.md.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
cfg="${PROMPT_RAIL_CONFIG:-$here/config.env}"
if [[ -f "$cfg" ]]; then
  set -a; . "$cfg"; set +a
fi

provider="${JUDGE_PROVIDER:?set JUDGE_PROVIDER in config.env}"
temp="${JUDGE_TEMPERATURE:-0}"
payload=$(cat)

read -r -d '' INSTR <<'EOF' || true
You are a strict, calibrated judge of prompt outputs. You will receive JSON
with keys `output` and `rubric` (and context: prompt, case, vars).
Score how fully `output` satisfies `rubric`, from 0.0 to 1.0:
  1.0 = flawless;  0.7 = good with a minor miss;  0.5 = partial;
  0.2 = mostly fails;  0.0 = does not satisfy the rubric at all.
Judge ONLY what the rubric asks — ignore qualities it doesn't mention.
Reply with ONLY compact JSON: {"score": <float>, "reasons": "<=30 words"}.
EOF

# normalize whatever the model returns into strict {"score","reasons"} JSON.
normalize() {
  python3 -c '
import sys, json, re
raw = sys.stdin.read()
m = re.search(r"\{.*\}", raw, re.S)   # tolerate prose around the JSON
if not m:
    print(json.dumps({"score": 0.0, "reasons": "judge returned no JSON"})); sys.exit(0)
try:
    d = json.loads(m.group(0))
    s = max(0.0, min(1.0, float(d["score"])))
    print(json.dumps({"score": s, "reasons": str(d.get("reasons", ""))[:200]}))
except Exception as e:
    print(json.dumps({"score": 0.0, "reasons": f"unparseable judge output: {e}"}))'
}

case "$provider" in

  claude_cli)
    if [[ -n "${JUDGE_MODEL:-}" ]]; then
      printf '%s\n\n%s' "$INSTR" "$payload" \
        | claude -p --model "$JUDGE_MODEL" --output-format text | normalize
    else
      printf '%s\n\n%s' "$INSTR" "$payload" \
        | claude -p --output-format text | normalize
    fi
    ;;

  openai_compatible)
    : "${JUDGE_BASE:?set JUDGE_BASE}"; : "${JUDGE_MODEL:?set JUDGE_MODEL}"
    : "${JUDGE_API_KEY_ENV:?set JUDGE_API_KEY_ENV}"
    key="${!JUDGE_API_KEY_ENV:?$JUDGE_API_KEY_ENV is not exported}"
    body=$(MODEL="$JUDGE_MODEL" TEMP="$temp" INSTR="$INSTR" PAYLOAD="$payload" python3 -c '
import os, json
print(json.dumps({
    "model": os.environ["MODEL"],
    "temperature": float(os.environ["TEMP"]),
    "messages": [
        {"role": "system", "content": os.environ["INSTR"]},
        {"role": "user", "content": os.environ["PAYLOAD"]},
    ],
}))')
    curl -sS "$JUDGE_BASE/chat/completions" \
      -H "Authorization: Bearer $key" \
      -H "Content-Type: application/json" \
      -d "$body" \
    | python3 -c 'import sys,json;print(json.load(sys.stdin)["choices"][0]["message"]["content"])' \
    | normalize
    ;;

  *)
    echo "unknown JUDGE_PROVIDER: $provider" >&2
    exit 1
    ;;
esac
