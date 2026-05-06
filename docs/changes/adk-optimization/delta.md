# Delta: ADK 对标优化 — Agent 管理 & 编排 & Hooks 增强

> 关联模块: tools/spec.md, llm/spec.md, coordination/spec.md, brainstorm/spec.md, events/spec.md, runtime/spec.md, session/spec.md
> 日期: 2026-05-07

---

## ADDED Requirements — tools/spec.md

### REQ-TOOL-010: BaseToolset 抽象（Phase A）

```
BaseToolset（core/tools/base_toolset.py）
- get_tools(ctx: ToolContext) -> list[ToolDef]
  动态工具发现：根据运行时上下文（project_root、agent_id、session_id）
  返回当前可用的工具列表
- tool_name_prefix: str = ""
  get_tools_with_prefix(ctx) 自动给所有工具名加前缀（命名空间隔离）
- tool_filter: Callable[[ToolDef], bool] | list[str] | None
  按条件过滤工具（白名单/自定义 predicate）
- get_auth_config() -> AuthConfig | None（预留，Iter-9+）
- process_llm_request(llm_request)（预留）

用例：
- MCPToolset：启动时连接 MCP server，动态发现工具列表
- WebSearchToolset：根据网络策略配置是否可用
- ReadonlyFSToolset：将 6 个只读工具打包为一个 toolset（已有 readonly_fs 可迁移）
```

### REQ-TOOL-011: Pydantic Schema 生成替代手动 inspect（Phase A）

```
修改 core/tools/decorators.py 的 _infer_json_schema()：

原实现：
  inspect.signature + get_type_hints → 手动 _py_to_json_type 映射

新实现：
  pydantic.create_model(func.__name__, **fields) → model_json_schema()
  
优势：
- 自动处理 Optional[T]、list[T]、Union[T1, T2] 等复杂类型
- 自动处理嵌套 Pydantic model
- 与 OpenAI function calling schema 格式天然兼容
- 移除 _py_to_json_type、_extract_param_desc 等手动解析代码

注意：
- ToolContext 参数仍排除在 schema 外（ctx/tool_context）
- docstring description 提取逻辑保留（Pydantic 不解析 docstring）
```

---

## ADDED Requirements — llm/spec.md

### REQ-LLM-020: Agent 对象模型 (Pydantic)（Phase A）

```
新增 core/agents/agent_model.py：

class AgentConfig(BaseModel):
    """Agent 运行时配置（纯数据，无 DB 耦合）"""
    model_config = ConfigDict(extra='forbid')
    
    name: str = Field(min_length=1, pattern=r'^[a-zA-Z_][a-zA-Z0-9_]*$')
    description: str = ""
    instruction: str = ""          # 系统指令（支持 {variable} 占位符）
    model: str = ""                # 空字符串 = 继承父 agent 的 model
    tools: list[str] = []          # 工具白名单（agent 级追加）
    parent_agent: Optional['AgentConfig'] = None  # 树结构
    sub_agents: list['AgentConfig'] = []          # 子 agent
    disallow_transfer_to_parent: bool = False
    disallow_transfer_to_peers: bool = False

    @computed_field
    def canonical_model(self) -> str:
        """沿 parent 链向上查找第一个有 model 的 agent"""
    
    def find_agent(self, name: str) -> Optional['AgentConfig']:
        """DFS 在树中查找 agent"""
    
    def clone(self, **overrides) -> 'AgentConfig':
        """深拷贝，支持字段覆盖"""
```

### REQ-LLM-021: Model 继承链（Phase A）

```
AgentConfig.model 为空时，沿 parent_agent 链向上查找：
  canonical_model() → self.model or parent.canonical_model or DEFAULT_MODEL

Desktop 集成：
- AgentTemplate ORM 新增 parent_template_id: str | None
- GET /api/settings/agents/{id} 返回 canonical_model
- InspirationAgent 创建时 resolve canonical_model
```

---

## ADDED Requirements — coordination/spec.md

### REQ-COORD-010: Agent 树 + transfer 工具（Phase C）

```
参考 specs/core/coordination/spec.md 的 Lane 模型 + Hermes L0-L3

Stage 1（iter-10）：Agent 树 + L1 结果传递
- AgentTreeManager：管理 agent 树（parent/children 关系）
- TransferToAgentTool：LLM 可见的 transfer 工具，
  FunctionDeclaration(name="transfer_to_agent", parameters={agent_name: enum[子agent名列表]})
- 枚举限制 agent_name 选项（防止 LLM 幻觉出不存在 agent）
- transfer 执行：暂停当前 agent，切换到目标 agent，注入切换事件
- 结果传递：切换回来时注入子 agent 的 summary

Stage 2（iter-11+）：ParallelAgent + LoopAgent
- 参考 specs/core/coordination/spec.md 的 Lane 模型实现
- ParallelAgent：asyncio.TaskGroup 并发，branch 隔离事件
- LoopAgent：循环执行直到 escalation 或 max_iterations
```

### REQ-COORD-011: BrainstormEngine 退化为编排组件之一（Phase C）

```
当前 BrainstormEngine 是多 Agent 编排的唯一实现。
Phase C 之后：
- BrainstormEngine 保留但改为 SequentialFlow 子类
- 新增 AgentTreeRunner 作为顶层调度器
- 新增 ParallelFlow、LoopFlow 作为可选编排模式
- SSE endpoint 通过 AgentTreeRunner 调度，而非直接调用 BrainstormEngine
```

---

## ADDED Requirements — events/spec.md + hooks（新建）

### REQ-EVENT-020: Agent 生命周期 Hooks（Phase B）

```
新建 core/hooks/ 模块：

class HookPoint(str, Enum):
    BEFORE_AGENT = "before_agent"       # Agent.run() 之前
    AFTER_AGENT = "after_agent"         # Agent.run() 之后
    BEFORE_MODEL = "before_model"       # LLM 调用之前
    AFTER_MODEL = "after_model"         # LLM 调用之后（可修改 response）
    ON_MODEL_ERROR = "on_model_error"   # LLM 调用异常时
    BEFORE_TOOL = "before_tool"         # 工具执行之前
    AFTER_TOOL = "after_tool"           # 工具执行之后（可修改 result）
    ON_TOOL_ERROR = "on_tool_error"     # 工具执行异常时

HookCallback = Callable[[HookContext], Optional[HookResult]]
# 返回 None = 继续下一个 hook
# 返回 HookResult(skip=True) = 跳过操作
# 返回 HookResult(override=...) = 替换结果

class HookManager:
    def register(self, point: HookPoint, callback: HookCallback, priority: int = 0)
    def unregister(self, point: HookPoint, callback: HookCallback)
    async def run_hooks(self, point: HookPoint, ctx: HookContext) -> HookResult
    # 按 priority 排序，顺序执行，遇到 return non-None 则短路

HookContext:
    agent_id, agent_name, session_id
    model_name（BEFORE/AFTER_MODEL 时）
    messages（BEFORE_MODEL 时，可修改）
    tool_name, tool_args（BEFORE_TOOL 时）
    tool_result（AFTER_TOOL 时）
    error（ON_*_ERROR 时）
```

### REQ-EVENT-021: Hooks 接入点（Phase B）

```
Phase B 在以下位置插入 hook 调用：

1. core/brainstorm/tool_loop.py 的 run_tool_loop()：
   - 工具执行前：await HookManager.run_hooks(HookPoint.BEFORE_TOOL, ctx)
   - 工具执行后：await HookManager.run_hooks(HookPoint.AFTER_TOOL, ctx)
   - 工具异常时：await HookManager.run_hooks(HookPoint.ON_TOOL_ERROR, ctx)

2. backend/app/services/brainstorm.py 的 _agent_turn()：
   - Agent 开始前：await HookManager.run_hooks(HookPoint.BEFORE_AGENT, ctx)
   - LLM 调用前：await HookManager.run_hooks(HookPoint.BEFORE_MODEL, ctx)
   - LLM 调用后：await HookManager.run_hooks(HookPoint.AFTER_MODEL, ctx)
   - Agent 结束后：await HookManager.run_hooks(HookPoint.AFTER_AGENT, ctx)

向后兼容：默认无 hook 注册时，HookManager.run_hooks() 直接返回 None，零开销。
```

---

## ADDED Requirements — runtime/spec.md

### REQ-RUNTIME-010: Runner 独立调度器（Phase C）

```
参考 specs/runtime/spec.md 运行时生命周期

新增 core/runtime/runner.py：

class Runner:
    """独立 Agent 调度器。管理 session 生命周期 + agent 树遍历"""
    
    async def run_async(
        self,
        agent_tree: AgentConfig,       # 树根
        session: Session,              # 当前会话
        user_message: str,             # 用户输入
    ) -> AsyncIterator[RunnerEvent]:   # 统一事件流
    
    职责：
    - 创建 InvocationContext
    - 遍历 agent 树（处理 transfer）
    - 管理 session state（delta apply）
    - 触发 compaction（超过 token 阈值时）
    - 发布生命周期事件（BEFORE/AFTER_AGENT, etc.）

注意：
- Runner 不负责 HTTP/SSE 传输 — 那是 Desktop adapter 的职责
- Runner 不负责 DB 持久化 — 那是 Session 的职责
```

---

## MODIFIED Requirements — session/spec.md

### REQ-SESSION-005: Session delta state（Phase D）

```
修改 session 模型，参考 specs/core/events/spec.md 的 state delta 设计：

class State:
    """delta-tracking dict。读时 merge(delta)，写时只写 delta"""
    
    _base: dict     # 已持久化的值
    _delta: dict    # 当前 invocation 的增量
    
    def get(self, key): return self._delta.get(key, self._base.get(key))
    def set(self, key, value): self._delta[key] = value
    def to_dict(self): return {**self._base, **self._delta}
    def commit(self): self._base = {**self._base, **self._delta}; self._delta = {}

命名空间约定：
- app:*     — 应用级共享
- user:*    — 用户级共享  
- temp:*    — 临时（不持久化，仅当前 invocation 有效）
- agent:*   — agent 级私有
```

---

## ADDED Requirements — events/spec.md（全量，Iter-10）

> 纳入 `specs/core/events/spec.md` 15KB 规划全量内容

### REQ-EVENT-001: Event 模型（CloudEvents 子集）

```
Event(BaseModel) — specs/core/events/spec.md §3.1
- event_id: UUIDv7
- event_type: 点分类型 "phase.completed" "tool.called" 等
- source: 事件来源模块
- data: 事件负载
- trace_id / correlation_id: 关联追踪
- priority: 0=normal, 1=high, 2=critical
```

### REQ-EVENT-002: 事件类型目录

```
EventType enum — specs/core/events/spec.md §3.2
- 运行时生命周期: run.started/completed/failed/paused/resumed
- Phase 生命周期: phase.started/completed/failed
- Agent 生命周期: agent.started/completed/failed/handoff
- 模型调用: model.request/response/fallback
- 工具调用: tool.called/completed/blocked
- 门控: gate.passed/failed
- 预算: budget.warning/exceeded
- 会话: session.created/completed
- 协调: task.dispatched/completed/failed, merge.conflict
- 通知: notification.sent, report.generated
- 健康: health.unhealthy/recovered
```

### REQ-EVENT-003: EventBus

```
EventBus — specs/core/events/spec.md §4.1
- subscribe(pattern, handler): 通配符 "phase.*" "*.completed" "*.*"
- publish(event): critical→sync_queue, 普通→async_queue
- 有界队列(256) + drop-oldest 背压
- 持久化: JSONL event_store → 支持 replay(start, end, type)
- DLQ: dead_letter.jsonl + retry_count < max_retries
- 禁止 handler 中 publish（防级联风暴）
- handler 抛异常 → DLQ，不影响其他 handler
```

### REQ-EVENT-004: EventHandler + 内置处理器

```
EventHandler(ABC) — specs/core/events/spec.md §4.2
- handle(event) 必须幂等
- AutoReportHandler: phase.completed → 生成报告
- BudgetAlertHandler: budget.warning/exceeded → 通知
- HookAdapter: EventBus ↔ HookManager 桥接

WorkflowRule — specs/core/events/spec.md §7
- trigger(通配符) + action + condition + cooldown
- BUILTIN_RULES: 预置触发规则
```

---

## ADDED Requirements — coordination/spec.md（全量，Iter-11）

> 纳入 `specs/core/coordination/spec.md` 16KB 规划全量内容

### REQ-COORD-001: 任务 DAG + 角色定义

```
TaskDAG — specs/core/coordination/spec.md §3.1
- topological_layers(): 层间串行、层内并行
- TaskAssignment: task_id, role, goal, context, needs(DAG), priority, lane

角色: Planner/Coder/Reviewer/Tester/Integrator/Reporter
- specs/core/coordination/spec.md §3.2
```

### REQ-COORD-002: Coordinator 总调度器

```
Coordinator — specs/core/coordination/spec.md §4.1
- execute(dag) → 按拓扑分层执行
- _execute_layer(tasks) → asyncio.gather 并行
- 依赖满足检测 + 致命失败中断
- 通过 EventBus 发布 task.* 事件
```

### REQ-COORD-003: LaneManager 并行度控制

```
LaneManager — specs/core/coordination/spec.md §4.2
- 同 lane 串行、异 lane 并行
- max_workers, queue_limit, overflow_policy(drop_oldest/drop_newest/reject)
- 调度策略: dag_layers / role_parallel / convoy / sequential (§4.3)
```

### REQ-COORD-004: Agent 间通信 + MessageBus

```
Hermes L0-L3 — specs/core/coordination/spec.md §5
- L1: DAG 结果注入到下游 context → Iter-11 实现
- L2: SharedScratchpad get/set/delete/watch → Iter-11 实现
- L3: 实时对话 → 现有 Brainstorm 已覆盖

MessageBus — specs/core/coordination/spec.md §5.2
- send/receive/broadcast/mark_consumed
- AgentMessage 幂等去重、TTL 自动清理
- 后端可插拔（默认 SQLite）
```

### REQ-COORD-005: Worktree 隔离 + 冲突检测

```
WorktreeManager — specs/core/coordination/spec.md §6
- create(task): 自动命名 {role}-{task_id}-{uuid8}
- remove/worktree/list_all/get_changed_files

ConflictDetector — specs/core/coordination/spec.md §7
- 文件级冲突 + 行级冲突检测
- 合并策略: sequential/ours/theirs/manual
```

### REQ-COORD-006: 失败恢复 + 卡死检测

```
三级恢复 — specs/core/coordination/spec.md §8.1
- L1 重试(瞬时错误) / L2 重规划(模糊任务) / L3 分解(超时)

CheckpointManager — specs/core/coordination/spec.md §8.2
- save/restore/list → .sloth/checkpoints/

StuckDetector — specs/core/coordination/spec.md §8.3
- N 秒无 tool call → nudge → kill → escalate
```

### REQ-COORD-007: Agent-as-Tool（Iter-11）

```
AgentTool（core/agents/agent_tool.py）
- 将子 agent 包装为 FunctionTool
- FunctionDeclaration 的 name = agent.name, description = agent.description
- 调用时：创建简易 Runner → run_async(child_agent, session, args) → 返回结果文本
- skip_summarization: bool = False（是否跳过 LLM 摘要）
- 与 transfer 的区别：transfer 移交控制权，AgentTool 拿结果回来继续
```

### REQ-LLM-022: YAML 配置加载 from_config()（Iter-11）

```
AgentConfig.from_yaml(path: str) → AgentConfig（新增在 core/agents/agent_model.py）
- 解析 YAML → 验证 Pydantic schema → 构造 AgentConfig 树
- sub_agents 支持 config_path（引用另一个 YAML）或 code（引用 Python 变量）
- tools 支持 name（ADK 内置名）、fully.qualified.path（用户定义）、name + args（带参数）
- 与现有 DB AgentTemplate 共存，不替代

用例：
- 版本控制：agent 配置和代码一起进 git
- CI 自动化：跑 eval 不需要先启动 Desktop 配 agent
- 团队共享：导出 YAML → 别人 import → 同样的 agent 行为
```

### REQ-SESSION-006: Session rewind（Iter-11）

```
Runner.rewind_async(session_id, target_invocation_id) → Session
- 计算逆向 state delta（从当前状态回退到目标 invocation 前）
- 计算逆向 artifact delta（删除目标 invocation 产生的文件）
- 用于调试、重放、"回到那个时间点"功能
- 依赖 delta state（REQ-SESSION-005）
```

---

## ADDED Requirements — eval/spec.md（跨 Iter-7~12+）

### REQ-EVAL-001: 工具能力评估（Iter-7 后补充，Iter-8）

```
Eval: Read-Only Tool Accuracy
- 测试集：20 个文件操作场景（读文件、搜索、glob 匹配等）
- 指标：工具选择正确率、参数正确率、路径安全（无越界）
- 格式：pytest 脚本，可 CI 运行

Eval: Write Tool Safety（Iter-8）
- 测试集：15 个写操作场景（写文件、打补丁、执行白名单命令）
- 指标：文件写入正确性、越界拒绝率、命令白名单拦截率
- 格式：pytest 脚本
```

### REQ-EVAL-002: 讨论质量评估（Iter-9）

```
Eval: Brainstorm Discussion Quality
- 测试集：10 个讨论场景（技术决策、方案对比、风险评估）
- 指标：讨论不跑题率、关键点覆盖率、结论一致性、token 效率
- 方法：LLM-as-judge（用大模型给讨论质量打分 1-5）
```

### REQ-EVAL-003: Agent 协作评估（Iter-10）

```
Eval: Agent Transfer & Collaboration
- 测试集：8 个多 Agent 协作场景
- 指标：transfer 正确率、子 agent 结果利用率、无循环 transfer
```

### REQ-EVAL-004: 编排效率评估（Iter-11）

```
Eval: Coordination Efficiency
- 测试集：5 个并行任务 DAG
- 指标：并行执行时间 < 串行时间 N%、冲突检测准确率、失败恢复成功率
```

### REQ-EVAL-005: eval 体系化（Iter-12+）

```
参考 ADK evaluation/ 模块（~47 文件）

- UserSimulator：模拟多轮用户交互，测试 Agent 对话流程
- LLM-as-judge：大模型评分（response_match、tool_trajectory、hallucinations）
- RubricBasedEvaluator：基于评分标准的评估
- SafetyEvaluator：安全评估
- TrajectoryEvaluator：执行轨迹评估
- 所有 evaluator 通过 EventBus 订阅评估事件
```

---

## ADDED Requirements — Iter-12+ 候选模块

### REQ-MEM-001: 长期记忆（Iter-12+）

```
参考 ADK BaseMemoryService + VertexAiMemoryBankService
关联 specs/memory/spec.md (993B)

- BaseMemoryService: add_session_to_memory / add_memory / search_memory
- 向量检索（复用现有 chromadb 依赖）
- 跨 session 召回：用户提到"上次讨论的那个 bug"→ 自动检索历史
```

### REQ-ERRORS-001: 错误处理体系接入 Desktop（Iter-12+）

```
关联 specs/errors/spec.md (1134B)
core 层已有 circuit_breaker.py + circuit_manager.py，未接入 Desktop

- 将 CircuitBreaker 接入 LLMAdapter（LLM 调用自动熔断）
- 将重试策略接入 run_tool_loop（工具执行自动重试）
- 错误码标准化（API 返回统一 error_code）
```

### REQ-COST-001: 费用追踪接入 Desktop（Iter-12+）

```
关联 specs/cost/spec.md (961B)
core 层已有 budget_router.py + cost/tracker.py，未接入 Desktop

- BudgetAwareRouter 接入 LLMAdapter（自动模型降级）
- Dashboard 展示按 agent/inspiration 的费用拆分
- 预算预警（通过 EventBus 发布 budget.warning/exceeded 事件）
```

### REQ-OBS-001: 可观测性（Iter-12+）

```
关联 specs/observability/spec.md (370B)

- OpenTelemetry tracing：每个 Agent.run() 生成 span
- Tool 调用、LLM 调用自动打点
- metrics：token 消耗、工具调用次数、讨论轮次
- 通过 EventBus 发布 health.unhealthy / health.recovered 事件
```

### REQ-SANDBOX-001: 容器沙箱（Iter-12+）

```
关联 specs/sandbox/spec.md (526B)

- ContainerCodeExecutor：Docker 容器执行代码（参考 ADK ContainerCodeExecutor）
- GkeCodeExecutor：K8s Pod 执行代码
- 比 Iter-8 文件级隔离更强的安全保证
```
