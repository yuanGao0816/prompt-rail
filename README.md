# prompt-rail

[English](README.md) · [简体中文](README.zh-CN.md)

A measured prompt iteration skill with **train/test dual-gate scoring** and **anti-overfit rewrite rails**.

Forked from [prompt-smith](https://github.com/Banner-Wang/prompt-smith). Works with any agent that loads Agent Skills (`SKILL.md`).

## Install

```bash
# global (recommended)
npx skills add yuanGao0816/prompt-rail -g -y

# or clone into your agent's skills directory
git clone https://github.com/yuanGao0816/prompt-rail.git ~/.agents/skills/prompt-rail
```

## Usage

Just ask the agent in natural language — you do **not** need to run the Python scripts yourself:

- "use prompt-rail to optimize this prompt"
- "write a prompt with prompt-rail and iterate until it passes train/test"
- "reduce overfitting / memorization in this system prompt"

The agent follows `SKILL.md`: build a train/test suite, baseline, then loop diagnose → edit → measure → gate (`KEEP` / `REVERT` / `OVERFIT`).

## vs prompt-smith

| | prompt-smith | prompt-rail |
|--|--------------|-------------|
| Eval slice | single suite | `split: train \| test` |
| Keep rule | aggregate up, no regression | + test must not drop |
| Overfit | no hard gate | `gate.py` → `OVERFIT` |
| Rewrite discipline | one hypothesis / round | + four anti-memorization rules |

## Why anti-overfit

If eval, scoring, and rewrite all run on the same cases, the prompt starts memorizing the suite. prompt-rail enforces:

1. **train** drives diagnosis and rewrite  
2. **test** is holdout-only — never used to invent rules  
3. train↑ + test↓ → `OVERFIT` → revert  
4. Prefer abstract rules; do not paste case surface forms to chase score  

See `references/anti-overfit.md`.

## Optional: run the engine yourself

The `scripts/` helpers are what the agent calls under the hood. Only use them if you want to inspect or re-run a step manually:

```bash
SK=~/.agents/skills/prompt-rail   # or this skill's install path
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split train --out runs/v0.train.json
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split test  --out runs/v0.test.json
python3 $SK/scripts/gate.py \
  --base-train runs/v0.train.json --base-test runs/v0.test.json \
  --cand-train runs/v1.train.json --cand-test runs/v1.test.json
```

## Dependencies

- Python 3.10+ (for the eval engine the agent invokes)
- Optional: [PyYAML](https://pypi.org/project/PyYAML/) (only if the suite is `.yaml`; JSON suites need no extra deps)
- A way to call a model (bundled runners support OpenAI-compatible HTTP, Claude CLI, etc. — see `references/runners.md`)

## License

MIT. Derived from [Banner-Wang/prompt-smith](https://github.com/Banner-Wang/prompt-smith) (MIT).
