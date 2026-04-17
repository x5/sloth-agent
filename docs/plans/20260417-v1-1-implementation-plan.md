# v0.2 Implementation Plan

> Date: 2026-04-17
> Goal: v0.2 最小可用扩展 — 成本管控、Provider 容错、Chat Mode 增强
> 依赖链: `Cost → Fallback → Chat → Context → Adaptive`
> 版本映射: 此计划原编号 v1.1，现重命名为 v0.2
> 状态: 全部完成 (360 tests pass)

---

## Task V1-1: Cost Tracking 基础

> Arch: `00000000-00-architecture-overview.md` §7.3
> Spec: `20260416-12-cost-budget-spec.md`
> Depends: v1.0 Task 8 (LLMRouter)

### 实现内容
1. **CostTracker 数据模型** (`src/sloth_agent/cost/models.py`)
   - `CallRecord` dataclass: `call_id, model, provider, input_tokens, output_tokens, cost_usd, timestamp, agent_id, run_id`
   - `CostTracker` class: `record_call()`, `get_total_cost()`, `get_usage_by_model()`, `check_budget()`
   - 基于文件系统存储: `cost/calls.jsonl`, `cost/budget.json`

2. **定价表** (`src/sloth_agent/cost/pricing.py`)
   - 内置定价表覆盖 spec 中 16 个模型（per-input/output-token 价格）
   - `calculate_cost(model, input_tokens, output_tokens) -> float`
   - 支持从 `configs/pricing.yaml` 覆盖

3. **BudgetAwareLLMRouter** (`src/sloth_agent/cost/budget_router.py`)
   - 继承/包装现有 LLMRouter
   - 每次 LLM 调用前 `check_budget()`，超过阈值返回降级建议
   - 支持软限额（80% 警告）和硬限额（100% 阻断）

4. **集成点**
   - 在 `ToolRuntime` 的 LLM 调用路径中接入 `record_call()`
   - 在 `Runner` 的 turn 循环中接入 budget 检查

5. **测试**
   - `tests/cost/test_models.py`: CallRecord / CostTracker 基本操作
   - `tests/cost/test_pricing.py`: 定价计算准确性
   - `tests/cost/test_budget_router.py`: 预算检查 / 降级触发

### 文件清单
| 文件 | 操作 |
|------|------|
| `src/sloth_agent/cost/__init__.py` | 新建 |
| `src/sloth_agent/cost/models.py` | 新建 |
| `src/sloth_agent/cost/pricing.py` | 新建 |
| `src/sloth_agent/cost/budget_router.py` | 新建 |
| `configs/pricing.yaml` | 新建 |
| `tests/cost/__init__.py` | 新建 |
| `tests/cost/test_models.py` | 新建 |
| `tests/cost/test_pricing.py` | 新建 |
| `tests/cost/test_budget_router.py` | 新建 |

---

## Task V1-2: Provider Fallback / 熔断降级

> Arch: `00000000-00-architecture-overview.md` §7.3
> Spec: `20260416-07-chat-mode-spec.md` §Provider 部分 + `20260416-09-error-handling-recovery-spec.md` §4
> Depends: Task V1-1

### 实现内容
1. **CircuitBreaker** (`src/sloth_agent/errors/circuit_breaker.py`)
   - closed → open → half_open 三态机
   - `can_execute()`, `record_success()`, `record_failure()`
   - `failure_threshold` (默认5) 和 `recovery_timeout` (默认300s)

2. **ProviderCircuitManager** (`src/sloth_agent/errors/circuit_manager.py`)
   - 为每个 registered provider 维护独立 CircuitBreaker
   - `get_available_provider(preferred)` — fallback 到下一个可用 provider
   - `record(provider, success)` — 记录执行结果

3. **LLMRouter 集成熔断**
   - 修改 `LLMRouter.get_model()` 支持 fallback 链
   - 当首选 provider 熔断时，自动切换到备选
   - 全部 provider 不可用时返回 MockProvider 或抛出明确错误

4. **测试**
   - `tests/errors/test_circuit_breaker.py`: 三态转换逻辑
   - `tests/errors/test_circuit_manager.py`: 多 provider 熔断管理
   - `tests/providers/test_llm_router_fallback.py`: fallback 链路

### 文件清单
| 文件 | 操作 |
|------|------|
| `src/sloth_agent/errors/__init__.py` | 新建 |
| `src/sloth_agent/errors/circuit_breaker.py` | 新建 |
| `src/sloth_agent/errors/circuit_manager.py` | 新建 |
| `src/sloth_agent/providers/llm_router.py` | 修改 (集成 fallback) |
| `tests/errors/__init__.py` | 新建 |
| `tests/errors/test_circuit_breaker.py` | 新建 |
| `tests/errors/test_circuit_manager.py` | 新建 |
| `tests/providers/test_llm_router_fallback.py` | 新建 |

---

## Task V1-3: Chat Mode 增强（REPL + streaming）

> Arch: `00000000-00-architecture-overview.md` §5 设计原则
> Spec: `20260416-07-chat-mode-spec.md`
> Depends: v1.0 基础工具 + Task V1-2

### 实现内容
1. **SessionManager** (`src/sloth_agent/chat/session.py`)
   - 创建/加载/保存 chat session
   - 对话历史持久化到 `sessions/chat/<id>.jsonl`
   - 上下文截断策略: 保留 system + 最后 N 轮

2. **工具执行集成** (`src/sloth_agent/chat/repl.py`)
   - 在 ChatSession 中支持 tool call 解析和执行
   - 用户确认机制: 高风险工具需 `/confirm`
   - streaming 输出显示

3. **v1.1 新增 slash commands**
   - `/skill <name>`: 触发 skill 执行
   - `/start autonomous`: 进入自主模式
   - `/stop`: 停止当前自主任务
   - `/status`: 显示当前任务状态

4. **自主模式控制器** (`src/sloth_agent/chat/autonomous.py`)
   - `AutonomousController`: 接收 plan → 交给 Runner 执行
   - 支持用户 `/stop` 中断
   - 任务完成后返回结果到 REPL

5. **测试**
   - `tests/chat/test_session.py`: session CRUD + 持久化
   - `tests/chat/test_context_truncation.py`: 上下文截断逻辑
   - `tests/chat/test_autonomous.py`: 自主模式 start/stop

### 文件清单
| 文件 | 操作 |
|------|------|
| `src/sloth_agent/chat/__init__.py` | 新建 |
| `src/sloth_agent/chat/session.py` | 新建 |
| `src/sloth_agent/chat/repl.py` | 新建 (增强版 REPL) |
| `src/sloth_agent/chat/autonomous.py` | 新建 |
| `src/sloth_agent/cli/chat.py` | 修改 (集成新组件) |
| `src/sloth_agent/cli/app.py` | 修改 (version + chat command) |
| `tests/chat/__init__.py` | 新建 |
| `tests/chat/test_session.py` | 新建 |
| `tests/chat/test_context_truncation.py` | 新建 |
| `tests/chat/test_autonomous.py` | 新建 |
| `tests/chat/test_repl.py` | 新建 |

---

## Task V1-4: Builder 上下文窗口管理优化

> Arch: `00000000-00-architecture-overview.md` §5.1.2
> Spec: `20260416-01-phase-role-architecture-spec.md`
> Depends: v1.0 Task 3 (Builder)

### 实现内容
1. **ContextWindowManager 优化** (`src/sloth_agent/core/context_window.py`)
   - 改进上下文截断算法: token-based 而非 turn-based
   - 增加 summary 压缩: 对早期对话生成摘要替代原文
   - 关键信息保护: plan, gate rules, tool definitions 始终保留

2. **Token 计数器** (`src/sloth_agent/core/token_counter.py`)
   - 估算文本 token 数 (支持 tiktoken 或简化估算)
   - 用于 context window 预算计算

3. **测试**
   - `tests/core/test_token_counter.py`: token 估算准确性
   - `tests/core/test_context_truncation.py`: 截断逻辑覆盖各种场景

### 文件清单
| 文件 | 操作 |
|------|------|
| `src/sloth_agent/core/context_window.py` | 修改 (增强) |
| `src/sloth_agent/core/token_counter.py` | 新建 |
| `tests/core/test_token_counter.py` | 新建 |
| `tests/core/test_context_truncation.py` | 新建 |

---

## Task V1-5: Adaptive Execution（自适应重规划）

> Arch: `00000000-00-architecture-overview.md` §6.0
> Spec: `20260416-01-phase-role-architecture-spec.md`
> Depends: Task V1-4

### 实现内容
1. **AdaptiveTrigger** (`src/sloth_agent/core/adaptive.py`)
   - 检测触发条件: gate 失败、context 不足、plan 偏离
   - `should_replan()`: 判断是否需要重新规划

2. **Replanner** (`src/sloth_agent/core/replanner.py`)
   - 接收当前状态 + 原始 plan → 生成 updated plan
   - 使用 LLM 或规则-based 重规划
   - 输出 `PlanUpdate` dataclass

3. **Runner 集成**
   - 在 Runner 的 turn 循环中检测 adaptive trigger
   - 触发 replan → 更新 plan → 继续执行

4. **测试**
   - `tests/core/test_adaptive_trigger.py`: 触发条件检测
   - `tests/core/test_replanner.py`: 重规划逻辑

### 文件清单
| 文件 | 操作 |
|------|------|
| `src/sloth_agent/core/adaptive.py` | 新建 |
| `src/sloth_agent/core/replanner.py` | 新建 |
| `src/sloth_agent/core/runner.py` | 修改 (集成 trigger) |
| `tests/core/test_adaptive_trigger.py` | 新建 |
| `tests/core/test_replanner.py` | 新建 |
