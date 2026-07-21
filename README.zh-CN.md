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

## 评测用例（train / test）——金标由人把关

**用例不是自动生成就等于正确。** 分数只对「可信的评测集」有意义；请优先使用**人工核对过**的输入与期望输出。

| 来源 | 什么时候用 |
|------|------------|
| **你上传 / 提供（推荐）** | 真实日志、已知误分、你已标好并核对过的例子 |
| **智能体起草，你审批** | 你说清任务后它可拟一批 case —— **跑基线前必须给你看 train/test 列表，确认后再冻** |
| **无人复核的自动生成** | 只能当草稿，不要当成冻结的权威 suite |

### 如何自己提供用例

1. 写入工作目录的 `suite.yaml`（可从 `assets/suite.template.yaml` 复制改）。
2. 每条必须有 `split: train` 或 `split: test`，以及 `vars` 和断言 / 期望标签。
3. 也可以先整理成表格 / CSV / JSON（`输入 → 期望标签 → train|test`），让智能体**只做格式转换进 suite，不要改你的金标**。

用例结构示例：

```yaml
cases:
  - name: train-example
    split: train          # 只有 train 失分才驱动改写
    vars:
      user_message: "粘贴你已核对过的真实用户原话"
    asserts:
      - {type: json_valid}
      - {type: json_field_eq, field: intent, equals: troubleshooting}

  - name: test-example
    split: test           # holdout：禁止把这些原文写进 prompt
    vars:
      user_message: "另一条已核对、表述不同的真实原话"
    asserts:
      - {type: json_valid}
      - {type: json_field_eq, field: intent, equals: troubleshooting}
```

**使用建议**

- 标签先人工（或交叉）核对，再冻结 suite。
- 各类标签尽量在 train / test 都有覆盖；高代价误分优先放进 **test**。
- 基线之后：不要同一轮既改 prompt 又改评测集。
- 已有金标时，对智能体说：「用我这些金标做 suite，不要自己编标签。」

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
