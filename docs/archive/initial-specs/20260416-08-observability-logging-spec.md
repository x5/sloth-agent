# 可观测性与日志规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

Sloth Agent 当前存在多个孤立的日志源：
- Tools spec 定义了 `logs/tool-calls.jsonl`
- Security spec 定义了 `logs/security.jsonl`
- Daemon spec 定义了 `logs/metrics.jsonl`

但缺少统一标准，导致：
1. 8 个 Agent 并行执行时无法通过 trace ID 关联同一工作流的操作
2. 没有日志轮转和保留策略，日志可能无限增长
3. 没有跨模块的日志查询和诊断能力
4. 无法区分"Agent 做了什么"和"系统出了什么错"

---

## 2. 日志架构

### 2.1 日志分层

```
┌────────────────────────────────────────────────────────────┐
│                    统一日志框架                              │
│                                                              │
│  Layer 1: Application Log (app.log)                         │
│    - Agent 生命周期、Phase 切换、Skill 激活                   │
│    - 面向运维和开发者                                        │
│                                                              │
│  Layer 2: Conversation Log (conversations/<session>.jsonl)   │
│    - LLM 对话记录、tool call 详情、skill 上下文               │
│    - 面向审计和回溯                                           │
│                                                              │
│  Layer 3: Tool Call Log (tool-calls.jsonl)                  │
│    - 工具调用的输入输出、执行时间、风险等级                    │
│    - 面向安全审计和性能分析                                   │
│                                                              │
│  Layer 4: Security Log (security.jsonl)                     │
│    - 安全事件、路径违规、命令拦截、脱敏操作                    │
│    - 面向安全合规                                             │
│                                                              │
│  Layer 5: Metrics Log (metrics.jsonl)                       │
│    - 性能指标、资源使用、Token 消耗、预算                     │
│    - 面向运营和优化                                           │
└────────────────────────────────────────────────────────────┘
```

### 2.2 统一 Trace ID

```
Trace ID: sloth-{session_id}-{phase_id}-{seq}

示例:
  sloth-nightly-20260416-engineer-001
    ├── sloth-nightly-20260416-engineer-001 (Phase start)
    ├── sloth-nightly-20260416-engineer-001-read-002 (Tool call)
    ├── sloth-nightly-20260416-engineer-001-write-003 (Tool call)
    └── sloth-nightly-20260416-engineer-001 (Phase complete)
```

---

## 3. 日志格式标准

### 3.1 结构化日志格式

```python
@dataclass
class LogEntry:
    timestamp: float              # Unix timestamp
    level: str                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
    trace_id: str                 # 全局追踪 ID
    agent_id: str                 # 执行 Agent 标识
    phase_id: str                 # 所属 Phase 标识
    event_type: str               # 事件类型
    message: str                  # 人类可读描述
    details: dict                 # 结构化详情
    duration_ms: int | None = None  # 操作耗时

# 示例 JSONL 行：
{
    "ts": 1713254400.123,
    "level": "INFO",
    "trace_id": "sloth-nightly-20260416-engineer-001",
    "agent_id": "engineer",
    "phase_id": "implementation",
    "event": "tool.call",
    "message": "Tool read_file executed successfully",
    "details": {
        "tool_name": "read_file",
        "input": {"path": "src/main.py"},
        "output_length": 1523,
        "risk_level": 1
    },
    "duration_ms": 45
}
```

### 3.2 事件类型清单

| 事件类型 | 日志层 | 说明 |
|----------|--------|------|
| `agent.start` | app | Agent 启动 |
| `agent.stop` | app | Agent 停止 |
| `phase.enter` | app | 进入 Phase |
| `phase.exit` | app | 退出 Phase |
| `phase.gate.pass` | app | 门控通过 |
| `phase.gate.fail` | app | 门控失败 |
| `skill.activate` | app | 技能激活 |
| `skill.complete` | app | 技能完成 |
| `skill.error` | app | 技能错误 |
| `tool.call` | tool-calls | 工具调用 |
| `tool.blocked` | tool-calls | 工具被拦截 |
| `tool.timeout` | tool-calls | 工具超时 |
| `llm.request` | metrics | LLM 请求 |
| `llm.response` | metrics | LLM 响应 |
| `llm.error` | metrics | LLM 错误 |
| `llm.fallback` | metrics | 模型降级切换 |
| `conversation.turn` | conversations | 对话轮次 |
| `security.violation` | security | 安全违规 |
| `security.blocked` | security | 安全拦截 |
| `budget.warning` | metrics | 预算警告（80%） |
| `budget.exceeded` | metrics | 预算超支 |
| `health.heartbeat` | app | 心跳信号 |
| `health.unhealthy` | app | 健康异常 |
| `recovery.trigger` | app | 自动恢复触发 |
| `notification.sent` | app | 通知发送 |
| `session.create` | app | 会话创建 |
| `session.resume` | app | 会话恢复 |
| `session.end` | app | 会话结束 |
| `report.generated` | app | 报告生成 |
| `cost.update` | metrics | 费用更新 |

---

## 4. 日志管理器

```python
class LogManager:
    """统一日志管理器。

    所有模块通过此接口写入日志，
    自动路由到对应的日志文件。
    """

    def __init__(self, base_dir: str = "logs",
                 max_file_mb: int = 100,
                 retention_days: int = 30):
        self.base_dir = Path(base_dir)
        self.max_file_mb = max_file_mb
        self.retention_days = retention_days

        # 各日志层对应的文件
        self.log_files = {
            "app": self.base_dir / "app.jsonl",
            "tool-calls": self.base_dir / "tool-calls.jsonl",
            "security": self.base_dir / "security.jsonl",
            "metrics": self.base_dir / "metrics.jsonl",
        }

        # Conversation logs 按 session 分文件
        self.conversations_dir = self.base_dir / "conversations"

    def log(self, level: str, trace_id: str, agent_id: str,
            phase_id: str, event_type: str, message: str,
            details: dict | None = None, duration_ms: int | None = None,
            layer: str = "app") -> None:
        """写入日志条目。"""
        entry = LogEntry(
            timestamp=time.time(),
            level=level,
            trace_id=trace_id,
            agent_id=agent_id,
            phase_id=phase_id,
            event_type=event_type,
            message=message,
            details=details or {},
            duration_ms=duration_ms,
        )

        # 路由到对应日志文件
        if layer == "conversations":
            session_id = details.get("session_id", "unknown")
            log_file = self.conversations_dir / f"{session_id}.jsonl"
        else:
            log_file = self.log_files.get(layer, self.log_files["app"])

        # 确保目录存在
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 写入
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry)) + "\n")

        # 错误及以上级别额外写入 app.log
        if level in ("ERROR", "CRITICAL", "WARNING"):
            with open(self.log_files["app"], "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry)) + "\n")

        # 日志轮转检查
        self._check_rotation(log_file)

    def _check_rotation(self, log_file: Path) -> None:
        """检查是否需要轮转日志。"""
        if not log_file.exists():
            return
        size_mb = log_file.stat().st_size / (1024 * 1024)
        if size_mb >= self.max_file_mb:
            self._rotate(log_file)

    def _rotate(self, log_file: Path) -> None:
        """轮转日志：重命名带时间戳，创建新文件。"""
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        rotated = log_file.with_name(
            f"{log_file.stem}-{ts}{log_file.suffix}"
        )
        log_file.rename(rotated)
        logger.info(f"Rotated log: {log_file.name} -> {rotated.name}")

    def cleanup_old_logs(self) -> int:
        """清理超过保留期的日志。"""
        cutoff = time.time() - (self.retention_days * 86400)
        cleaned = 0
        for f in self.base_dir.rglob("*.jsonl"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                cleaned += 1
        return cleaned
```

---

## 5. Trace ID 生成器

```python
class TraceContext:
    """Trace 上下文管理器。

    支持嵌套 Trace，自动传播 trace_id 到子操作。
    """

    def __init__(self, session_id: str, agent_id: str, phase_id: str):
        self.session_id = session_id
        self.agent_id = agent_id
        self.phase_id = phase_id
        self.counter = 0

    def new_trace(self, suffix: str = "") -> str:
        """生成新的 trace ID。"""
        self.counter += 1
        seq = f"{self.counter:04d}"
        if suffix:
            return f"sloth-{self.session_id}-{self.phase_id}-{suffix}-{seq}"
        return f"sloth-{self.session_id}-{self.phase_id}-{seq}"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass
```

---

## 6. 日志查询 CLI

```python
@app.command()
def logs(
    level: str = typer.Option("INFO", "--level", "-l",
                               help="Filter by log level"),
    agent: str = typer.Option(None, "--agent", "-a",
                               help="Filter by agent ID"),
    phase: str = typer.Option(None, "--phase", "-p",
                               help="Filter by phase ID"),
    trace: str = typer.Option(None, "--trace", "-t",
                               help="Filter by trace ID"),
    follow: bool = typer.Option(False, "--follow", "-f",
                                 help="Tail logs in real-time"),
    limit: int = typer.Option(100, "--limit", "-n",
                               help="Max entries to show"),
    since: str = typer.Option(None, "--since", "-s",
                               help="Show entries since (ISO datetime)"),
    output: str = typer.Option("text", "--output", "-o",
                                help="Output format: text|json|table"),
):
    """Query and display Sloth Agent logs."""
    from sloth_agent.observability.log_query import LogQuerier

    querier = LogQuerier(base_dir="logs")
    entries = querier.query(
        level=level, agent_id=agent, phase_id=phase,
        trace_id=trace, since=since, limit=limit,
    )

    if follow:
        querier.tail(entries)
    else:
        querier.display(entries, format=output)
```

---

## 7. 日志保留与轮转策略

```yaml
# configs/observability.yaml
observability:
  logging:
    max_file_mb: 100          # 单文件最大 100MB
    retention_days: 30        # 保留 30 天
    rotation_count: 5         # 最多保留 5 个轮转文件
    flush_interval: 1         # 每条日志立即刷盘（低延迟优先）

    # 各层日志的文件路径
    layers:
      app: "logs/app.jsonl"
      tool_calls: "logs/tool-calls.jsonl"
      security: "logs/security.jsonl"
      metrics: "logs/metrics.jsonl"
      conversations: "logs/conversations/{session_id}.jsonl"

  tracing:
    enabled: true
    trace_id_format: "sloth-{session_id}-{phase_id}-{suffix}-{seq}"
    propagate_to_children: true

  diagnostics:
    debug_mode: false          # 开启后记录 DEBUG 级别日志
    slow_threshold_ms: 5000    # 超过此时间标记为慢操作
```

---

## 8. 健康看板集成

```python
class LogBasedHealthCheck:
    """基于日志的健康检查。

    补充 Daemon spec 的 Heartbeat 机制：
    通过分析最近日志判断 Agent 是否真正健康。
    """

    def __init__(self, log_manager: LogManager, window_seconds: int = 300):
        self.log_manager = log_manager
        self.window = window_seconds

    def check(self) -> HealthDiagnosis:
        """分析最近 5 分钟的日志。"""
        recent = self.log_manager.get_recent(
            layer="app",
            since=time.time() - self.window,
        )

        # 检查是否有错误风暴
        errors = [e for e in recent if e.level == "ERROR"]
        if len(errors) > 10:
            return HealthDiagnosis(
                status="degraded",
                reason=f"Error storm: {len(errors)} errors in {self.window}s",
                recommendation="Check tool-calls.jsonl for root cause",
            )

        # 检查心跳是否正常
        heartbeats = [e for e in recent if e.event_type == "health.heartbeat"]
        if not heartbeats:
            return HealthDiagnosis(
                status="warning",
                reason=f"No heartbeat in {self.window}s",
                recommendation="Check if daemon is still running",
            )

        # 检查是否有 Phase 长时间无进展
        last_phase_event = None
        for e in reversed(recent):
            if e.event_type in ("phase.enter", "phase.exit"):
                last_phase_event = e
                break

        if last_phase_event:
            age = time.time() - last_phase_event.timestamp
            if age > 1800:  # 30 分钟
                return HealthDiagnosis(
                    status="stuck",
                    reason=f"Phase {last_phase_event.phase_id} inactive for {age:.0f}s",
                    recommendation="Consider triggering recovery",
                )

        return HealthDiagnosis(status="healthy")
```

---

## 9. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/observability/__init__.py` | 可观测性模块入口 |
| `src/sloth_agent/observability/log_manager.py` | LogManager 统一日志管理器 |
| `src/sloth_agent/observability/trace_context.py` | TraceContext trace ID 生成器 |
| `src/sloth_agent/observability/log_query.py` | LogQuerier 日志查询 CLI |
| `src/sloth_agent/observability/health_diagnosis.py` | 基于日志的健康诊断 |
| `src/sloth_agent/observability/models.py` | 日志数据模型 |
| `configs/observability.yaml` | 可观测性配置 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
