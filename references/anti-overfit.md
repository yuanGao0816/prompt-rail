# 防背题纪律（Anti-overfit）

prompt-rail 相对 prompt-smith 的核心增量：把「评测 / 打分 / 改写」从同一批数据上拆开，避免系统提示词越写越像在背训练集用例。

灵感来源：支付宝 618 小模型意图识别迭代（train/test 切开 + 改写四纪律）。

---

## 1. 数据切开（硬规则）

| 切片 | 用途 | 禁止 |
|------|------|------|
| **train** | 发现 badcase、驱动诊断与改写 | — |
| **test** | 每轮结束后独立验收泛化 | 参与改写假设、被抄进 prompt、当 few-shot |

每轮流程固定为：

```
诊断(train badcase) → 假设 → 改一处 → 测 train → 测 test → gate(KEEP|REVERT|OVERFIT)
```

- 写假设时：**只打开 train 失分 case 的 output / failed_asserts**
- test 结果只用于 `gate.py` 与日志里的「泛化信号」，不用于「下一句该加哪条例」

建议比例：同类意图在 train/test 都有覆盖；危险误分（如误进 `code_fix`）优先放进 **test** 做验收闸门。

---

## 2. 双门槛收敛

`suite.yaml`：

```yaml
dual_gate: true
thresholds:
  train: 0.90
  test: 0.92
```

- **收敛**：train ≥ train 门槛 **且** test ≥ test 门槛
- **OVERFIT 信号**：train 上升且 test 下降超过 `gate.py --max-test-drop` → 必须回退，即使 train「好看」
- 改了 suite（增删用例、改断言）→ `suite_hash` 变了 → **整轮重新 baseline**，禁止拿旧分比新分

---

## 3. 改写四纪律（非协商）

存在多个 badcase 时，改写器必须先抽象**共同判定规则或边界**，写进 Rules。

1. **规则优先，禁止刷例**  
   严禁批量枚举案例、堆砌 few-shot、用大量「例如输入 X 应输出 Y」刷指标。  
   允许的例外：每轮最多 **1** 条对比示例，且示例必须改写为占位符（不可原样粘贴 train 用例原文）。

2. **每轮 ≤1 个结构性改动**  
   与 prompt-smith 的「一假设」一致。禁止一轮同时加规则 + 加示例 + 调格式。

3. **分信号读写**  
   - 仅 train 失分、test 正常 → 优先当噪声/长尾，**禁止为单条 train 噪声加专规**  
   - 仅 test 失分 → 往「判定原理 / 边界条件」改，不要抄 test 字样  
   - train+test 同向失分 → 真规则缺口，抽象后写入

4. **达标维不动**  
   某意图/维度已在 train 与 test 双过线，本轮禁止为「写得更漂亮」去改它相关段落。

### 背题嗅探（交付前自检）

打开候选 prompt，搜索是否出现：

- train 用例里的整句 `user_message` / 独特短语
- 「例如：……应输出……」超过 1 条
- 针对单条噪声的特判规则

命中任一项 → 视为 OVERFIT 风险，回退或重写为抽象规则后再测。

---

## 4. 与意图分类任务的贴合

分类 / 路由 prompt 优先用确定性断言（`json_valid` + `json_field_eq`），少用 LLM-as-judge 刷软分——软分更容易被「更长更像标准答案」的背题文风骗过。

危险误分（例如不该进 `code_fix`）应：

- 在 **test** 里有明确用例
- 在评分上可加高权重 case，或失败时直接让该 case 分掉到门槛以下

---

## 5. Agent 执行检查清单

每轮结束前确认：

- [ ] 本轮诊断只引用了 train badcase
- [ ] prompt diff 未粘贴任何 test 用例原文
- [ ] 未新增超过 1 条 few-shot
- [ ] 已分别写出 `runs/vN.train.json` 与 `runs/vN.test.json`
- [ ] 已跑 `gate.py`，决策为 KEEP / REVERT / OVERFIT 之一并写入 ledger
