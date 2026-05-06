# 成本追踪与预算

> 归档参考: archive/initial-specs/20260416-12-cost-budget-spec.md
> 最后更新: 2026-05-01
> Scope: Core（CLI 命令与 Desktop 展示为 adapter）

## 概述

追踪 LLM 调用的 Token 消耗和费用，支持预算上限和告警。

## 已实现

### 成本追踪 (`src/sloth_agent/cost/`)

- `tracker.py` — Token 计数与费用计算
- `budget_router.py` — 预算检查与路由
- `pricing.py` — 各 Provider 价格表
- `models.py` — 成本数据模型

### CLI 命令 (`src/sloth_agent/cli/cost_cmd.py`)

- 成本查询
- 预算设置

### 配置 (`configs/cost.yaml`)

- 各模型价格
- 预算上限

### Hook 集成

HookManager 暴露 `budget.warn` 和 `budget.over` 事件点。

## 待实现

- 熔断降级（费用超限自动切换低价模型）
- 费用预测
- 多 Provider 自动切换

## 关键接口

- `CostTracker.track(model, tokens_in, tokens_out)`
- `BudgetRouter.check() → BudgetStatus`
