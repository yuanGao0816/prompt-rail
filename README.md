# prompt-rail

基于 [prompt-smith](https://github.com/Banner-Wang/prompt-smith) 二次改造的 Agent Skill：保留可度量迭代引擎，并加上 **train/test 双门槛** 与 **防背题改写纪律**。

Compatible with Cursor / Claude Code / Codex style skill directories (`SKILL.md`).

## Install

```bash
# global (recommended)
npx skills add yuanGao0816/prompt-rail -g -y

# or clone manually
git clone https://github.com/yuanGao0816/prompt-rail.git ~/.cursor/skills/prompt-rail
```

In Cursor, say:「用 prompt-rail 优化这个 prompt」.

## vs prompt-smith

| | prompt-smith | prompt-rail |
|--|--------------|-------------|
| Eval slice | single suite | `split: train \| test` |
| Keep rule | aggregate up, no regression | + test must not drop |
| Overfit | no hard gate | `gate.py` → `OVERFIT` |
| Rewrite discipline | one hypothesis / round | + four anti-memorization rules |

## Quick commands

```bash
SK=~/.cursor/skills/prompt-rail   # or your clone path
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split train --out runs/v0.train.json
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split test  --out runs/v0.test.json
python3 $SK/scripts/gate.py \
  --base-train runs/v0.train.json --base-test runs/v0.test.json \
  --cand-train runs/v1.train.json --cand-test runs/v1.test.json
```

See `SKILL.md` and `references/anti-overfit.md` for the full loop.

## License

MIT. Derived from [Banner-Wang/prompt-smith](https://github.com/Banner-Wang/prompt-smith) (MIT).
