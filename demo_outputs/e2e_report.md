# E2E Demo 报告：Baseline vs Full Harness

> 模型：`deepseek-v4-flash`
> 测试时间：2026-05-09 00:08:56
> 测试任务：分析 `main.py` 中的重复代码并给出重构建议

<p align="center"><font face="黑体" size=4>Baseline vs Full Harness 端到端对比</font></p>

| 维度 | Baseline | Full Harness (10 机制) | 差异 |
|---|---|---|---|
| 步骤数 | 1 | 6 | +5 |
| 耗时 (s) | 17.23 | 215.63 | +198.4 |
| 总 tokens | 1324 | 15169 | +13845 |
| 拦截次数 (Permission) | 0 | 0 | — |
| 错误数 | 0 | 0 | — |


## Budget 报告（Full Harness）

- 累计成本：$0.0811 USD
- 预算上限：$0.50 USD
- 是否超限：否
- 迭代数：6
- 输入 tokens：12204
- 输出 tokens：2965


## Baseline 输出（节选 800 字符）

```
以下是对代码中重复问题的分析及重构建议。

## 重复模式 1：客户类型与折扣率的映射重复

在 `calculate_discount` 和 `process_order` 两个函数中，都通过 `if-elif-else` 结构判断同一组客户类型（`"regular"`、`"vip"`、`"premium"`），并各自硬编码了相同的折扣率（0.05、0.15、0.25）。当需要新增、删除或修改客户类型及其折扣率时，必须同时修改两处，容易遗漏且违反 DRY 原则。

## 重复模式 2：折扣计算逻辑重复

每个函数内的每个分支都重复了相同的计算步骤：

```python
discount = price * rate
final_price = price - discount
```

尽管运算对象不同（`price` vs `total`），但模式完全相同。这种“先计算折扣额，再从原价中扣除”的逻辑也被重复编写了三次（每个客户类型分支各写一次），进一步增加了冗余。

## 重构建议

1. **提取折扣率映射**：使用字典定义客户类型与折扣率的对应关系，消除硬编码和重复的判断结构。
2. **提取通用折扣计算函数**：将“应用折扣”的通用逻辑抽离为一个单独函数，接受价格和折扣率，返回折后价格。
3. **简化两个业务函数**：让它们仅负责调用通用函数，并利用字典进行快速查找。

### 重构后的代码示例

```python
"""Refactored version with eliminated duplication."""

# 折扣率映射
DISCOUNT_RATES = {
    "regular": 0.05,
    "vip": 0.15,
    "premium": 0.25,
}

def apply_discount(price: floa
```

## Full Harness 输出（节选 800 字符）

```
---

## 🔍 完整重构方案

### (a) 至少 2 处重复模式的具体位置

---

**重复模式 1：同一函数内的 if-elif 分支重复计算逻辑（行级重复）**

位置：`calculate_discount` 函数（第 5–16 行）

```python
if customer_type == "regular":
    discount = price * 0.05
    final_price = price - discount
    return final_price
elif customer_type == "vip":
    discount = price * 0.15
    final_price = price - discount
    return final_price
elif customer_type == "premium":
    discount = price * 0.25
    final_price = price - discount
    return final_price
else:
    return price
```

三个分支除了折扣率（0.05 / 0.15 / 0.25）不同之外，`discount = price * X`、`final_price = price - discount`、`return final_price` 这三行完全一样。这是典型的 **"复制-粘贴-if"** 反模式，重复了 **3 × 3 = 9 行** 几乎相同的代码。

---

**重复模式 2：完全相同的折扣逻辑跨函数重复（函数间重复）**

位置：`calculate_discount`（第 5–16 行）与 `process_order`（第 24–34 行）

`proces
```

## 关键观察

1. Full Harness 通过 TODO 工具把任务拆成清单，每步单独推理。
2. Progress Tracker 实时把每步写到 `demo_outputs/progress.md`，跨 session 续传的基础设施。
3. Permission Gate 对 `run_bash` 的危险命令进行拦截，demo 中 `blocked_tools=0`。
4. Token Budget 实时累计成本并在超限时优雅终止（本次 $0.0811 < 上限 $0.50，未触发）。

## 文件清单

- `demo_outputs/progress.md` — Progress Tracker 真实落盘记录
- `demo_outputs/e2e_result.json` — 完整指标（JSON 可编程读）
- `demo_outputs/e2e_report.md` — 本报告（课件可直接引用）
