# Tasks: ADK 对标优化 + events + coordination 全量

> 日期: 2026-05-07
> 关联 proposal: docs/changes/adk-optimization/proposal.md
> 关联 delta: docs/changes/adk-optimization/delta.md

---

## Iter-8: Phase A + 原 Iter-8 写工具（5 天）

### Task A.1: Pydantic Schema 生成（½ 天）

**文件：** `src/sloth_agent/core/tools/decorators.py`

- 用 `pydantic.create_model()` 替代 `_py_to_json_type` 手动映射
- 自动处理 `Optional[T]`、`list[T]`、`Union[T1, T2]`
- docstring description 提取保留
- 验证：`uv run pytest tests/core/tools/test_tool_decorators.py -v`

### Task A.2: BaseToolset 抽象（½ 天）

**文件：** `src/sloth_agent/core/tools/base_toolset.py` (new)、`tests/core/tools/test_toolset.py` (new)

- `BaseToolset` abstract class：`get_tools(ctx)`、`tool_name_prefix`、`get_tools_with_prefix(ctx)`、`tool_filter`
- `ReadonlyFSToolset`：打包现有的 6 个只读工具
- 验证：`uv run pytest tests/core/tools/test_toolset.py -v`

### Task A.3: AgentConfig Pydantic 模型（½ 天）

**文件：** `src/sloth_agent/core/agents/agent_model.py` (new)、`tests/core/agents/test_agent_model.py` (new)

- `AgentConfig(BaseModel)`：name, description, instruction, model, parent, sub_agents
- `canonical_model` computed field（沿 parent 链）
- `find_agent(name)`、`clone(**overrides)`
- 验证：`uv run pytest tests/core/agents/ -v`

### Task A.4: Model 继承链 Desktop 接线（¼ 天）

**文件：** `backend/app/models.py`、`backend/app/services/agent.py`

- `AgentTemplate.parent_template_id: str | None`
- `AgentService.resolve_canonical_model(template_id) -> str`
- API response 加 `canonical_model`

### Task 8.0~8.2: 原 Iter-8 写工具 + 受限执行器 + apply API + SandboxFileViewer（3 天）

> 按原计划 `docs/plans/20260425-mvp-desktop-app-plan.md` Iter-8 执行

- 写工具（write_file/patch_file）+ tool-whitelist.yaml
- 受限网络只读工具（websearch/webfetch + NetworkGuard）
- apply-file / apply-all API + discussion_end 扩展
- 前端 SandboxFileViewer 组件

### Iter-8 验收标准

- [ ] Pydantic schema 替代手动 `_py_to_json_type`
- [ ] `BaseToolset.get_tools(ctx)` 动态发现
- [ ] `AgentConfig.canonical_model` 继承链
- [ ] 写工具 + apply API 可用
- [ ] 原有 148 测试全通过

---

## Iter-9: Phase B + 原 Iter-9 异步自主模式（4 天）

### Task B.1: HookManager + HookPoint（1 天）

**文件：** `src/sloth_agent/core/hooks/__init__.py`、`manager.py` (new)
`tests/core/hooks/test_hook_manager.py` (new)

- `HookPoint` enum（BEFORE/AFTER 各 4 个 = 8 种）
- `HookContext` dataclass、`HookResult(skip, override)` dataclass
- `HookManager.register(point, callback, priority)` / `unregister` / `run_hooks`
- 顺序执行 + 短路：遇到 non-None 返回值 → 停止
- 验证：priority 排序、短路语义、空 hook 零开销

### Task B.2: 接入 Tool 层 Hooks（¼ 天）

**文件：** `src/sloth_agent/core/brainstorm/tool_loop.py`

- 工具执行前/后/异常三个 hook 调用点
- 注册 `BEFORE_TOOL` hook return `skip=True` → 跳过执行
- 注册 `AFTER_TOOL` hook return `override=...` → 替换结果

### Task B.3: 接入 Agent 层 Hooks（½ 天）

**文件：** `backend/app/services/brainstorm.py`

- BEFORE_AGENT / AFTER_AGENT / BEFORE_MODEL / AFTER_MODEL / ON_MODEL_ERROR 五个 hook 点
- 放在 `_agent_turn` 和 `_agent_turn_with_tools` 中

### Task 9.0~9.2: 原 Iter-9 异步自主模式 + 断线恢复（2 天）

> 按原计划 Iter-9 执行

- BrainstormEngine 生成即写 DB 重构
- start-async + status API
- 前端断线恢复 + 浏览器通知

### Iter-9 验收标准

- [ ] 8 种 HookPoint 均可注册/触发
- [ ] Tool hook 可跳过/覆盖执行
- [ ] Agent hook 可在 LLM 调用前后拦截
- [ ] 异步讨论运行正常、断线恢复可用
- [ ] 原有测试全通过

---

## Iter-10: events 全量 + Phase C Agent 树 + transfer（5 天）

### Task E.1: Event 模型（CloudEvents 子集）（½ 天）

**文件：** `src/sloth_agent/core/events/__init__.py`、`models.py` (new)
`tests/core/events/test_event_models.py` (new)

- `Event(BaseModel)`：event_id(UUIDv7)、event_type(点分)、source、timestamp、data、correlation_id、priority
- 事件类型常量：`EventType` enum — run.* / phase.* / agent.* / model.* / tool.* / gate.* / budget.* / session.* / task.*
- `EventStats` dataclass：published/delivered/dropped/dead_letter 计数

### Task E.2: EventBus 核心（1 天）

**文件：** `src/sloth_agent/core/events/event_bus.py` (new)
`tests/core/events/test_event_bus.py` (new)

- `EventBus` 类：
  - `subscribe(pattern: str, handler: EventHandler)` — 通配符匹配（"phase.*", "*.completed"）
  - `publish(event: Event)` — 同/异步双队列（critical→sync，普通→async）
  - `unsubscribe(subscription_id)`
  - 持久化到 JSONL（event_store）
  - 死信队列（DLQ）：handler 失败 → `dead_letter.jsonl` + retry
  - 有界队列（maxsize=256）+ drop-oldest 背压
  - `publish` 禁止在 handler 中调用（防级联风暴）
- 验证：通配符匹配、持久化回放、DLQ、背压

### Task E.3: EventHandler 内置处理器（½ 天）

**文件：** `src/sloth_agent/core/events/handlers.py` (new)

- `EventHandler(ABC)` 基类：`handle(event)` 幂等
- `AutoReportHandler`：phase.completed → 生成报告
- `BudgetAlertHandler`：budget.warning/exceeded → 发送通知
- `HookAdapter(EventHandler)`：EventBus ↔ HookManager 桥接（Phase B hooks）

### Task E.4: WorkflowRule 声明式规则（¼ 天）

**文件：** `src/sloth_agent/core/events/workflow_rule.py` (new)

- `WorkflowRule(BaseModel)`：trigger(通配符) + action + condition + cooldown
- `BUILTIN_RULES`：预置规则列表
- `RuleEngine.evaluate(event) -> list[action]`

### Task C.1: Agent 树管理器（1 天）

**文件：** `src/sloth_agent/core/agents/tree_manager.py` (new)
`tests/core/agents/test_tree_manager.py` (new)

- `AgentTreeManager`：
  - `build_tree(configs)` 从列表构建树
  - `find_agent(root, name)` DFS 查找
  - `walk_depth_first(root)` 遍历
  - `validate_tree(root)` 循环引用/重名检测

### Task C.2: TransferToAgentTool（½ 天）

**文件：** `src/sloth_agent/core/agents/transfer_tool.py` (new)

- `TransferToAgentTool`：agent_name 是 enum（可选值=子 agent 名），防幻觉
- 执行后设 `ToolContext.actions.transfer_to_agent`
- `run_tool_loop` 检测 transfer action → 跳出循环

### Iter-10 验收标准

- [ ] EventBus pub/sub + 通配符匹配 + 持久化回放
- [ ] DLQ 正确路由、背压不丢事件
- [ ] WorkflowRule 声明式触发
- [ ] Agent 树：build/find/walk/validate
- [ ] transfer 工具：LLM 可选范围受限、transfer action 正确传递

---

## Iter-11: coordination 全量 + Phase D delta state + Runner 重构（5 天）

### Task CO.1: Coordinator + TaskDAG（1½ 天）

**文件：** `src/sloth_agent/core/coordination/__init__.py`、`coordinator.py` (new)
`tests/core/coordination/test_coordinator.py` (new)

- `TaskAssignment(BaseModel)`：task_id, role, goal, context, needs(DAG), priority, lane
- `TaskDAG`：topological_layers(), validate()
- `Coordinator`：
  - `execute(dag) -> DispatchResult`：逐层串行、层内并行
  - `_execute_layer(tasks)` → asyncio.gather
  - 依赖满足检测、致命失败中断
  - 通过 EventBus 发布 task.dispatched/completed/failed

### Task CO.2: LaneManager 并行度控制（½ 天）

**文件：** `src/sloth_agent/core/coordination/lane_manager.py` (new)

- `Lane(max_workers, queue_limit, overflow_policy)` 
- `LaneManager.create_lane(name, max_workers, ...)`
- `LaneManager.submit(lane, task)` — 同lane串行、异lane并行
- 背压：queue full 时 drop_oldest / drop_newest / reject

### Task CO.3: MessageBus Agent 间通信（½ 天）

**文件：** `src/sloth_agent/core/coordination/message_bus.py` (new)

- `AgentMessage(BaseModel)`：幂等 id、from/to、type、payload、correlation_id、ttl
- `MessageBus.send()` / `receive()` / `broadcast()` / `mark_consumed()`
- 存储后端：默认 SQLite，预留 Redis/NATS adapter
- `SharedScratchpad`（L2 共享便签）：get/set/delete/watch

### Task CO.4: Worktree 隔离 + 冲突检测（½ 天）

**文件：** `src/sloth_agent/core/coordination/worktree_manager.py` (new)

- `WorktreeManager`：create/remove/list/get_changed_files
- `ConflictDetector`：文件级 → 行级冲突检测
- 合并策略：sequential/ours/theirs/manual

### Task CO.5: 失败恢复 + 卡死检测（½ 天）

**文件：** `src/sloth_agent/core/coordination/recovery.py` (new)

- 三级恢复：L1 重试 / L2 重规划 / L3 分解
- `CheckpointManager`：save/restore/list（存 .sloth/checkpoints/）
- `StuckDetector`：N 秒无 tool call → nudge → kill → escalate

### Task C.3: Runner 重构（1 天）

**文件：** `src/sloth_agent/core/runtime/runner.py` (new)

- `Runner` 独立调度器：
  - `run_async(agent_tree, session, user_message) -> AsyncIterator[RunnerEvent]`
  - 遍历 agent 树（支持 transfer）
  - 通过 EventBus 发布生命周期事件
  - 调用 Coordinator 执行并行任务（如果 DAG 存在）
- BrainstormEngine 退化为 SequentialFlow 子类
- SSE endpoint 改为通过 Runner 调度

### Task D.1: Session delta state（½ 天）

**文件：** `src/sloth_agent/core/session/state.py` (new)

- `State` delta-tracking dict：`_base`(持久化) + `_delta`(增量)
- 命名空间约定：app:* / user:* / temp:* / agent:*
- `commit()` / `rollback()`

### Iter-11 验收标准

- [ ] Coordinator 按 DAG 拓扑执行，层内并行
- [ ] LaneManager 同 lane 串行、异 lane 并行
- [ ] MessageBus 点对点 + 广播
- [ ] WorktreeManager 创建/清理 worktree
- [ ] 失败 L1/L2/L3 三级恢复
- [ ] Runner 替代 BrainstormEngine 直接调度
- [ ] Session delta state commit/rollback
- [ ] 原有测试全通过
