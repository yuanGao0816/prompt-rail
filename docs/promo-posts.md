# Promo copy (for sharing outside the repo)

Copy-paste ready. Not required for using the skill.

---

## 中文 · 短帖（即刻 / 朋友圈 / 技术群）

凭感觉改 prompt，最后容易「背评测集答案」。

开源了 prompt-rail：在可度量迭代之上，强制 train/test 切开。
train 涨、test 跌 → 直接判 OVERFIT 回退。

安装（或让 Agent 帮你装）：
npx skills add yuanGao0816/prompt-rail -g -y

仓库：https://github.com/yuanGao0816/prompt-rail

---

## 中文 · 稍长（掘金 / 博客开头）

标题建议：别再让 System Prompt 背答案了：用 train/test 双门槛迭代 Prompt

正文要点：
1. 痛点：同一批用例又评又改 → prompt 堆满「例如输入 X 应输出 Y」
2. 做法：冻结评测集；改写只看 train；每轮用 test 验收；双门槛 + OVERFIT 门禁
3. 使用：对 Agent 说「用 prompt-rail 优化这个 prompt」
4. 安装：`npx skills add yuanGao0816/prompt-rail -g -y`
5. 致谢：基于 prompt-smith 二次改造

---

## English · short (X / Reddit)

Stop rewriting prompts by vibes — they start memorizing your eval set.

prompt-rail: measured prompt iteration with train/test dual-gate + OVERFIT revert.

Install:
npx skills add yuanGao0816/prompt-rail -g -y

Or ask your agent:
"Help me install this skill: npx skills add yuanGao0816/prompt-rail -g -y"

Repo: https://github.com/yuanGao0816/prompt-rail
(Forked from prompt-smith; adds anti-overfit rails.)

---

## GitHub Discussion / Issue note to prompt-smith (polite)

Hi! Thanks for prompt-smith — the measured loop (frozen suite, one hypothesis, keep/revert) is excellent.

I published a small derivative, **prompt-rail**, that adds train/test holdout + an OVERFIT gate so rewrite signals don't come from the same cases used for final scoring (a common "memorize the suite" failure mode).

- Repo: https://github.com/yuanGao0816/prompt-rail
- Install: `npx skills add yuanGao0816/prompt-rail -g -y`

Happy to take feedback or link back more prominently if useful. MIT, attributed.
