# 事件系统规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

多 Agent spec 定义了 SQLite 为基础的 MessageBus，但它是点对点消息，不是发布-订阅事件总线。

跨模块通信需要统一的事件架构：
- "Phase 完成" → 触发报告生成
- "预算超支" → 触发降级执行
- "安全违规" → 触发通知
- "场景完成" → 触发下一个场景

没有事件系统，模块间耦合，扩展困难。

---

## 2. 事件架构

### 2.1 事件总线

```
┌─────────────────────────────────────────────────────────┐
│                    Event Bus                             │
│                                                          │
│  Publisher          ──→  Event Router  ──→  Subscriber   │
│  (Agent)                          │  ┌─→  Report          │
│  (Tool)                           ├─→  Notification      │
│  (Daemon)                         ├─→  CostTracker       │
│                                   ├─→  ErrorRecovery     │
│                                   └─→  SessionManager    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 事件定义

```python
@dataclass
class Event:
    """系统事件。"""
    event_id: str                  # 唯一标识
    event_type: str                # 事件类型
    source: str                    # 事件来源（模块名）
    timestamp: float
    payload: dict                  # 事件数据
    trace_id: str | None = None    # 关联的 trace ID
    priority: int = 0              # 优先级（高的先处理）

    # 元数据
    headers: dict = field(default_factory=dict)
```

### 2.3 事件类型清单

| 事件类型 | 来源 | 订阅者 | 说明 |
|----------|------|--------|------|
| `agent.started` | Daemon | Report, Session | Agent 启动 |
| `agent.stopped` | Daemon | Report, Session | Agent 停止 |
| `scenario.started` | Orchestrator | Report, Session | 场景开始 |
| `scenario.completed` | Orchestrator | Report, Cost, Session | 场景完成 |
| `scenario.failed` | Orchestrator | Report, Error, Notification | 场景失败 |
| `phase.entered` | PhaseExecutor | Session, Cost | 进入 Phase |
| `phase.completed` | PhaseExecutor | Report, Cost, Session, Event Router(触发下一Phase) | Phase 完成 |
| `phase.failed` | PhaseExecutor | Error, Notification | Phase 失败 |
| `phase.gate.passed` | GateValidator | Report, Session | 门控通过 |
| `phase.gate.failed` | GateValidator | Error, Notification | 门控失败 |
| `tool.called` | ToolOrchestrator | Cost, Observability | 工具调用 |
| `tool.blocked` | RiskGate | Security, Notification | 工具被拦截 |
| `llm.requested` | LLMRouter | Cost | LLM 请求 |
| `llm.completed` | LLMRouter | Cost | LLM 响应 |
| `llm.fallback` | LLMRouter | Notification | 模型降级 |
| `budget.warning` | CostTracker | Notification, Error | 预算警告 |
| `budget.exceeded` | CostTracker | Error, Notification | 预算超支 |
| `security.violation` | Security | Notification, Error | 安全违规 |
| `health.unhealthy` | HealthChecker | Error, Notification | 健康异常 |
| `session.created` | SessionManager | Report | 会话创建 |
| `session.paused` | SessionManager | Report | 会话暂停 |
| `session.resumed` | SessionManager | Report | 会话恢复 |
| `session.completed` | SessionManager | Report, Cost | 会话完成 |
| `session.failed` | SessionManager | Error, Notification | 会话失败 |
| `notification.sent` | NotificationManager | Observability | 通知发送 |
| `report.generated` | ReportGenerator | Notification | 报告生成 |
| `skill.evolved` | SkillEvolution | Observability, Notification | 技能进化 |

---

## 3. 事件总线实现

```python
class EventBus:
    """发布-订阅事件总线。

    支持同步和异步事件处理。
    支持事件持久化（用于回放和调试）。
    """

    def __init__(self, config: Config,
                 persist: bool = True,
                 log_manager: LogManager | None = None):
        self.config = config
        self.persist = persist
        self.log_manager = log_manager

        # handlers[event_type_pattern] = [handler1, handler2, ...]
        self.handlers: dict[str, list[EventHandler]] = {}
        # 同步队列（高优先级事件）
        self.sync_queue: PriorityQueue = PriorityQueue()
        # 异步队列（低优先级事件）
        self.async_queue: Queue = Queue()

        self.event_store: list[Event] = []
        self.running = False

    def subscribe(self, event_pattern: str,
                  handler: EventHandler) -> str:
        """订阅事件。

        event_pattern 支持通配符：
        - "phase.*" 匹配所有 phase 事件
        - "*.completed" 匹配所有完成事件
        - "phase.completed" 精确匹配
        """
        if event_pattern not in self.handlers:
            self.handlers[event_pattern] = []
        self.handlers[event_pattern].append(handler)

        handler_id = f"{event_pattern}:{handler.__name__}"
        return handler_id

    def unsubscribe(self, handler_id: str) -> None:
        """取消订阅。"""
        for pattern, handlers in self.handlers.items():
            self.handlers[pattern] = [
                h for h in handlers
                if f"{pattern}:{h.__name__}" != handler_id
            ]

    def publish(self, event: Event, sync: bool = False) -> None:
        """发布事件。"""
        # 持久化
        if self.persist:
            self.event_store.append(event)

        # 写入日志
        if self.log_manager:
            self.log_manager.log(
                level="INFO",
                trace_id=event.trace_id or "",
                agent_id=event.headers.get("agent_id", ""),
                phase_id=event.headers.get("phase_id", ""),
                event_type=event.event_type,
                message=event.event_type,
                details=event.payload,
                layer="app",
            )

        # 路由
        if sync:
            self.sync_queue.put((event.priority, event))
            self._process_sync(event)
        else:
            self.async_queue.put(event)

        # 异步处理
        self._dispatch_async(event)

    def _dispatch_async(self, event: Event) -> None:
        """异步分发事件到匹配的处理器。"""
        matched = self._find_matching_handlers(event.event_type)
        for handler in matched:
            try:
                handler.handle(event)
            except Exception as e:
                logger.error(f"Event handler error: {handler.__name__} - {e}")
                # 发送到死信队列
                self._send_to_dead_letter(event, handler, e)

    def _process_sync(self, event: Event) -> None:
        """同步处理事件（阻塞直到所有处理器完成）。"""
        matched = self._find_matching_handlers(event.event_type)
        for handler in matched:
            handler.handle(event)

    def _find_matching_handlers(self, event_type: str) -> list[EventHandler]:
        """查找匹配事件的处理器。"""
        matched = []
        for pattern, handlers in self.handlers.items():
            if self._match_pattern(pattern, event_type):
                matched.extend(handlers)
        return matched

    def _match_pattern(self, pattern: str, event_type: str) -> bool:
        """通配符匹配。"""
        pattern_parts = pattern.split(".")
        type_parts = event_type.split(".")

        if len(pattern_parts) != len(type_parts):
            return False

        for p, t in zip(pattern_parts, type_parts):
            if p != "*" and p != t:
                return False

        return True

    def _send_to_dead_letter(self, event: Event,
                              handler: EventHandler, error: Exception) -> None:
        """发送到死信队列。"""
        dead_letter = {
            "event": asdict(event),
            "handler": handler.__name__,
            "error": str(error),
            "timestamp": time.time(),
        }
        dead_letter_file = Path("logs/dead_letter.jsonl")
        with open(dead_letter_file, "a") as f:
            f.write(json.dumps(dead_letter) + "\n")
```

---

## 4. 事件处理器

```python
class EventHandler(ABC):
    """事件处理器基类。"""

    @abstractmethod
    def handle(self, event: Event) -> None:
        """处理事件。"""
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__


# 示例：Phase 完成后自动生成报告
class AutoReportHandler(EventHandler):
    """Phase 完成后自动生成 Phase 报告。"""

    def __init__(self, report_generator: ReportGenerator):
        self.report_gen = report_generator

    def handle(self, event: Event) -> None:
        if event.event_type == "phase.completed":
            phase_result = PhaseResult.from_dict(event.payload)
            self.report_gen.generate_phase_report(phase_result)


# 示例：预算警告时发送通知
class BudgetAlertHandler(EventHandler):
    """预算超限时发送告警。"""

    def __init__(self, notification_manager: NotificationManager):
        self.notifications = notification_manager

    def handle(self, event: Event) -> None:
        if event.event_type == "budget.warning":
            self.notifications.send(Notification(
                notification_id=uuid4().hex[:12],
                priority=NotificationPriority.NORMAL,
                title=f"Budget Warning: {event.payload.get('message', '')}",
                body=f"Budget usage: {event.payload.get('used_percent', 0):.0f}%",
                event_type="budget.warning",
                category="cost",
                timestamp=time.time(),
            ))
        elif event.event_type == "budget.exceeded":
            self.notifications.send(Notification(
                notification_id=uuid4().hex[:12],
                priority=NotificationPriority.CRITICAL,
                title="Budget Exceeded - Agent shutting down",
                body=f"Daily budget of ¥{event.payload.get('limit', 0)} has been exceeded.",
                event_type="budget.exceeded",
                category="cost",
                timestamp=time.time(),
            ))
```

---

## 5. 事件驱动的工作流触发

```python
class EventDrivenWorkflow:
    """基于事件的工作流触发器。

    定义事件到动作的映射规则。
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.rules: list[WorkflowRule] = []

    def add_rule(self, rule: WorkflowRule) -> None:
        """添加工作流规则。"""
        self.rules.append(rule)
        self.event_bus.subscribe(rule.trigger_event, self._handle)

    def _handle(self, event: Event) -> None:
        """处理触发事件。"""
        for rule in self.rules:
            if self._match(event, rule):
                rule.action(event)

    def _match(self, event: Event, rule: WorkflowRule) -> bool:
        """检查事件是否匹配规则。"""
        if rule.condition and not rule.condition(event):
            return False
        return True


@dataclass
class WorkflowRule:
    """工作流规则。"""
    rule_id: str
    trigger_event: str          # 触发事件
    action: Callable[[Event], None]  # 执行动作
    condition: Callable[[Event], bool] | None = None  # 触发条件
    enabled: bool = True


# 内置规则
BUILTIN_RULES = [
    WorkflowRule(
        rule_id="phase-to-report",
        trigger_event="phase.completed",
        action=lambda e: None,  # 由 AutoReportHandler 实现
        condition=lambda e: e.payload.get("generate_report", True),
    ),
    WorkflowRule(
        rule_id="phase-to-next",
        trigger_event="phase.completed",
        action=lambda e: None,  # 触发下一个 Phase
    ),
    WorkflowRule(
        rule_id="failure-to-recovery",
        trigger_event="phase.failed",
        action=lambda e: None,  # 触发恢复
        condition=lambda e: e.payload.get("retry_count", 0) < 3,
    ),
    WorkflowRule(
        rule_id="scenario-to-report",
        trigger_event="scenario.completed",
        action=lambda e: None,  # 生成场景报告
    ),
]
```

---

## 6. 事件持久化与回放

```python
class EventReplay:
    """事件回放工具。

    用于调试和审计：重放指定时间段的事件。
    """

    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def replay(self, start_time: float, end_time: float | None = None,
                event_filter: str | None = None) -> list[Event]:
        """回放事件。"""
        events = self.event_bus.event_store

        filtered = [
            e for e in events
            if e.timestamp >= start_time
            and (end_time is None or e.timestamp <= end_time)
            and (event_filter is None or
                 self._match_pattern(event_filter, e.event_type))
        ]

        return filtered

    def export(self, start_time: float, end_time: float | None = None,
                format: str = "jsonl") -> str:
        """导出事件到文件。"""
        events = self.replay(start_time, end_time)

        if format == "jsonl":
            output = Path(f"logs/events-{int(start_time)}.jsonl")
            with open(output, "w") as f:
                for e in events:
                    f.write(json.dumps(asdict(e)) + "\n")
            return str(output)

        elif format == "markdown":
            output = Path(f"reports/events-{int(start_time)}.md")
            with open(output, "w") as f:
                f.write("# Event Timeline\n\n")
                for e in events:
                    ts = datetime.fromtimestamp(e.timestamp).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    f.write(f"- [{ts}] **{e.event_type}**\n")
                    if e.payload:
                        f.write(f"  ```json\n")
                        f.write(json.dumps(e.payload, indent=2))
                        f.write(f"\n  ```\n")
            return str(output)
```

---

## 6.1 v1.x — 轻量 Hook 系统

> v1.x 采用同步 hooks，无持久化、无死信队列，满足基本扩展需求。

```python
class HookManager:
    hooks: dict[str, list[Callable]]

    def on(self, event: str, handler: Callable): ...
    def emit(self, event: str, data: Any): ...
```

内置 hook 点：

| Hook 点 | 时机 | 用途 |
|---------|------|------|
| `run.start` / `run.end` | run 生命周期 | 记录开始/结束时间 |
| `phase.start` / `phase.end` | 当前 owner/phase 生命周期 | Phase 级统计 |
| `model.start` / `model.end` | 模型调用前后 | Token 计数、费用追踪 |
| `tool.start` / `tool.end` | 工具调用前后 | 工具使用统计 |
| `handoff` | ownership transfer | 交接记录 |
| `gate.pass` / `gate.fail` | 自动门禁结果 | 质量统计 |
| `reflection` | 结构化反思产出 | 学习记录 |
| `resume` | interruption 恢复 | 恢复追踪 |
| `budget.warn` / `budget.over` | 预算警告/超支 | 费用告警 |

v1.x tracing 的最小粒度应覆盖：run、turn、model call、tool call、handoff、gate failure、interruption / resume。Hook 与 tracing 都是 runtime 的观察面，不应侵入业务执行逻辑。

---

## 7. 配置

```yaml
# configs/events.yaml
events:
  persist: true                    # 是否持久化事件
  max_history: 10000               # 最大保留事件数（内存中）
  dead_letter:
    enabled: true
    log_path: "logs/dead_letter.jsonl"

  handlers:
    auto_report: true              # Phase 完成后自动生成报告
    auto_next: true                # Phase 完成后自动触发下一个
    budget_alert: true             # 预算告警
    failure_recovery: true         # 失败自动恢复
```

---

## 8. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/events/__init__.py` | 事件模块入口 |
| `src/sloth_agent/events/bus.py` | EventBus 事件总线 |
| `src/sloth_agent/events/handlers.py` | 内置事件处理器 |
| `src/sloth_agent/events/workflow_rules.py` | 事件驱动工作流规则 |
| `src/sloth_agent/events/replay.py` | EventReplay 事件回放 |
| `src/sloth_agent/events/models.py` | 事件数据模型 |
| `configs/events.yaml` | 事件配置 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
