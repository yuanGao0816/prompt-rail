# prompt-rail

[English](README.md) · [简体中文](README.zh-CN.md)

[![skills.sh](https://skills.sh/b/yuanGao0816/prompt-rail)](https://skills.sh/yuanGao0816/prompt-rail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Stop rewriting prompts by vibes.** prompt-rail turns prompt work into a measured loop with **train/test dual-gate scoring** and **anti-overfit rails** — so your system prompt learns rules, not answers.

Forked from [prompt-smith](https://github.com/Banner-Wang/prompt-smith). Works with any agent that loads Agent Skills (`SKILL.md`).

## Install

Ask your agent (recommended):

> Help me install this skill: `npx skills add yuanGao0816/prompt-rail -g -y`

Or run it yourself:

```bash
npx skills add yuanGao0816/prompt-rail -g -y
```

## Usage

Talk to the agent — no need to run Python yourself:

- "use prompt-rail to optimize this prompt"
- "write a prompt with prompt-rail and iterate until train/test both pass"
- "this system prompt is overfitting / memorizing cases — fix it with prompt-rail"

The agent follows `SKILL.md`: build a train/test suite → baseline → diagnose → one edit → measure → gate (`KEEP` / `REVERT` / `OVERFIT`).

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

## Share

```text
prompt-rail — measured prompt iteration with train/test anti-overfit rails
Install: npx skills add yuanGao0816/prompt-rail -g -y
Repo: https://github.com/yuanGao0816/prompt-rail
```

## Optional: run the engine yourself

`scripts/` is what the agent calls under the hood. Use only if you want to re-run a step manually:

```bash
SK=~/.agents/skills/prompt-rail
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split train --out runs/v0.train.json
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split test  --out runs/v0.test.json
python3 $SK/scripts/gate.py \
  --base-train runs/v0.train.json --base-test runs/v0.test.json \
  --cand-train runs/v1.train.json --cand-test runs/v1.test.json
```

## Dependencies

- Python 3.10+ (eval engine)
- Optional: [PyYAML](https://pypi.org/project/PyYAML/) for `.yaml` suites (JSON needs none)
- A model runner (OpenAI-compatible HTTP, Claude CLI, … — see `references/runners.md`)

## License

MIT. Derived from [Banner-Wang/prompt-smith](https://github.com/Banner-Wang/prompt-smith) (MIT).
