# prompt-rail

[English](README.md) · [简体中文](README.zh-CN.md)

一个用于**编写、优化、测试 prompt** 的 Agent Skill，核心是可度量的迭代，并加上 **train/test 双门槛** 与 **防背题改写纪律**。

基于 [prompt-smith](https://github.com/Banner-Wang/prompt-smith) 二次改造。只要智能体支持 Agent Skills（`SKILL.md`）即可使用，不绑定某一家产品。

## 安装

直接让智能体帮你装（推荐）：

> 帮我安装这个技能：`npx skills add yuanGao0816/prompt-rail -g -y`

也可以自己执行：

```bash
# 全局安装（推荐）
npx skills add yuanGao0816/prompt-rail -g -y

# 或克隆到你的智能体 skills 目录
git clone https://github.com/yuanGao0816/prompt-rail.git ~/.agents/skills/prompt-rail
```

## 用法

直接用自然语言让智能体执行即可，**不必自己敲 Python 命令**：

- 「用 prompt-rail 优化这个 prompt」
- 「用 prompt-rail 写一个 prompt，并迭代到 train/test 都过线」
- 「减少这个 system prompt 的背题 / 过拟合」

智能体会按 `SKILL.md` 自动完成：建 train/test 评测集 → 基线 → 诊断 → 改一处 → 测量 → 门禁（`KEEP` / `REVERT` / `OVERFIT`）。

## 和 prompt-smith 的差异

| | prompt-smith | prompt-rail |
|--|--------------|-------------|
| 评测切片 | 单一 suite | `split: train \| test` |
| 保留条件 | 聚合分上升且无回归 | + test 不显著下降 |
| 过拟合 | 无硬门禁 | `gate.py` → `OVERFIT` |
| 改写纪律 | 每轮一假设 | + 四条防背题纪律 |

## 为什么需要防背题

如果评测、打分、改写都钉在同一批用例上，prompt 会越来越像在「背答案」。prompt-rail 强制：

1. **train** 只负责发现 badcase、驱动改写  
2. **test** 只做 holdout 验收，不参与改写  
3. train 涨、test 跌 → 判 `OVERFIT` 并回退  
4. 改写优先写规则边界，禁止堆砌用例原文刷分  

详见 `references/anti-overfit.md`。

## 可选：自己手动跑引擎

`scripts/` 里的脚本是智能体底层会调用的评测引擎。只有你想自己复查某一步时，才需要手动执行：

```bash
SK=~/.agents/skills/prompt-rail   # 或本 skill 的实际安装路径
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split train --out runs/v0.train.json
python3 $SK/scripts/run_eval.py suite.yaml --prompt prompts/v0.md --split test  --out runs/v0.test.json
python3 $SK/scripts/gate.py \
  --base-train runs/v0.train.json --base-test runs/v0.test.json \
  --cand-train runs/v1.train.json --cand-test runs/v1.test.json
```

## 依赖

- Python 3.10+（供智能体调用评测引擎）
- 可选：[PyYAML](https://pypi.org/project/PyYAML/)（suite 用 `.yaml` 时需要；用 JSON 则不需要）
- 一种可调用模型的方式（内置 runner 支持 OpenAI 兼容 HTTP 与 Claude CLI 等，见 `references/runners.md`）

## License

MIT。衍生自 [Banner-Wang/prompt-smith](https://github.com/Banner-Wang/prompt-smith)（MIT）。
