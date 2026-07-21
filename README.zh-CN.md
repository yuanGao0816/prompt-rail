# prompt-rail

[English](README.md) · [简体中文](README.zh-CN.md)

[![skills.sh](https://skills.sh/b/yuanGao0816/prompt-rail)](https://skills.sh/yuanGao0816/prompt-rail)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**别再凭感觉改 prompt。** prompt-rail 把优化变成可度量闭环：带 **train/test 双门槛** 和 **防背题护栏**，让系统提示词学规则，而不是背答案。

基于 [prompt-smith](https://github.com/Banner-Wang/prompt-smith) 二次改造。只要智能体支持 Agent Skills（`SKILL.md`）即可使用。

## 安装

直接让智能体帮你装（推荐）：

> 帮我安装这个技能：`npx skills add yuanGao0816/prompt-rail -g -y`

也可以自己执行：

```bash
npx skills add yuanGao0816/prompt-rail -g -y
```

## 用法

用自然语言交给智能体即可，不必自己敲 Python：

- 「用 prompt-rail 优化这个 prompt」
- 「用 prompt-rail 写一个 prompt，迭代到 train/test 都过线」
- 「这个 system prompt 在背题 / 过拟合，用 prompt-rail 修」

智能体按 `SKILL.md` 自动完成：建 train/test 评测集 → 基线 → 诊断 → 改一处 → 测量 → 门禁（`KEEP` / `REVERT` / `OVERFIT`）。

## 和 prompt-smith 的差异

| | prompt-smith | prompt-rail |
|--|--------------|-------------|
| 评测切片 | 单一 suite | `split: train \| test` |
| 保留条件 | 聚合分上升且无回归 | + test 不显著下降 |
| 过拟合 | 无硬门禁 | `gate.py` → `OVERFIT` |
| 改写纪律 | 每轮一假设 | + 四条防背题纪律 |

## 为什么需要防背题

评测、打分、改写若都钉在同一批用例上，prompt 会越来越像在背答案。prompt-rail 强制：

1. **train** 发现 badcase、驱动改写  
2. **test** 只做 holdout，不参与改写  
3. train 涨、test 跌 → `OVERFIT` → 回退  
4. 优先写规则边界，禁止堆用例原文刷分  

详见 `references/anti-overfit.md`。

## 分享

```text
prompt-rail：带 train/test 防背题的 prompt 迭代 Skill
安装：npx skills add yuanGao0816/prompt-rail -g -y
仓库：https://github.com/yuanGao0816/prompt-rail
```

## 可选：自己手动跑引擎

`scripts/` 是智能体底层调用的评测引擎，仅在你想复查某一步时使用：

```bash
SK=~/.agents/skills/prompt-rail
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split train --out runs/v0.train.json
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split test  --out runs/v0.test.json
python3 $SK/scripts/gate.py \
  --base-train runs/v0.train.json --base-test runs/v0.test.json \
  --cand-train runs/v1.train.json --cand-test runs/v1.test.json
```

## 依赖

- Python 3.10+（评测引擎）
- 可选：[PyYAML](https://pypi.org/project/PyYAML/)（`.yaml` suite；JSON 不需要）
- 可调用模型的方式（OpenAI 兼容 HTTP、Claude CLI 等，见 `references/runners.md`）

## License

MIT。衍生自 [Banner-Wang/prompt-smith](https://github.com/Banner-Wang/prompt-smith)（MIT）。
