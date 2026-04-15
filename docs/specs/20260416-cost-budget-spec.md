# 费用与预算追踪规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

现有 Metrics spec 只有 `total_tokens_used`（原始 token 计数），没有：
1. 各模型的价格和费用换算
2. 预算限制和软硬停机机制
3. 按场景/Phase 的费用细分
4. 费用预测

Sloth Agent 使用 6 个 LLM Provider（含 Xiaomi mimo），自主模式下无人值守，费用可能失控。

---

## 2. 模型定价表

### 2.1 支持的模型清单

| Provider | 模型 | Input (¥/1K tokens) | Output (¥/1K tokens) | 备注 |
|----------|------|---------------------|----------------------|------|
| **DeepSeek** | deepseek-v3.2 | 0.001 | 0.002 | 最新基础模型（2025-12） |
| **DeepSeek** | deepseek-r1-0528 | 0.002 | 0.004 | 最新推理模型（2026-01） |
| **DeepSeek** | deepseek-v4 | 0.002 | 0.004 | 编码旗舰（2026-02） |
| **Qwen** | qwen3.6-plus | 0.001 | 0.002 | 最新旗舰，代码增强 |
| **Qwen** | qwen3.5-plus | 0.0005 | 0.001 | 多模态，速度快 |
| **Qwen** | qwen3-max | 0.002 | 0.004 | 最大规模文本旗舰 |
| **Kimi** | kimi-k2.5 | 0.002 | 0.004 | 最新旗舰（2026-01） |
| **Kimi** | kimi-k2 | 0.001 | 0.002 | 上一代（2025-07） |
| **GLM** | glm-4.5 | 0.001 | 0.002 | 最新旗舰（2025-07） |
| **GLM** | glm-4.5-air | 0.0005 | 0.001 | 轻量版 |
| **GLM** | glm-4.5-flash | 0 | 0 | 免费版 |
| **MiniMax** | minimax-m2.5 | 0.001 | 0.002 | 最新全栈交付 |
| **MiniMax** | minimax-m1 | 0.001 | 0.002 | MoE 推理模型 |
| **Xiaomi** | mimo-v2-pro | 0.001 | 0.002 | 最新旗舰（2026-03） |
| **Xiaomi** | mimo-v2-omni | 0.002 | 0.004 | 全模态 Agent |
| **Xiaomi** | mimo-v2-flash | 0.0005 | 0.001 | 轻量版 |

> 价格为参考值，实际以 Provider 官方定价为准。
> 配置中应支持通过 YAML 覆盖价格。

### 2.2 定价配置

```yaml
# configs/cost.yaml
cost:
  pricing:
    deepseek:
      deepseek-v3.2:
        input_per_1k: 0.001
        output_per_1k: 0.002
      deepseek-r1-0528:
        input_per_1k: 0.002
        output_per_1k: 0.004
      deepseek-v4:
        input_per_1k: 0.002
        output_per_1k: 0.004
    qwen:
      qwen3.6-plus:
        input_per_1k: 0.001
        output_per_1k: 0.002
      qwen3.5-plus:
        input_per_1k: 0.0005
        output_per_1k: 0.001
      qwen3-max:
        input_per_1k: 0.002
        output_per_1k: 0.004
    kimi:
      kimi-k2.5:
        input_per_1k: 0.002
        output_per_1k: 0.004
      kimi-k2:
        input_per_1k: 0.001
        output_per_1k: 0.002
    glm:
      glm-4.5:
        input_per_1k: 0.001
        output_per_1k: 0.002
      glm-4.5-air:
        input_per_1k: 0.0005
        output_per_1k: 0.001
      glm-4.5-flash:
        input_per_1k: 0
        output_per_1k: 0
    minimax:
      minimax-m2.5:
        input_per_1k: 0.001
        output_per_1k: 0.002
      minimax-m1:
        input_per_1k: 0.001
        output_per_1k: 0.002
    xiaomi:
      mimo-v2-pro:
        input_per_1k: 0.001
        output_per_1k: 0.002
      mimo-v2-omni:
        input_per_1k: 0.002
        output_per_1k: 0.004
      mimo-v2-flash:
        input_per_1k: 0.0005
        output_per_1k: 0.001

  budget:
    daily_limit: 10.0           # 每日预算上限（¥）
    scenario_limit: 3.0         # 单场景预算上限（¥）
    soft_limit_percent: 0.8     # 软停机阈值（80%）
    hard_limit_percent: 1.0     # 硬停机阈值（100%）
```

---

## 3. 费用追踪器

```python
class CostTracker:
    """费用追踪器。

    追踪每次 LLM 调用的 token 消耗和费用，
    提供预算检查和费用预测。
    """

    def __init__(self, config: Config,
                 pricing: dict | None = None):
        self.config = config
        self.pricing = pricing or self._load_pricing(config)
        self.records: list[CostRecord] = []

        # 当前周期累计
        self.daily_total: float = 0.0
        self.scenario_totals: dict[str, float] = {}

    def record_llm_call(self, provider: str, model: str,
                         input_tokens: int, output_tokens: int,
                         scenario_id: str | None = None,
                         phase_id: str | None = None) -> CostRecord:
        """记录一次 LLM 调用的费用。"""
        input_cost = (
            input_tokens / 1000
            * self.pricing.get(provider, {}).get(model, {}).get("input_per_1k", 0)
        )
        output_cost = (
            output_tokens / 1000
            * self.pricing.get(provider, {}).get(model, {}).get("output_per_1k", 0)
        )
        total_cost = input_cost + output_cost

        record = CostRecord(
            timestamp=time.time(),
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=total_cost,
            scenario_id=scenario_id,
            phase_id=phase_id,
        )

        self.records.append(record)
        self.daily_total += total_cost

        if scenario_id:
            self.scenario_totals[scenario_id] = (
                self.scenario_totals.get(scenario_id, 0) + total_cost
            )

        return record

    def check_budget(self, scope: str = "daily") -> BudgetStatus:
        """检查预算使用情况。"""
        if scope == "daily":
            limit = self.config.cost.budget.daily_limit
            used = self.daily_total
        elif scope == "scenario":
            # 返回所有场景的预算状态
            return self._check_all_scenarios()
        else:
            raise ValueError(f"Unknown budget scope: {scope}")

        used_percent = used / limit if limit > 0 else 0
        soft_limit = limit * self.config.cost.budget.soft_limit_percent
        hard_limit = limit * self.config.cost.budget.hard_limit_percent

        if used >= hard_limit:
            return BudgetStatus(
                scope=scope,
                limit=limit,
                used=used,
                remaining=max(0, limit - used),
                used_percent=used_percent,
                status="hard_exceeded",
                action="stop_all",
            )
        elif used >= soft_limit:
            return BudgetStatus(
                scope=scope,
                limit=limit,
                used=used,
                remaining=max(0, limit - used),
                used_percent=used_percent,
                status="soft_limit_reached",
                action="degrade",
            )
        else:
            return BudgetStatus(
                scope=scope,
                limit=limit,
                used=used,
                remaining=limit - used,
                used_percent=used_percent,
                status="ok",
            )

    def get_daily_tokens(self, date: str) -> int:
        """获取指定日期的总 token 数。"""
        return sum(
            r.input_tokens + r.output_tokens
            for r in self.records
            if datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d") == date
        )

    def get_daily_cost(self, date: str) -> float:
        """获取指定日期的总费用。"""
        return sum(
            r.total_cost
            for r in self.records
            if datetime.fromtimestamp(r.timestamp).strftime("%Y-%m-%d") == date
        )

    def forecast_daily_cost(self, current_hour: int | None = None) -> float:
        """预测今日总费用。"""
        if current_hour is None:
            current_hour = datetime.now().hour
        if current_hour == 0:
            return self.daily_total

        # 线性外推
        hourly_rate = self.daily_total / current_hour
        return hourly_rate * 24

    def get_cost_breakdown(self, scope: str = "daily") -> CostBreakdown:
        """获取费用细分。"""
        records = self.records

        # 按 Provider 分组
        by_provider: dict[str, float] = {}
        for r in records:
            by_provider[r.provider] = by_provider.get(r.provider, 0) + r.total_cost

        # 按场景分组
        by_scenario: dict[str, float] = {}
        for r in records:
            sid = r.scenario_id or "unknown"
            by_scenario[sid] = by_scenario.get(sid, 0) + r.total_cost

        return CostBreakdown(
            total=sum(by_provider.values()),
            by_provider=by_provider,
            by_scenario=by_scenario,
            total_tokens=sum(r.input_tokens + r.output_tokens for r in records),
        )
```

---

## 4. 费用与 LLM 调用联动

```python
class BudgetAwareLLMRouter:
    """预算感知的 LLM 路由。

    当预算接近上限时，自动切换到更便宜的模型。
    """

    def __init__(self, config: Config, cost_tracker: CostTracker,
                 circuit_manager: ProviderCircuitManager):
        self.config = config
        self.costs = cost_tracker
        self.circuits = circuit_manager

        # 模型按费用从低到高排序
        self.cheap_models = ["glm-4.5-flash", "qwen3.5-plus", "deepseek-v3.2"]
        self.mid_models = ["qwen3.6-plus", "kimi-k2", "minimax-m1"]
        self.expensive_models = ["qwen3-max", "kimi-k2.5", "mimo-v2-pro", "claude-sonnet"]
        self.expensive_models = ["qwen-max", "moonshot-v1-128k", "claude-sonnet"]

    def select_model(self, preferred: str, task_complexity: str = "medium") -> str:
        """根据预算状态选择模型。"""
        budget = self.costs.check_budget("daily")

        if budget.status == "hard_exceeded":
            # 预算已超，使用最便宜的可用模型
            for model in self.cheap_models:
                if self.circuits.get_available_provider(model):
                    return model
            return preferred  # 全部不可用则回退

        elif budget.status == "soft_limit_reached":
            # 接近预算，降级到便宜模型
            if task_complexity == "low":
                for model in self.cheap_models:
                    if self.circuits.get_available_provider(model):
                        return model
            elif task_complexity == "medium":
                for model in self.mid_models:
                    if self.circuits.get_available_provider(model):
                        return model

        # 预算充足，使用首选模型
        return preferred
```

---

## 5. 数据模型

```python
@dataclass
class CostRecord:
    timestamp: float
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    scenario_id: str | None = None
    phase_id: str | None = None


@dataclass
class BudgetStatus:
    scope: str           # "daily" | "scenario"
    limit: float         # 预算上限（¥）
    used: float          # 已用（¥）
    remaining: float     # 剩余（¥）
    used_percent: float  # 使用率
    status: str          # "ok" | "soft_limit_reached" | "hard_exceeded"
    action: str          # "continue" | "degrade" | "stop_all"


@dataclass
class CostBreakdown:
    total: float
    by_provider: dict[str, float]
    by_scenario: dict[str, float]
    total_tokens: int
```

---

## 6. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/cost/__init__.py` | 费用模块入口 |
| `src/sloth_agent/cost/tracker.py` | CostTracker 费用追踪器 |
| `src/sloth_agent/cost/budget_router.py` | BudgetAwareLLMRouter 预算感知路由 |
| `src/sloth_agent/cost/pricing.py` | 定价表加载器 |
| `src/sloth_agent/cost/models.py` | 费用数据模型 |
| `configs/cost.yaml` | 费用和预算配置 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
