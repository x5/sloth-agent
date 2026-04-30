# 错误处理与恢复规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

现有规范中：
- Daemon spec 有 RecoveryStrategy 处理进程级崩溃（API 不可用、OOM、进程死）
- Tools spec 有 RollbackManager 处理工具级失败

但缺少**工作流级别的错误处理**：
1. Phase 门控连续失败 3 次怎么办？
2. 某个场景执行到一半卡住了怎么办？
3. 预算耗尽中途如何处理？
4. 多个 Agent 并行时一个失败了怎么影响其他？
5. LLM Provider 连续失败是否需要熔断？

---

## 2. 错误分类体系

### 2.1 错误层级

```
┌─────────────────────────────────────────────────────────┐
│  Level 4: Scenario/Workflow Level                        │
│    - 场景整体失败、Phase 连续门控失败、超时               │
│    - 处理：跳过剩余 Phase、通知用户、生成报告             │
├─────────────────────────────────────────────────────────┤
│  Level 3: Phase Level                                    │
│    - Phase 内部技能连续失败、Phase 超时                   │
│    - 处理：重试 Phase、降级执行（跳过非关键技能）、       │
│           回滚到上一个 checkpoint                        │
├─────────────────────────────────────────────────────────┤
│  Level 2: Skill Level                                    │
│    - 技能执行失败、LLM 响应异常、工具调用失败             │
│    - 处理：重试技能、切换模型、切换工具替代方案           │
├─────────────────────────────────────────────────────────┤
│  Level 1: Tool Level                                     │
│    - 单个工具调用超时、权限拒绝、路径违规                 │
│    - 处理：重试工具、报告给上层                           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 错误类型

```python
class ErrorCategory(Enum):
    """错误分类。"""

    # 基础设施错误
    INFRASTRUCTURE = "infrastructure"     # 网络、磁盘、进程
    API_UNAVAILABLE = "api_unavailable"   # LLM API 不可用
    RATE_LIMITED = "rate_limited"         # API 限流
    TIMEOUT = "timeout"                   # 操作超时
    OOM = "oom"                           # 内存不足

    # 工具执行错误
    TOOL_ERROR = "tool_error"            # 工具内部错误
    PERMISSION_DENIED = "permission_denied"  # 权限不足
    PATH_VIOLATION = "path_violation"    # 路径违规
    COMMAND_BLOCKED = "command_blocked"  # 命令被拦截

    # 工作流错误
    PHASE_GATE_FAILED = "phase_gate_failed"     # 门控失败
    SCENARIO_STUCK = "scenario_stuck"    # 场景卡住
    BUDGET_EXCEEDED = "budget_exceeded"  # 预算超支
    CONTEXT_LOST = "context_lost"        # 上下文丢失

    # 技能错误
    SKILL_NOT_FOUND = "skill_not_found"  # 技能不存在
    SKILL_TIMEOUT = "skill_timeout"      # 技能超时
    SKILL_LOOP_ERROR = "skill_loop_error"  # 技能内部错误
```

---

## 3. 错误处理策略

### 3.1 重试策略

```python
@dataclass
class RetryPolicy:
    """重试策略。"""
    max_retries: int              # 最大重试次数
    backoff_base: float           # 退避基数（秒）
    backoff_max: float            # 最大退避时间
    retry_on: list[ErrorCategory]  # 哪些错误类型可重试
    timeout_seconds: float        # 单次超时

# 各层级的默认重试策略
RETRY_POLICIES = {
    "tool": RetryPolicy(
        max_retries=3,
        backoff_base=1.0,
        backoff_max=30.0,
        retry_on=[ErrorCategory.TIMEOUT, ErrorCategory.RATE_LIMITED],
        timeout_seconds=60.0,
    ),
    "skill": RetryPolicy(
        max_retries=2,
        backoff_base=5.0,
        backoff_max=60.0,
        retry_on=[ErrorCategory.TOOL_ERROR, ErrorCategory.SKILL_LOOP_ERROR],
        timeout_seconds=300.0,
    ),
    "phase": RetryPolicy(
        max_retries=1,
        backoff_base=10.0,
        backoff_max=120.0,
        retry_on=[ErrorCategory.PHASE_GATE_FAILED],
        timeout_seconds=600.0,
    ),
}
```

### 3.2 重试实现

```python
class RetryHandler:
    """带指数退避的重试处理器。"""

    def __init__(self, policy: RetryPolicy):
        self.policy = policy

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Result:
        """执行函数，失败时重试。"""
        last_error = None
        for attempt in range(self.policy.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if result.success:
                    return result
                # 检查是否可重试
                if not self._is_retryable(result.error_category):
                    return result
                last_error = result
            except Exception as e:
                last_error = e

            if attempt < self.policy.max_retries:
                wait_time = min(
                    self.policy.backoff_base * (2 ** attempt),
                    self.policy.backoff_max,
                )
                # 添加随机抖动
                wait_time *= (0.5 + random.random())
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {wait_time:.1f}s"
                )
                time.sleep(wait_time)

        return self._build_final_error(last_error)
```

---

## 4. 熔断器

### 4.1 LLM Provider 熔断

```python
class CircuitBreaker:
    """熔断器：防止对持续失败的服务发起请求。"""

    def __init__(self, failure_threshold: int = 5,
                 recovery_timeout: int = 300,
                 half_open_max: int = 1):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max

        self.failure_count = 0
        self.state = "closed"  # closed → open → half_open → closed
        self.last_failure_time = 0
        self.half_open_attempts = 0

    def can_execute(self) -> bool:
        """检查是否允许执行。"""
        if self.state == "closed":
            return True

        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half_open"
                self.half_open_attempts = 0
                return True
            return False

        if self.state == "half_open":
            return self.half_open_attempts < self.half_open_max

        return False

    def record_success(self) -> None:
        """记录成功。"""
        self.failure_count = 0
        self.state = "closed"

    def record_failure(self) -> None:
        """记录失败。"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def record_half_open_attempt(self) -> None:
        """记录半开状态尝试。"""
        self.half_open_attempts += 1
```

### 4.2 Provider 熔断管理

```python
class ProviderCircuitManager:
    """管理所有 LLM Provider 的熔断器。"""

    def __init__(self, config: Config):
        self.breakers: dict[str, CircuitBreaker] = {
            provider: CircuitBreaker(
                failure_threshold=config.llm.fuse_threshold,
                recovery_timeout=config.llm.fuse_recovery_seconds,
            )
            for provider in config.llm.available_providers
        }

    def get_available_provider(self, preferred: str | None = None) -> str | None:
        """获取可用的 Provider。"""
        if preferred and self.breakers[preferred].can_execute():
            return preferred

        for name, breaker in self.breakers.items():
            if breaker.can_execute():
                return name

        return None  # 全部熔断

    def record(self, provider: str, success: bool) -> None:
        """记录 Provider 的执行结果。"""
        if success:
            self.breakers[provider].record_success()
        else:
            self.breakers[provider].record_failure()
```

---

## 5. 工作流级恢复策略

### 5.1 场景级恢复

```python
class ScenarioRecovery:
    """场景级恢复策略。"""

    def __init__(self, config: Config, log_manager: LogManager):
        self.config = config
        self.log_manager = log_manager

    def recover(self, failure: WorkflowFailure) -> RecoveryAction:
        """根据失败类型选择恢复动作。"""

        # Phase 门控连续失败
        if failure.is_gate_consecutive_failure():
            return RecoveryAction(
                type="degrade_execute",
                detail=f"Phase {failure.phase_id} gate failed 3 times, "
                       f"degrading to non-gated execution",
                action=self._degrade_phase,
            )

        # 场景超时
        if failure.is_scenario_timeout():
            return RecoveryAction(
                type="partial_report",
                detail=f"Scenario {failure.scenario_id} timed out after "
                       f"{failure.elapsed_seconds}s, generating partial report",
                action=self._generate_partial_report,
            )

        # 预算超支
        if failure.is_budget_exceeded():
            return RecoveryAction(
                type="graceful_shutdown",
                detail="Budget exceeded, performing graceful shutdown",
                action=self._graceful_shutdown,
            )

        # 上下文丢失
        if failure.is_context_lost():
            return RecoveryAction(
                type="checkpoint_restore",
                detail=f"Context lost, restoring from checkpoint "
                       f"{failure.last_checkpoint}",
                action=self._restore_checkpoint,
            )

        # LLM Provider 全部不可用
        if failure.is_all_providers_down():
            return RecoveryAction(
                type="queue_and_notify",
                detail="All LLM providers unavailable, queuing task for retry",
                action=self._queue_for_retry,
            )

        # 默认：重试
        return RecoveryAction(
            type="retry",
            detail=f"Retrying after {failure.error_category}",
            action=self._retry,
        )
```

### 5.2 降级执行

```python
class GracefulDegradation:
    """优雅降级：在资源受限情况下尽可能完成任务。"""

    def should_skip(self, action: str, reason: str) -> bool:
        """判断是否应跳过某操作。"""
        degradation_rules = {
            "qa_phase": "budget_low",       # 预算不足时跳过 QA
            "auto_deploy": "manual_required",  # 无人值守时跳过部署
            "refactoring": "time_constraint",   # 时间不足时跳过重构
        }

        return degradation_rules.get(action) == reason

    def get_degraded_actions(self, scenario: Scenario,
                              constraints: Constraints) -> list[Action]:
        """获取降级后的可执行动作列表。"""
        actions = scenario.actions.copy()

        if constraints.budget_remaining_percent < 20:
            # 预算不足 20%，只执行核心动作
            actions = [a for a in actions if a.is_core]

        if constraints.time_remaining_minutes < 30:
            # 时间不足 30 分钟，跳过非关键动作
            actions = [a for a in actions if a.is_critical]

        return actions
```

---

## 6. 错误上报与人工介入

### 6.1 上报阈值

```yaml
# configs/error_handling.yaml
error_handling:
  retry:
    tool:
      max_retries: 3
      backoff_base: 1.0
    skill:
      max_retries: 2
      backoff_base: 5.0
    phase:
      max_retries: 1
      backoff_base: 10.0

  circuit_breaker:
    failure_threshold: 5         # 连续失败 5 次触发熔断
    recovery_timeout: 300        # 5 分钟后尝试恢复

  escalation:
    notify_on:
      - "phase_gate_failed:3"    # Phase 门控失败 3 次
      - "scenario_stuck:1800"    # 场景卡住超过 30 分钟
      - "budget_exceeded"        # 预算超支
      - "all_providers_down:600" # 全部 Provider 不可用超过 10 分钟

  recovery:
    checkpoint_dir: "./checkpoints/"
    auto_checkpoint_on:
      - "phase.enter"
      - "phase.exit"
      - "error.critical"
```

### 6.2 人工介入请求

```python
@dataclass
class HumanInterventionRequest:
    request_id: str
    scenario_id: str
    error_summary: str
    suggested_actions: list[str]  # 建议的处理方式
    created_at: float
    status: str  # pending | acknowledged | resolved | dismissed
    resolution: str | None = None  # 处理结果

class HumanInterventionManager:
    """人工介入管理。"""

    def __init__(self, notification_manager, checkpoint_manager):
        self.notifications = notification_manager
        self.checkpoints = checkpoint_manager
        self.pending_requests: dict[str, HumanInterventionRequest] = {}

    def request(self, failure: WorkflowFailure) -> str:
        """发起人工介入请求。"""
        request = HumanInterventionRequest(
            request_id=uuid4().hex[:12],
            scenario_id=failure.scenario_id,
            error_summary=failure.summary,
            suggested_actions=self._suggest_actions(failure),
            created_at=time.time(),
            status="pending",
        )
        self.pending_requests[request.request_id] = request

        # 发送通知
        self.notifications.send_escalation(
            title=f"Sloth Agent needs attention: {failure.summary}",
            body=self._format_request(request),
            actions=request.suggested_actions,
        )

        return request.request_id

    def resolve(self, request_id: str, resolution: str) -> None:
        """标记介入已处理。"""
        if request_id in self.pending_requests:
            self.pending_requests[request_id].status = "resolved"
            self.pending_requests[request_id].resolution = resolution
```

---

## 7. Runbook（常见故障处理手册）

```markdown
| 故障现象 | 可能原因 | 自动处理 | 人工处理 |
|----------|---------|---------|---------|
| Phase 门控连续失败 3 次 | 测试代码有 bug、环境配置错误 | 降级执行（跳过门控） | 检查测试日志，修复后重新触发 |
| 场景超时（>30 分钟） | LLM 响应慢、工具调用过多 | 生成部分报告，停止后续 Phase | 检查进度，决定是否重新执行 |
| 预算超支 | Token 消耗过高、模型选择不当 | 优雅关闭，保存 checkpoint | 调整模型选择或预算上限 |
| 全部 Provider 不可用 | 网络问题、API 服务中断 | 队列等待，定期重试 | 检查网络，确认 API 状态 |
| 单个工具连续失败 | 工具实现有 bug、权限问题 | 切换替代工具（如有） | 检查工具实现和权限配置 |
| 文件系统错误 | 磁盘满、权限变更 | 恢复 checkpoint | 清理磁盘空间，修复权限 |
| OOM | 上下文过大、并发过高 | 降低并发数，重启 Agent | 调整 max_context_turns 配置 |
```

---

## 8. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/errors/__init__.py` | 错误处理模块入口 |
| `src/sloth_agent/errors/retry.py` | RetryHandler 重试处理器 |
| `src/sloth_agent/errors/circuit_breaker.py` | CircuitBreaker 熔断器 |
| `src/sloth_agent/errors/recovery.py` | ScenarioRecovery 场景恢复 |
| `src/sloth_agent/errors/degradation.py` | GracefulDegradation 优雅降级 |
| `src/sloth_agent/errors/escalation.py` | HumanInterventionManager 人工介入 |
| `src/sloth_agent/errors/models.py` | 错误数据模型 |
| `configs/error_handling.yaml` | 错误处理配置 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
