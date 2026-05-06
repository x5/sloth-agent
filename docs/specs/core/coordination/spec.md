# 多 Agent 协调编排

> 归档参考: archive/initial-specs/20260416-03-multi-agent-coordination-spec.md
> 最后更新: 2026-05-06
> 状态: 规划中（v1.0 为 3-Agent 串行流水线，本模块覆盖 v2.0+ 并行协调，预计 Iter-10+）
> Scope: Core

## 1. 问题域

当前 v1.0 的 3-Agent 流水线（Builder → Reviewer → Deployer）是**固定串行**的。扩展需求包括：

1. **并行执行**：无依赖的编码任务并行跑，而非排队等待
2. **角色分工**：不同 Agent 扮演不同角色（Coder、Reviewer、Tester），按任务类型动态分配
3. **任务编排**：主调度器按 DAG 拆分子任务，收集结果并合并
4. **结果合并**：多个 Agent 的输出合入同一分支，处理冲突
5. **Agent 间通信**：Agent 能互通状态、传递结果、等待依赖

## 2. 参考设计

### 2.1 OpenClaw

OpenClaw 采用 **Hub-and-Spoke（中心辐射）** 拓扑：

- **Gateway** 作为中心 hub，所有 Agent/Channel 通过 WebSocket 连接
- **sessions_spawn** 工具：主 Agent 通过工具调用派生子 Agent，子 Agent 跑在独立 lane 上
- **Lane 模型**：每个 session 分配一条 lane，同 lane 内串行，异 lane 间并行。原则是 "默认串行，显式并行"
- **Command Queue**：确定性的排队机制（collect / steer / followup），带背压控制
- **隔离**：子 Agent 有独立 SessionKey、独立上下文，结果通过 Gateway 路由回父 Agent

**对我们有价值的模式**：
- Lane 模型比单纯的 ThreadPoolExecutor 更灵活——可以精确控制哪些任务串行、哪些并行
- sessions_spawn 工具化——Agent 自己决定什么时候派生子任务，而非由外部 scheduler 硬编码
- 背压控制（debounce、队列上限、溢出策略）对生产环境至关重要

### 2.2 Hermes Agent

Hermes（Nous Research）定义了四层 Agent 间通信模型（L0–L3）：

| 层级 | 机制 | 适用场景 |
|------|------|---------|
| **L0: 隔离** | 无共享；父 Agent 手动传递结果 | 简单委托（当前 delegate_task 状态） |
| **L1: 结果传递** | DAG 引擎自动注入上游结果到下游上下文 | 工作流 DAG |
| **L2: 共享便签** | 读/写共享 KV 存储 | 需要细粒度数据共享的复杂工作流 |
| **L3: 实时对话** | Agent 间轮次对话 | 辩论/审查模式 |

**对我们有价值的模式**：
- L0–L3 分级精细——不需要一步到位实现全部，可以逐级演进
- L1 的 DAG 结果注入特别实用——下游 Agent 自动看到上游产出，不依赖人工拼接
- L3 的实时对话模式对应我们的 Brainstorm 多 Agent 讨论

### 2.3 与 A2A 协议的关系

A2A（Google）解决的是**跨组织/跨框架**的 Agent 互操作。本模块解决的是**单系统内**的 Agent 协调。二者互补：

- 本模块的 Lane / Worktree 管理 → A2A 不涉及，完全自建
- 本模块的 MessageBus → 可预留面向 A2A 的 adapter，但不直接使用 A2A 协议
- 当需要接入外部 Agent 服务时，MessageBus 增加 A2A adapter 即可对外互通

## 3. 核心模型

### 3.1 任务 DAG

```
         ┌──────────┐
         │  Plan    │ (Planner)
         └────┬─────┘
              │
    ┌─────────┼─────────┐
    │         │         │
┌───▼──┐ ┌───▼──┐ ┌───▼──┐
│Code A│ │Code B│ │Code C│  ← 并行编码层 (Coder × 3)
└───┬──┘ └───┬──┘ └───┬──┘
    │        │        │
    └────────┼────────┘
             │
       ┌─────▼─────┐
       │  Review   │ ← 审查层 (Reviewer × 2)
       └─────┬─────┘
             │
       ┌─────▼─────┐
       │  Test     │ ← 测试层 (Tester × 1)
       └─────┬─────┘
             │
       ┌─────▼─────┐
       │  Integrate │ ← 集成层 (Integrator)
       └───────────┘
```

### 3.2 角色定义

| 角色 | 职责 | 推荐模型 | 最大并行实例 | 输出 |
|------|------|---------|------------|------|
| Planner | 任务分解、优先级排序、DAG 构建 | claude-sonnet | 1 | PLAN + 任务 DAG |
| Coder | 编写代码 + 测试 | deepseek | 3 | 代码变更 + 单元测试 |
| Reviewer | 代码审查、Spec 合规检查 | claude-sonnet | 2 | 审查报告 |
| Tester | 集成测试、QA 验证 | claude-sonnet | 2 | 测试报告 |
| Integrator | 合并分支、解决冲突 | claude-sonnet | 1 | 合并后的代码 |
| Reporter | 生成报告 | claude-haiku | 1 | 日报/周报 |

### 3.3 任务模型

```python
class TaskAssignment(BaseModel):
    task_id: str
    task_name: str
    role: str                      # "planner" | "coder" | "reviewer" | "tester" | "integrator" | "reporter"
    goal: str                      # 任务目标描述
    context: dict[str, Any]        # 上下文信息（文件路径、spec 等）
    needs: list[str] = []          # 依赖的 task_id 列表
    priority: int = 0              # 0 = 最高
    timeout_seconds: int = 1800    # 30 分钟默认
    retry_policy: RetryPolicy = RetryPolicy()
    lane: str | None = None        # 指定 lane（同 lane 串行，否则可并行）
```

## 4. 编排引擎

### 4.1 Coordinator（总调度器）

```python
class Coordinator:
    """多 Agent 协调器。

    与 v1.0 Runner 的关系：
    - v1.0: Runner 直接驱动单个 Agent 串行执行
    - v2.0: Runner 调用 Coordinator，Coordinator 管理子 Agent 并行执行
    - Coordinator 本身不替代 Runner，而是 Runner 的并行执行委托
    """

    def __init__(self, config: CoordinatorConfig):
        self.tasks: dict[str, TaskAssignment] = {}
        self.results: dict[str, TaskResult] = {}
        self.lane_manager: LaneManager
        self.message_bus: MessageBus
        self.worktree_manager: WorktreeManager

    async def execute(self, dag: TaskDAG) -> DispatchResult:
        """按 DAG 拓扑排序执行任务。"""
        # 1. 拓扑排序 → 分层
        layers = dag.topological_layers()

        # 2. 逐层执行（层间串行，层内并行）
        for layer in layers:
            ready = [t for t in layer if self._dependencies_satisfied(t)]
            results = await self._execute_layer(ready)
            self.results.update(results)

            # 检查致命失败
            if self._has_blocking_failure(results):
                return DispatchResult(status="failed", ...)

        return DispatchResult(status="success", ...)

    async def _execute_layer(self, tasks: list[TaskAssignment]) -> dict[str, TaskResult]:
        """并行执行同一层的所有任务。"""
        ...
```

### 4.2 Lane 模型（借鉴 OpenClaw）

不是所有并行任务都应该跑在独立线程里。Lane 模型提供更精细的并行度控制：

```
Lane 规则：
- 同一个 lane 内的任务严格串行（即使没有显式依赖）
- 不同 lane 的任务可以并行
- 默认分配：不同角色 → 不同 lane（Coder lane、Reviewer lane、Tester lane）
- 同角色内可用 sub-lane 进一步并行
```

```python
class LaneManager:
    """Lane 并行度管理器。

    每条 lane 有自己的并发上限、任务队列和背压策略。
    """

    def __init__(self, max_global_workers: int = 8):
        self.lanes: dict[str, Lane] = {}

    def create_lane(self, name: str, max_workers: int = 1,
                    queue_limit: int = 10,
                    overflow_policy: str = "drop_oldest") -> Lane:
        ...

    async def submit(self, lane: str, task: TaskAssignment) -> TaskResult:
        """提交任务到指定 lane，等待完成。"""
        ...
```

### 4.3 调度策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| `dag_layers` | 拓扑分层，层间串行层内并行 | 有明确依赖的任务图 |
| `role_parallel` | 按角色分组并行（Coder lane × 3, Reviewer lane × 2） | 无依赖的独立任务 |
| `convoy` | 多路并行 + 最后汇聚（借鉴 Hermes convoy 模式） | 前后端同时开发 |
| `sequential` | 全串行 | 当前 v1.0 行为，作为 fallback |

## 5. Agent 间通信（L0–L3）

### 5.1 层级定义（借鉴 Hermes）

```
L0: 隔离 — 无共享数据，父 Agent 手动传递结果
    ↓ (v2.0 实现)
L1: 结果传递 — DAG 引擎自动注入上游结果到下游 TaskAssignment.context
    ↓ (v2.1 实现)
L2: 共享便签 — 可读写的共享 KV 存储，Agent 主动读写
    ↓ (v3.0 实现)
L3: 实时对话 — Agent 间轮次对话，支持辩论/协作模式
```

### 5.2 MessageBus（L1+ 基础设施）

```python
class MessageBus:
    """Agent 间消息传递。

    设计原则：
    - 存储后端可插拔（默认 SQLite，可切换 Redis/NATS）
    - 消息幂等（基于 message_id 去重）
    - 支持点对点和广播两种模式
    - 预留 A2A adapter 接口
    """

    async def send(self, msg: AgentMessage) -> None: ...
    async def receive(self, agent_id: str, message_type: str | None = None) -> list[AgentMessage]: ...
    async def broadcast(self, msg: AgentMessage, role_filter: str | None = None) -> None: ...
    async def mark_consumed(self, message_id: str) -> None: ...


class AgentMessage(BaseModel):
    message_id: str      # 全局唯一，幂等去重
    from_agent: str
    to_agent: str        # "*" 表示广播
    message_type: str    # "task_result" | "error" | "dependency_ready" | "heartbeat" | "custom"
    payload: dict[str, Any]
    correlation_id: str | None  # 关联的 task_id，用于追踪链路
    timestamp: float
    ttl: int = 300       # 消息 TTL（秒），超时自动清理
```

### 5.3 SharedScratchpad（L2）

```python
class SharedScratchpad:
    """Agent 间共享的 KV 便签。

    用途：多个 Agent 需要读写同一数据时（如共享 todo 列表、共享发现的问题列表），
    避免通过 MessageBus 来回传数据。
    """

    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> None: ...
    async def watch(self, key_pattern: str) -> AsyncIterator[WatchEvent]: ...
```

## 6. Git Worktree 隔离

### 6.1 设计

每个并行 Agent 实例在独立 git worktree 中工作，避免文件系统冲突。

```
repo/
├── .worktrees/
│   ├── code-task-001-a1b2c3d4/   ← Coder A
│   ├── code-task-002-e5f6g7h8/   ← Coder B
│   ├── review-001-i9j0k1l2/      ← Reviewer
│   └── test-001-m3n4o5p6/        ← Tester
```

### 6.2 WorktreeManager

```python
class WorktreeManager:
    """管理 Git worktree 生命周期。

    约束：
    - 自动命名：{role}-{task_id}-{uuid8}
    - 自动清理：任务完成后按配置删除（auto_cleanup）
    - 并发安全：同一分支不会同时被两个 Agent 使用
    """

    async def create(self, task: TaskAssignment) -> Worktree: ...
    async def remove(self, worktree: Worktree) -> None: ...
    async def list_all(self) -> list[Worktree]: ...
    async def get_changed_files(self, worktree: Worktree) -> list[str]: ...
```

## 7. 结果合并与冲突处理

### 7.1 合并策略

| 策略 | 说明 | 适用场景 |
|------|------|---------|
| `sequential` | 按完成顺序逐个合并（假设无冲突） | 任务修改不相交的文件集 |
| `ours` | 以主分支为准 | 实验性改动 |
| `theirs` | 以 Agent 改动为准 | 自动修复 |
| `manual` | 暂停等待人工解决 | 冲突无法自动判断 |

### 7.2 ConflictDetector

```python
class ConflictDetector:
    """检测多个 Agent 的修改是否冲突。

    三阶段检测：
    1. 文件级：同一文件被多个 Agent 修改 → 标记
    2. 行级：同一文件的不同行 → 自动合并，同一文件相同行 → 冲突
    3. 语义级（远期）：两个 Agent 的改动语义冲突但 git 没检测到
    """

    async def detect(self, worktrees: list[Worktree]) -> list[Conflict]:
        ...
```

## 8. 失败恢复

### 8.1 三级恢复（借鉴 Hermes / CAMEL-AI）

| 层级 | 动作 | 触发器 |
|------|------|--------|
| **L1: 重试** | 同一 Agent 重跑同一任务 | 瞬时错误（网络超时、临时文件锁） |
| **L2: 重规划** | 元 Agent 基于失败原因改写任务描述 | 任务描述模糊、上下文不足 |
| **L3: 分解** | 将失败任务拆成更小的子任务 | 任务范围过大、单次执行超时 |

### 8.2 检查点

```python
class CheckpointManager:
    """持久化任务执行状态，支持断点恢复。

    每次 tool call 后自动保存检查点到 .sloth/checkpoints/{task_id}/。
    恢复时从最新检查点继续，不重跑已完成的工作。
    """

    async def save(self, task_id: str, state: TaskState) -> None: ...
    async def restore(self, task_id: str) -> TaskState | None: ...
    async def list_checkpoints(self, task_id: str) -> list[Checkpoint]: ...
```

### 8.3 卡死检测

```python
class StuckDetector:
    """监控 Agent 活动，检测卡死。

    规则：Agent 在 N 秒内无任何 tool call → 判定卡死
    动作：轻推（nudge）→ 超时杀（kill）→ 上报（escalate）
    """
```

## 9. 与现有模块的关系

```
Runner (cli/runtime)          ← CLI 运行循环
    │
    ├── [v1.0] 直接驱动 Agent (Builder → Reviewer → Deployer)
    │
    └── [v2.0] 委托给 Coordinator
                   │
                   ├── LaneManager      ← 并行度控制
                   ├── MessageBus       ← Agent 间通信 (L1+)
                   ├── WorktreeManager  ← 隔离
                   ├── ResultMerger     ← 结果合并
                   ├── ConflictDetector ← 冲突检测
                   ├── CheckpointManager ← 故障恢复
                   └── StuckDetector    ← 卡死检测

EventBus (core/events)       ← 事件总线（与 MessageBus 互补）
```

**MessageBus vs EventBus 的区别**：
- MessageBus：点对点/广播的**消息传递**，有明确的目标接收者，面向 Agent 间任务协调
- EventBus：发布/订阅的**事件通知**，发布者不关心谁订阅，面向系统模块间解耦

## 10. 演进路线

| 版本 | 交付内容 | L 层级 |
|------|---------|--------|
| v1.0（已实现） | 3-Agent 串行流水线，无并行 | — |
| v2.0 | Coordinator + DAG + LaneManager + WorktreeManager + MessageBus(L1) | L1 |
| v2.1 | SharedScratchpad + ConflictDetector | L2 |
| v3.0 | 实时对话模式（Brainstorm Engine 对接） | L3 |

## 11. 配置

```yaml
# configs/coordination.yaml
coordination:
  enabled: false
  max_global_workers: 8

  lanes:
    coder:
      max_workers: 3
      queue_limit: 10
      overflow: drop_oldest
    reviewer:
      max_workers: 2
    tester:
      max_workers: 2

  message_bus:
    backend: sqlite         # sqlite | redis | nats
    db_path: "./run/message_bus.db"
    message_ttl: 300
    dedup_window: 600

  worktrees:
    base_dir: ".worktrees"
    auto_cleanup: true

  failure_recovery:
    retry_max: 3
    retry_backoff: exponential
    checkpoint_enabled: true
    stuck_timeout_seconds: 300

  merge:
    default_strategy: sequential
    auto_resolve: false
```

## 12. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/coordination/__init__.py` | 模块入口 |
| `src/sloth_agent/coordination/coordinator.py` | Coordinator 总调度器 |
| `src/sloth_agent/coordination/dag.py` | 任务 DAG 构建与拓扑排序 |
| `src/sloth_agent/coordination/lane.py` | LaneManager 并行度控制 |
| `src/sloth_agent/coordination/roles.py` | Agent 角色定义 |
| `src/sloth_agent/coordination/message_bus.py` | MessageBus 消息总线 |
| `src/sloth_agent/coordination/scratchpad.py` | SharedScratchpad (L2) |
| `src/sloth_agent/coordination/worktree.py` | WorktreeManager |
| `src/sloth_agent/coordination/merger.py` | ResultMerger 结果合并 |
| `src/sloth_agent/coordination/conflict.py` | ConflictDetector 冲突检测 |
| `src/sloth_agent/coordination/checkpoint.py` | CheckpointManager 检查点 |
| `src/sloth_agent/coordination/stuck.py` | StuckDetector 卡死检测 |
| `src/sloth_agent/coordination/models.py` | 数据模型 |
| `configs/coordination.yaml` | 配置 |
