# Sloth Agent 轻量级架构设计 v2（已归档）

> 版本: archived
> 日期: 2026-04-16
> 状态: 已合并归档
> 参考: OpenClaw, Hermes Agent, Claude Code, Codex

> 归档说明：本文件中的运行时内核设计已合并到 [docs/specs/00000000-architecture-overview.md](c:/Users/TUF/Workspace/agent-evolve/docs/specs/00000000-architecture-overview.md)。自本次合并起，本文件不再是规范真相源，只保留为历史讨论与设计演进记录。

> 当前应优先阅读：
> 1. [docs/specs/00000000-architecture-overview.md](c:/Users/TUF/Workspace/agent-evolve/docs/specs/00000000-architecture-overview.md) — 唯一 canonical architecture spec
> 2. [docs/specs/20260416-phase-role-architecture-spec.md](c:/Users/TUF/Workspace/agent-evolve/docs/specs/20260416-phase-role-architecture-spec.md) — phase/ownership 编排细节
> 3. [docs/specs/20260416-tools-invocation-spec.md](c:/Users/TUF/Workspace/agent-evolve/docs/specs/20260416-tools-invocation-spec.md) — tool runtime 细节

---

## 1. 核心洞察

### 1.1 最佳实践共性

分析 Claude Code、OpenClaw、Hermes Agent 的共性：

```
┌─────────────────────────────┐
│     Orchestrator Loop       │  ← 核心：一个循环
│                             │
│   observe → think → act     │  ← 观察、思考、行动
│   observe → think → act     │
│   ...                       │
│                             │
│   Tools Layer               │  ← 工具抽象层
│   Skills Layer              │  ← 技能指令层
│   Memory Layer              │  ← 持久记忆层
└─────────────────────────────┘
```

**不是** 8 个专用 Agent，**不是** 8 个固定 Phase，**不是** 3 种存储引擎。

**是一个 Agent + 可组合工具 + 可插拔技能 + 渐进式记忆。**

### 1.2 为什么 Phase-Role 抽象过早

| 参考框架 | Agent 数量 | Phase 概念 | 如何组织流程 |
|----------|-----------|-----------|-------------|
| Claude Code | 1 | 无 | 用户指令 + 工具组合 |
| OpenClaw | 1 | 无 | 技能组合链 |
| Hermes Agent | 1 + 子代理 | 无 | 技能积累 + 经验学习 |
| **我们 v1** | **8** | **8** | 固定场景编排 |

Phase 的本质是**技能的有序调用**。不需要专用 Agent 角色来实现。同一个 Agent 在需求分析阶段用 brainstorming 技能，在编码阶段用 TDD 技能，在审查阶段用 review 技能——靠的是**注入不同的系统提示词和技能上下文**，而不是创建不同的 Agent 实例。

### 1.3 v2 架构原则

1. **一个 Runner 内核**：所有执行都由统一 runtime kernel 驱动，避免控制流分散在 Agent / Executor / Reflector / Reporter 中
2. **少量 Agent，所有权明确**：是否拆 agent 取决于 ownership contract，而不是先验地按 phase 数量拆分
2. **工具优先**：LLM 通过工具层执行，不直接写文件/跑命令
3. **技能即指令**：SKILL.md 就是 prompt 模板，运行时注入
4. **渐进式记忆**：从 FS 开始，需要时加 SQLite，再需要时加向量
5. **场景即工作流**：场景定义 = 技能调用序列 + 门控条件

---

## 2. 架构总览

```
┌────────────────────────────────────────────────────────────────┐
│                      CLI Gateway                                │
│                   (typer: run/chat/daemon)                       │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│            Product Orchestrator (产品层入口 / 模式调度)            │
└──────────────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────────┐
│                   Runner (唯一运行时内核)                        │
│                                                                  │
│  while run_not_finished:                                         │
│    1. prepare()  — 解析当前 active agent / phase / context        │
│    2. think()    — 调模型，得到结构化 next step                    │
│    3. resolve()  — final / tool / handoff / retry / interrupt     │
│    4. persist()  — 写回 RunState / session / memory               │
│    5. observe()  — hooks / tracing / gate / reflection            │
└────────────┬──────────────┬──────────────┬──────────────────────┘
             │              │              │
             ▼              ▼              ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────────┐
│ LLM Router  │  │ Tool         │  │ Skill            │
│             │  │ Orchestrator │  │ Injector         │
│ 多模型路由   │  │              │  │                  │
│ 自动降级     │  │ 意图→风险→   │  │ 匹配技能          │
│ 流式响应     │  │ 执行→结果    │  │ 注入 prompt       │
└─────────────┘  └──────────────┘  └──────────────────┘
                          │
                          ▼
┌────────────────────────────────────────────────────────────────┐
│                    Persistence Layer                            │
│                                                                  │
│  File System (主)   SQLite (索引，可选)   ChromaDB (向量，可选)  │
└────────────────────────────────────────────────────────────────┘
```

### 2.1 Runtime Kernel：系统真正的控制平面

本架构的关键不是“有几个 agent”，而是“谁驱动执行循环”。

`Agent`、`Skill`、`Tool` 都只是声明式能力；真正负责推进工作的是 `Runner`。这与 OpenAI Agents SDK 的核心思路一致：

- `Agent` 定义“这个 specialist 有什么能力和约束”
- `Runner` 负责“当前轮该怎么跑、什么时候停、什么时候恢复”
- `RunState` 负责“这一轮执行到哪了、下一轮从哪接”

因此，Sloth 的产品层 `Orchestrator` 不应再直接承担细粒度执行职责，而应只负责：

- 选择运行模式（autonomous / chat / daemon）
- 创建或恢复 `RunState`
- 调用 `Runner.run(...)`
- 在 run 结束后决定是否切换到新的高层场景

细粒度控制流统一收敛到 `Runner`，这样 gate fail、tool approval、phase handoff、resume、trace 才能共用一套语义。

---

## 3. 目录结构

```
src/sloth_agent/
├── __main__.py                  # 入口（typer app，已有）
│
├── cli/                         # CLI 层（已有 + 扩展）
│   ├── app.py                   # CLI 子命令
│   ├── chat.py                  # REPL 交互
│   ├── context.py               # 对话上下文
│   └── install.py               # 安装引导（spec 已定义）
│
├── core/                        # 核心层（重构）
│   ├── __init__.py
│   ├── config.py                # 配置模型（已有）
│   ├── orchestrator.py          # ★★★ 核心循环（新增，替代 agent.py）
│   ├── agent.py                 # 统一 Agent（简化，保留）
│   └── state.py                 # 运行状态（已有）
│
├── tools/                       # 工具层（重构 + 扩展）
│   ├── __init__.py
│   ├── registry.py              # 工具注册（从 core/tools/ 迁移）
│   ├── orchestrator.py          # 工具调度链（spec 已定义）
│   ├── intent_resolver.py       # 意图解析
│   ├── risk_gate.py             # 风险门控
│   ├── executor.py              # 执行器（增强）
│   └── builtin/                 # 内置工具
│       ├── file_ops.py          # 读写编辑
│       ├── shell.py             # Bash 执行
│       ├── git_ops.py           # Git 操作
│       └── search.py            # 文件搜索
│
├── skills/                      # 技能层（已有 + 扩展）
│   ├── __init__.py
│   ├── loader.py                # SKILL.md 加载
│   ├── router.py                # 技能路由/匹配
│   ├── injector.py              # 技能 prompt 注入
│   └── evolution.py             # 技能自进化
│
├── memory/                      # 记忆层（已有 + 扩展）
│   ├── __init__.py
│   ├── store.py                 # FS 存储（已有）
│   ├── session.py               # Session 管理（spec 已定义）
│   ├── summarizer.py            # 上下文摘要
│   └── index.py                 # SQLite 索引（可选）
│
├── providers/                   # 外部服务（已有）
│   ├── __init__.py
│   └── llm_providers.py         # LLM 路由（已有）
│
├── workflow/                    # 工作流层（从 phase 简化）
│   ├── __init__.py
│   ├── scenario.py              # 场景定义
│   ├── pipeline.py              # 技能调用管道
│   └── gates.py                 # 门控验证
│
├── daemon/                      # 常驻进程（spec 已定义）
│   ├── __init__.py
│   ├── health.py                # 健康检查
│   └── watchdog.py              # 看门狗（已有，增强）
│
└── security/                    # 安全层（spec 已定义）
    ├── __init__.py
    ├── path_validator.py        # 路径校验
    ├── sandbox.py               # 沙箱
    └── auditor.py               # 审计日志
```

---

## 4. 核心循环（Runner + Orchestrator）

### 4.1 Product Orchestrator 只负责模式调度

```python
class Orchestrator:
    """Sloth Agent 产品层入口。

    只负责模式选择、RunState 创建/恢复、与 Runner 对接。
    """

    def __init__(self, config: Config):
        self.config = config
        self.runner = Runner(config)
        self.memory = MemoryStore(config)
        self.state_store = RunStateStore(config)

    def run(self, mode: str = "autonomous") -> None:
        """模式入口。"""
        if mode == "autonomous":
            self._autonomous_loop()
        else:
            self._chat_loop()

    def _autonomous_loop(self) -> None:
        state = self.state_store.load_or_create(mode="autonomous")
        result = self.runner.run(state)
        self.state_store.save(result.state)

    def _chat_loop(self) -> None:
        state = self.state_store.load_or_create(mode="chat")
        result = self.runner.run(state)
        self.state_store.save(result.state)
        pass
```

### 4.2 Runner 是唯一执行循环

```python
class Runner:
    """统一运行时内核。

    顶层只有一个 run loop。phase、agent、skill、tool 都在这一个 loop 里流转。
    """

    def __init__(self, config: Config):
        self.config = config
        self.tool_orchestrator = ToolOrchestrator(config)
        self.skill_injector = SkillInjector(config)
        self.hooks = HookManager(config)
        self.tracer = TraceRecorder(config)

    def run(self, state: RunState) -> RunResult:
        while not state.is_finished:
            prepared = self.prepare_turn(state)
            next_step = self.call_model(prepared)
            self.resolve_next_step(state, next_step)
        return RunResult.from_state(state)

    def resolve_next_step(self, state: RunState, next_step: NextStep) -> None:
        match next_step.type:
            case "final_output":
                state.finish(next_step.output)
            case "tool_call":
                self.tool_orchestrator.execute(state, next_step.request)
            case "phase_handoff":
                state.transfer_ownership(next_phase=next_step.phase_id, next_agent=next_step.agent_id)
            case "retry_same":
                state.schedule_retry(strategy="same")
            case "retry_different":
                state.schedule_retry(strategy="different")
            case "replan":
                state.schedule_replan(next_step.reason)
            case "interruption":
                state.pause(next_step.interruption)
            case "abort":
                state.abort(next_step.reason)
```

### 4.3 NextStep：所有控制流的统一协议

```python
class NextStep(BaseModel):
    type: Literal[
        "final_output",
        "tool_call",
        "phase_handoff",
        "retry_same",
        "retry_different",
        "replan",
        "interruption",
        "abort",
    ]
    output: str | None = None
    request: ToolRequest | None = None
    phase_id: str | None = None
    agent_id: str | None = None
    reason: str | None = None
    interruption: Interruption | None = None
```

将 reflection 的 action 与 `NextStep` 映射后，运行时不再需要把 gate failure 当作普通异常硬编码处理，而是作为状态机的合法分支处理。

### 4.4 RunState：唯一状态真相源

```python
@dataclass
class RunState:
    run_id: str
    mode: Literal["autonomous", "chat", "daemon"]
    scenario_id: str | None
    current_phase: str | None
    current_agent: str
    current_task_id: str | None
    history: list[MessageItem]
    tool_history: list[ToolExecutionRecord]
    gate_results: list[GateResult]
    reflections: list[Reflection]
    pending_interruptions: list[Interruption]
    retries: dict[str, int]
    continuation: ContinuationState | None
    persisted_memory_refs: list[str]
    final_output: str | None = None
    is_finished: bool = False
```

`RunState` 是系统的真相源，优先级高于任何 provider-specific continuation ID。恢复 run 时，应优先恢复 `RunState`，而不是依赖某个模型厂商的 conversation token。

### 4.4.1 Context Boundary：模型上下文、运行时上下文、持久化状态必须分层

```python
class ModelVisibleContext(BaseModel):
    history: list[MessageItem]
    retrieved_memory: list[str]
    current_task: str | None
    handoff_payload: dict | None

@dataclass
class RuntimeOnlyContext:
    config: Config
    tool_registry: ToolRegistry
    skill_registry: SkillRegistry
    logger: Logger
    budget_tracker: BudgetTracker
    workspace_handle: WorkspaceHandle
    secrets: SecretStore

@dataclass
class PersistedRunState:
    run_state: RunState
    snapshots: list[str]
    session_refs: list[str]
```

边界规则：

- `ModelVisibleContext` 才能发给模型
- `RuntimeOnlyContext` 只给代码与工具层使用，不直接进入 prompt
- `PersistedRunState` 用于恢复、审计、回放，不等价于对话历史

特别地，以下信息默认禁止直接进入模型上下文：

- secret / credential
- logger / tracing handle
- registry 对象本身
- workspace 文件句柄
- budget / permission controller 的内部状态

### 4.5 Gate failure / approval / resume 都是同一个运行时语义

```python
def handle_gate_failure(state: RunState, gate: GateResult) -> None:
    reflection = reflect(state, gate)
    state.reflections.append(reflection)
    state.gate_results.append(gate)
    state.apply(reflection.to_next_step())

def resume(state: RunState, decision: ApprovalDecision) -> RunResult:
    state.resolve_interruption(decision)
    return runner.run(state)
```

这条原则很重要：

- gate fail 不是“新任务”，而是当前 run 的未完成分支
- human approval 不是“新对话”，而是当前 run 的暂停点
- resume 时沿用原 `RunState`，不重新拼装历史

### 4.6 生命周期 Hooks 与 Tracing 是运行时的一部分

```python
class HookManager:
    def on_run_start(self, state: RunState): ...
    def on_run_end(self, state: RunState): ...
    def on_phase_start(self, state: RunState): ...
    def on_phase_end(self, state: RunState): ...
    def on_model_start(self, state: RunState): ...
    def on_model_end(self, state: RunState, response: ModelResponse): ...
    def on_tool_start(self, state: RunState, request: ToolRequest): ...
    def on_tool_end(self, state: RunState, result: ToolResult): ...
    def on_handoff(self, state: RunState, from_owner: str, to_owner: str): ...
    def on_gate_failed(self, state: RunState, gate: GateResult): ...
    def on_reflection(self, state: RunState, reflection: Reflection): ...
    def on_resume(self, state: RunState): ...
```

tracing 的最小粒度应覆盖：

- run
- turn
- model call
- tool call
- handoff
- gate failure
- interruption / resume

这样 observability 才不需要侵入业务逻辑。

### 4.7 Continuation 抽象

```python
class ContinuationState(BaseModel):
    session_id: str | None = None
    snapshot_id: str | None = None
    provider_name: str | None = None
    provider_token: str | None = None
    daemon_thread_id: str | None = None
```

支持的 continuation 来源：

- local session
- persisted run snapshot
- provider continuation token
- daemon-owned conversation thread

其中 provider token 只是优化层，不能成为系统真相源。

**关键设计：Product Orchestrator 是入口，Runner 才是唯一的执行循环。**

自主模式和对话模式的区别仅在于：
- 自主模式：`Runner` 默认从任务驱动的 `RunState` 启动
- 对话模式：`Runner` 默认从对话驱动的 `RunState` 启动

---

## 5. 与 v1 的映射关系

| v1 概念 | v2 对应 | 变化 |
|---------|---------|------|
| 8 个 Agent 角色 | 少量 Agent + ownership contract | 简化 |
| 8 个 Phase | 技能调用序列（workflow/pipeline） | 简化 |
| PhaseRegistry | Scenario + Pipeline | 合并 |
| SkillRegistry | SkillLoader + Router | 拆分 |
| ToolRegistry | ToolOrchestrator（4 层链） | 增强 |
| MemoryStore（3 层） | MemoryStore（FS 主，其他可选） | 简化 |
| AgentEvolve.run() | Product Orchestrator + Runner.run() | 替换 |
| ChatSession | Orchestrator._chat_loop() | 保留 |
| Watchdog | Daemon + Watchdog | 增强 |

---

## 6. 需要保留的 v1 设计

以下 v1 设计是正确的，应保留：

| 设计 | 原因 |
|------|------|
| SKILL.md 格式 | 与 Claude Code 生态兼容 |
| 文件系统为主存储 | 可回溯、可审计、可手动编辑 |
| jsonl 对话格式 | 流式写入、不丢失 |
| 多 LLM Provider + fallback | 中国模型生态必要 |
| TDD 门控 | 质量保证底线 |
| 日夜时间窗口 | 黑灯工厂核心需求 |
| 技能进化触发条件 | 自进化能力基础 |

---

## 7. 需要合并/调整的 v1 设计

| 设计 | 问题 | 调整方案 |
|------|------|---------|
| 8 个专用 Agent | 过度设计，拆分标准不清 | 缩减为少量 agent，并用 ownership contract 决定何时 handoff |
| Phase 作为独立实体 | Phase 本质是 ownership + contract 边界，而不是任意摘要边界 | Phase 保留为业务编排概念，但执行上统一进入 Runner |
| ScenarioValidator 的 input/output schema 匹配 | 过于严格，LLM 输出不固定 | 改为 output 契约检查（是否存在必需产出） |
| Memory 3 层同时实现 | 起步太重 | 先 FS，需要时加 SQLite，再需要时加向量 |
| 每个 Phase 独立 LLM 切换 | 切换开销大，上下文丢失 | 默认复用同一 run，必要时仅切换 active owner 或 model policy |
| Gate 定义为 Python lambda | 不可配置 | Gate 改为 YAML 可配置 |

---

## 8. 需要新增的组件

| 组件 | 优先级 | 说明 |
|------|--------|------|
| Orchestrator 核心循环 | P0 | 统一入口，替代 AgentEvolve |
| Runner + RunState + NextStep | P0 | 统一执行内核、状态机、恢复协议 |
| ToolOrchestrator 4 层链 | P0 | IntentResolver → RiskGate → Executor → Formatter |
| SkillInjector | P0 | 技能 prompt 注入机制 |
| Pipeline（替代 Phase） | P1 | 技能调用序列 + 门控 |
| Daemon 守护进程 | P1 | 常驻运行 + 健康检查 |
| Security 沙箱 | P1 | 路径校验 + 命令黑名单 |
| Memory Session 管理 | P2 | Session 生命周期（spec 已有） |
| 技能自进化 | P2 | 错误驱动的技能改进 |
| Hook / Trace Recorder | P1 | 统一生命周期观察面 |
| Continuation 抽象 | P1 | 本地快照 / provider token / daemon thread 统一接口 |

---

## 9. 实施路径

### Phase 1: 核心替换（2-3 天）

1. 创建 `Runner`、`RunState`、`NextStep`，收敛执行循环
2. 创建 `Product Orchestrator`，仅负责模式入口和 state 创建/恢复
3. 创建 `ToolOrchestrator`，并挂接到 `Runner.resolve_next_step()`
4. 创建 `SkillInjector`，实现 SKILL.md 加载和注入
5. 保留 `ChatSession` 作为对话入口
6. 将 `AgentEvolve.run()` 标记为 deprecated

### Phase 2: 工作流重构（2-3 天）

1. 将 Phase 定义迁移为 Pipeline 定义
2. 实现 Pipeline 执行器（技能序列 + 门控）
3. 保留 8 个场景定义，但用 Pipeline 代替 Phase
4. 为 phase transition 明确定义 handoff contract
5. 为 skill 调用明确 as-tool contract

### Phase 3: 迁移现有组件（1-2 天）

| 现有组件 | 新架构归位 | 迁移方式 |
|---------|-----------|---------|
| `src/sloth_agent/core/agent.py` | Product Orchestrator 入口层 | 保留 CLI / 日夜模式入口，移除细粒度执行职责 |
| `src/sloth_agent/core/executor.py` | `Runner` + tool execution adapter | `load_approved_tasks()` 留在产品层；`execute_tasks()` 拆到 runtime + workflow |
| `src/sloth_agent/core/reflector.py` | `Runner` 内的 reflection / next-step resolver | 从“任务后置步骤”改为“gate fail 分支处理器” |
| `src/sloth_agent/core/reporter.py` | Hook / Trace / Report projection | 由运行时事件流生成报告，而不是单独扫结果 |
| `src/sloth_agent/core/state.py` | `RunState` / projection models | 区分真相源状态与展示层上下文 |

迁移原则：

1. `agent.py` 不再直接驱动 task loop
2. `executor.py` 不再拥有自己的局部状态机
3. reflection / reporting / approval 都围绕 `RunState` 聚合
4. v1.0 的 Builder → Reviewer → Deployer 业务目标保留，但底层执行内核统一
4. Gate 改为 YAML 可配置

### Phase 3: 常驻 + 安全（2-3 天）

1. 实现 Daemon 守护进程
2. 实现健康检查
3. 实现 Security 沙箱
4. 实现安装引导

### Phase 4: 记忆 + 进化（1-2 天）

1. 完善 Memory Session 管理
2. 实现技能自进化
3. 可选：SQLite 索引层

---

## 10. 风险与权衡

| 风险 | 缓解 |
|------|------|
| 从 Phase 迁移到 Pipeline 需要重写场景定义 | 场景定义是 YAML 数据，迁移成本低 |
| Orchestrator 统一入口后，自主/对话模式耦合 | 通过 mode 参数分离，代码结构清晰 |
| ToolOrchestrator 4 层链增加延迟 | 意图解析可缓存，风险门控可跳过（低风险工具） |
| 1 个 Agent vs 8 个 Agent 的能力差异 | 通过 prompt 注入 + 技能激活实现同等行为，参考 Claude Code |

---

## 11. 与参考框架的对齐

| 特性 | OpenClaw | Hermes Agent | Claude Code | **我们 v2** |
|------|----------|-------------|-------------|-------------|
| 单 Agent 核心循环 | ✅ | ✅ | ✅ | ✅ |
| 技能/工具抽象层 | ✅ Skills | ✅ Skills | ✅ Tools | ✅ Tools + Skills |
| 持久记忆 | ✅ | ✅ 自积累 | Session | ✅ FS + Session |
| 多模型支持 | ✅ | ✅ | ❌ | ✅ |
| 安全沙箱 | ✅ Risk | ✅ | Risk levels | ✅ 5 层安全 |
| 自进化能力 | ❌ | ✅ | 部分 | ✅ 技能进化 |
| 守护进程 | ✅ Gateway | ✅ Persistent | ❌ | ✅ Daemon |
| 可观测性 | ✅ | ✅ | ❌ | ✅ 指标收集 |
| 工作流编排 | ✅ Multi-agent | ❌ | ❌ | ✅ Pipeline |

**我们的差异化优势**：多模型支持 + 技能自进化 + 工作流编排 + 中国模型生态。

---

*文档版本: v2.0.0-draft*
*创建日期: 2026-04-16*
