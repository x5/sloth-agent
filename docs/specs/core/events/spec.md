# 事件系统

> 归档参考: archive/initial-specs/20260416-14-event-system-spec.md
> 最后更新: 2026-05-06
> 状态: 规划中（v1.0 使用 HookManager 作为轻量替代，预计 Iter-10+ 实现 EventBus）
> Scope: Core

## 1. 问题域

当前 HookManager 是同步回调，无法满足以下需求：

1. **模块解耦**：Phase 完成 → 自动生成报告、发送通知、记录审计——这些消费者不应该侵入 Phase 执行代码
2. **异步处理**：预算告警事件不应该阻塞 Agent 执行循环
3. **通配符订阅**：`phase.*` 匹配所有 phase 事件，`*.failed` 匹配所有失败——HookManager 需要逐个注册
4. **事件持久化**：调试时需要回放事件时间线
5. **可靠投递**：事件处理器崩溃不应该丢事件

## 2. 参考设计

### 2.1 OpenClaw 的 Gateway 事件模型

OpenClaw 的 Gateway 作为事件中心，所有组件通过 WebSocket 连接：

- **事件类型**：`agent`, `chat`, `presence`, `health`, `heartbeat`, `cron`, `tick`, `shutdown`
- **事件协议**：`{type: "event", event: "<name>", payload: {...}, seq: N, stateVersion: "..."}`
- **持久化保证**：OutboundEvent 先写磁盘再分发，Delivery Worker ack 后才删除——确保消息不丢
- **Hook 体系**：`before_model_resolve`, `before_agent_start`, `agent_end`, `before/after_tool_call`, `message_received/sent`, `session_start/end` 等二十余个钩子点
- **去重**：idempotency key + 短周期去重缓存

**对我们有价值的模式**：
- 事件 + seq 号实现有序投递
- 先持久化再投递，ack 后删除的可靠性模型
- 丰富的 hook 点分类（生命周期、工具、消息、会话）

### 2.2 行业最佳实践：CloudEvents + Pub/Sub

| 实践 | 说明 |
|------|------|
| **CloudEvents 规范** | CNCF 标准事件格式：`id`, `source`, `specversion`, `type` 四个必填字段 + 可选 `datacontenttype`, `data`, `time`, `subject` |
| **幂等性** | 基于 event_id 去重，消费者必须幂等 |
| **Outbox 模式** | 写业务变更时同步写事件到同一事务，后台异步投递 |
| **死信队列（DLQ）** | 处理失败的事件路由到 DLQ，不阻塞正常事件流 |
| **背压控制** | 有界通道 + drop-oldest 策略，发布者永不阻塞 |
| **相关追踪** | 每个事件带 correlation_id，贯穿整个 Agent 调用链 |

### 2.3 与 HookManager 的关系

```
HookManager (v1.0)              EventBus (v2.0)
────────────────────            ─────────────────
同步回调                         异步 + 同步双队列
硬编码事件名                     通配符匹配（"phase.*"）
无持久化                         持久化 + 回放
无 DLQ                          死信队列
一对一定向注册                    发布/订阅，多消费者
CLI 层实现 (runner.py)           Core 层实现，CLI/Desktop 共享
```

迁移策略：EventBus 发布时同时调用 HookManager（兼容期），逐步将 HookManager 的消费者迁移到 EventBus 订阅。

## 3. 事件模型（遵循 CloudEvents 子集）

### 3.1 Event

```python
class Event(BaseModel):
    """系统事件（基于 CloudEvents 规范子集）。"""
    event_id: str                       # 全局唯一 ID（UUIDv7）
    event_type: str                     # 点分事件类型，如 "phase.completed"
    source: str                         # 事件来源模块，如 "runner", "brainstorm", "gate"
    timestamp: float
    data: dict[str, Any] = {}           # 事件负载
    datacontenttype: str = "application/json"
    trace_id: str | None = None         # W3C TraceContext traceparent
    correlation_id: str | None = None   # 关联的 run_id / task_id
    priority: int = 0                   # 0=normal, 1=high, 2=critical
    headers: dict[str, str] = {}
```

### 3.2 事件类型目录

#### 运行时生命周期

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `run.started` | Runner | Run 开始 |
| `run.completed` | Runner | Run 正常结束 |
| `run.failed` | Runner | Run 异常终止 |
| `run.paused` | Runner | Run 暂停 |
| `run.resumed` | Runner | Run 恢复 |

#### Phase 生命周期

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `phase.started` | Runner | Phase 开始 |
| `phase.completed` | Runner | Phase 完成 |
| `phase.failed` | Runner | Phase 失败 |

#### 门控

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `gate.passed` | GateValidator | 门控通过 |
| `gate.failed` | GateValidator | 门控失败 |

#### Agent 生命周期

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `agent.started` | Runner/Coordinator | Agent 开始执行 |
| `agent.completed` | Runner/Coordinator | Agent 完成 |
| `agent.failed` | Runner/Coordinator | Agent 失败 |
| `agent.handoff` | Runner | Agent 交接 |

#### 模型调用

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `model.request` | LLMRouter | LLM 请求发送前 |
| `model.response` | LLMRouter | LLM 响应返回后 |
| `model.fallback` | LLMRouter | 模型降级 |

#### 工具调用

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `tool.called` | ToolOrchestrator | 工具调用 |
| `tool.completed` | ToolOrchestrator | 工具返回 |
| `tool.blocked` | RiskGate | 工具被安全策略拦截 |

#### 预算与成本

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `budget.warning` | CostTracker | 预算使用达到阈值（如 80%） |
| `budget.exceeded` | CostTracker | 预算超支 |

#### 会话

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `session.created` | SessionManager | 会话创建 |
| `session.completed` | SessionManager | 会话完成 |

#### 通知与报告

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `notification.sent` | NotificationManager | 通知已发送 |
| `report.generated` | ReportGenerator | 报告已生成 |

#### 健康检查

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `health.unhealthy` | HealthChecker | 健康异常 |
| `health.recovered` | HealthChecker | 健康恢复 |

#### 协调编排（关联 coordination 模块）

| 事件类型 | 来源 | 说明 |
|----------|------|------|
| `task.dispatched` | Coordinator | 子任务已分发 |
| `task.completed` | Coordinator | 子任务完成 |
| `task.failed` | Coordinator | 子任务失败 |
| `merge.conflict` | ResultMerger | 合并发现冲突 |

## 4. 事件总线

### 4.1 EventBus

```python
class EventBus:
    """发布-订阅事件总线。

    核心特性：
    - 通配符匹配订阅（"phase.*" 匹配所有 phase 事件）
    - 同步 + 异步双队列（critical 事件走同步，其余异步）
    - 事件持久化（用于回放、调试、审计）
    - 死信队列（处理失败的事件不阻塞正常流）
    - 发布者永不阻塞（有界队列 + drop-oldest）

    设计约束：
    - 禁止在 handler 中执行超过 1s 的同步操作（用异步队列）
    - 禁止在 handler 中 publish 事件（禁止级联，会导致事件风暴）
    - handler 抛异常时自动路由到 DLQ，不影响其他 handler
    """

    def __init__(self, config: EventBusConfig):
        self.handlers: dict[str, list[EventHandler]] = {}
        self.sync_queue: PriorityQueue  = PriorityQueue()
        self.async_queue: Queue = Queue(maxsize=256)
        self.event_store: list[Event] = []
        self.dead_letter: list[DeadLetter] = []
        self._stats: EventStats

    # -- 订阅管理 --
    def subscribe(self, pattern: str, handler: EventHandler) -> str:
        """订阅事件。返回 subscription_id 用于 unsubscribe。

        pattern 语法：
        - "phase.completed" → 精确匹配
        - "phase.*" → 匹配所有 phase.* 事件
        - "*.completed" → 匹配所有 *.completed 事件
        - "*.*" → 匹配所有双段事件
        """

    def unsubscribe(self, subscription_id: str) -> None: ...

    # -- 发布 --
    async def publish(self, event: Event) -> None:
        """发布事件。

        流程：
        1. 分配 event_id（如果发布者未提供）
        2. 持久化到 event_store
        3. 查找匹配的 handler
        4. critical 事件 → sync_queue（阻塞执行）
           普通事件 → async_queue（异步执行）
        """

    # -- 查询 --
    async def replay(self, start: float, end: float | None = None,
                     event_type: str | None = None) -> list[Event]:
        """回放时间段内的事件。"""

    async def stats(self) -> EventStats:
        """返回事件统计：published/delivered/dropped/dead_letter 计数。"""

    # -- 内部 --
    def _match(self, pattern: str, event_type: str) -> bool:
        """通配符匹配。"""

    async def _dispatch(self, event: Event) -> None:
        """异步分发到匹配的 handler。"""

    async def _send_to_dlq(self, event: Event, handler_id: str, error: Exception) -> None:
        """处理失败的事件进入死信队列。"""
```

### 4.2 EventHandler

```python
class EventHandler(ABC):
    """事件处理器基类。"""

    @abstractmethod
    async def handle(self, event: Event) -> None:
        """处理事件。必须幂等——同一个 event 可能投递多次。"""
        ...

    @property
    def name(self) -> str:
        return type(self).__name__
```

## 5. 内置处理器

### 5.1 AutoReportHandler

Phase 完成后自动生成报告：

```python
class AutoReportHandler(EventHandler):
    """订阅 phase.completed → 生成 Phase 报告"""

    async def handle(self, event: Event) -> None:
        report = await self.report_gen.generate(event.data)
        # 报告生成后 publish report.generated 事件（不在 handle 中直接 publish，
        # 而是通过独立的后台任务）
```

### 5.2 BudgetAlertHandler

预算告警：

```python
class BudgetAlertHandler(EventHandler):
    """订阅 budget.warning / budget.exceeded → 发送通知"""

    async def handle(self, event: Event) -> None:
        if event.event_type == "budget.warning":
            priority = NotificationPriority.NORMAL
        else:
            priority = NotificationPriority.CRITICAL
        await self.notifications.send(...)
```

### 5.3 HookAdapter（兼容层）

```python
class HookAdapter(EventHandler):
    """将 EventBus 事件桥接到 v1.0 HookManager。

    在兼容期内，EventBus 发布事件时同步调用 HookManager.emit()。
    此 handler 的优先级最低，在 v2.0 中移除。
    """

    def __init__(self, hook_manager: HookManager):
        self.hook_manager = hook_manager

    async def handle(self, event: Event) -> None:
        self.hook_manager.emit(event.event_type, event.data)
```

## 6. 可靠投递

### 6.1 持久化投递（Outbox 风格）

```
publish(event)
    │
    ├── 1. 写入 event_store (JSONL 追加)
    │
    ├── 2. 查找匹配 handler
    │
    └── 3. 入队 (async_queue)
            │
            ├── 成功 → 标记 delivered
            │
            └── 失败 → 写入 dead_letter.jsonl + 递增 retry_count
                       │
                       └── retry_count < max_retries → 重新入队
```

### 6.2 死信队列

```python
@dataclass
class DeadLetter:
    event: Event
    handler_id: str
    error: str
    timestamp: float
    retry_count: int = 0
```

死信文件 `logs/dead_letter.jsonl` 支持手动检查和重新投递。

## 7. 事件驱动工作流

```python
class WorkflowRule(BaseModel):
    """事件 → 动作的声明式规则。"""
    rule_id: str
    trigger: str                                      # 事件类型（支持通配符）
    action: str                                       # 动作名称（在 ActionRegistry 注册）
    condition: dict[str, Any] | None = None            # 触发条件
    enabled: bool = True
    cooldown_seconds: int = 0                          # 冷却时间（防止频繁触发）


BUILTIN_RULES = [
    WorkflowRule(
        rule_id="phase-completed→report",
        trigger="phase.completed",
        action="generate_phase_report",
    ),
    WorkflowRule(
        rule_id="phase-completed→next",
        trigger="phase.completed",
        action="advance_to_next_phase",
    ),
    WorkflowRule(
        rule_id="phase-failed→recovery",
        trigger="phase.failed",
        action="trigger_recovery",
        condition={"retry_count": {"$lt": 3}},
        cooldown_seconds=60,
    ),
    WorkflowRule(
        rule_id="gate-failed→replan",
        trigger="gate.failed",
        action="trigger_replan",
    ),
]
```

## 8. 可观测性

### 8.1 指标

```python
class EventStats(BaseModel):
    """EventBus 运行时统计。"""
    events_published: int       # 累计发布
    events_delivered: int       # 累计投递成功
    events_dropped: int         # 累计丢弃（队列满）
    events_dead_letter: int     # 累计死信
    handlers_registered: int    # 当前注册的 handler 数
    avg_dispatch_ms: float      # 平均分发延迟
    queue_depth: int            # 当前异步队列深度
```

### 8.2 事件时间线（调试用）

```bash
$ sloth events replay --from "2026-05-06 10:00" --to "2026-05-06 11:00" --type "phase.*"
[10:03:01] phase.started   | build
[10:15:42] phase.completed | build  | duration=761s
[10:15:43] gate.passed     | gate1  | lint=ok, type=ok
[10:15:44] phase.started   | review
[10:18:22] phase.completed | review | duration=158s
```

## 9. 反模式与约束

| 禁止 | 原因 |
|------|------|
| handler 中 publish 事件 | 可能形成事件风暴，难以追踪因果关系 |
| handler 中执行同步长任务（>1s） | 阻塞异步队列，影响所有消费者 |
| 依赖事件投递顺序 | 异步投递不保证顺序，handler 必须有状态校验 |
| 在事件中放大体积数据 | Event 保持轻量（< 1KB），大对象用引用（memory key / file path） |
| 事件类型超过 3 段 | event_type 保持两段式（`module.action`），便于分组匹配 |

## 10. 演进路线

| 版本 | 内容 |
|------|------|
| v1.0（已实现） | HookManager 同步回调，9 个 hook 点 |
| v2.0 | EventBus（async + sync 队列、通配符、持久化、DLQ）+ HookAdapter 兼容层 |
| v2.1 | WorkflowRules 声明式工作流 + 事件回放 CLI |
| v3.0 | 跨进程事件桥接（Desktop sidecar ↔ CLI Runner 事件同步） |

## 11. 配置

```yaml
# configs/events.yaml
events:
  persist: true
  persist_path: "./run/events.jsonl"
  max_memory_events: 10000

  async_queue:
    maxsize: 256
    overflow: drop_oldest

  dead_letter:
    enabled: true
    path: "./run/dead_letter.jsonl"
    max_retries: 3

  builtin_handlers:
    auto_report: true
    budget_alert: true
    hook_adapter: true       # v1.0 兼容桥

  workflow_rules:
    phase_to_report: true
    phase_to_next: true
    failure_recovery: true
    gate_to_replan: true

  observability:
    stats_interval_seconds: 60
    trace_header: "traceparent"
```

## 12. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/events/__init__.py` | 事件模块入口 |
| `src/sloth_agent/events/bus.py` | EventBus 核心实现 |
| `src/sloth_agent/events/models.py` | Event / DeadLetter / EventStats 数据模型 |
| `src/sloth_agent/events/handlers.py` | 内置处理器（AutoReport, BudgetAlert, HookAdapter） |
| `src/sloth_agent/events/rules.py` | WorkflowRule 声明式工作流 |
| `src/sloth_agent/events/replay.py` | EventReplay CLI + API |
| `src/sloth_agent/events/persistence.py` | JSONL 事件存储读写 |
| `configs/events.yaml` | 事件配置 |
