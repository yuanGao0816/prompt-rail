# prompt-rail

A measured prompt iteration skill with **train/test dual-gate scoring** and **anti-overfit rewrite rails**.

Forked from [prompt-smith](https://github.com/Banner-Wang/prompt-smith). Works with any agent that loads Agent Skills (`SKILL.md`).

## Install

```bash
# global (recommended)
npx skills add yuanGao0816/prompt-rail -g -y

# or clone into your agent's skills directory
git clone https://github.com/yuanGao0816/prompt-rail.git ~/.agents/skills/prompt-rail
```

Ask the agent: "use prompt-rail to optimize this prompt".

## vs prompt-smith

| | prompt-smith | prompt-rail |
|--|--------------|-------------|
| Eval slice | single suite | `split: train \| test` |
| Keep rule | aggregate up, no regression | + test must not drop |
| Overfit | no hard gate | `gate.py` → `OVERFIT` |
| Rewrite discipline | one hypothesis / round | + four anti-memorization rules |

## Quick commands

```bash
# SK = wherever this skill is installed
SK=~/.agents/skills/prompt-rail
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split train --out runs/v0.train.json
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split test  --out runs/v0.test.json
python3 $SK/scripts/gate.py \
  --base-train runs/v0.train.json --base-test runs/v0.test.json \
  --cand-train runs/v1.train.json --cand-test runs/v1.test.json
```

See `SKILL.md` and `references/anti-overfit.md` for the full loop.

## License

MIT. Derived from [Banner-Wang/prompt-smith](https://github.com/Banner-Wang/prompt-smith) (MIT).
