# 变更提案: ADK 对标优化 — Agent 管理 & 编排 & Hooks 增强

> 日期: 2026-05-07
> 参考: Google ADK Python (`git@github.com:google/adk-python.git`)
> 影响模块: coordination, events, tools, llm, brainstorm, runtime, session

## 动机

通过分析 Google ADK Python 的 Agent 管理架构，对比 Sloth 当前实现，发现以下差距：

| 维度 | ADK | Sloth 当前 | 差距 |
|------|-----|-----------|------|
| Agent 定义 | Pydantic BaseModel + YAML 双轨，model 继承链，clone() | dataclass + ORM 分离 | 缺少对象模型、继承 |
| Tool 系统 | FunctionTool + BaseToolset（动态发现/MCP），Pydantic schema | @tool + ToolPool（静态注册），手动 inspect | 缺少 Toolset 抽象 |
| Multi-Agent 编排 | 树形层级 + transfer 工具 + Sequential/Parallel/Loop 四种模式 | 平铺 Team + 固定顺序发言 | 无 agent 树、无 transfer |
| 状态管理 | State delta + rewind + branch 隔离 + compaction | DB Message 表 + ContextWindowManager | 无 delta、无 rewind |
| Hooks | 6 种 callback（before/after agent/model/tool），可组合列表 | 0 | 完全空白 |
| Pipeline | Runner + 12+ 可插拔 processor | BrainstormEngine 硬编码 | 无 processor 管道 |

**目标：** 将以上差距转化为可执行的 spec 增量，按影响/成本排入后续 Iter。

## 对齐的 spec 模块

```
ADK 维度                    →  Sloth spec 模块

1. Agent 定义（Pydantic + 继承） → specs/llm/spec.md
2. Tool 系统（Toolset 抽象）    → specs/tools/spec.md
3. 编排模式（树形 + transfer）   → specs/coordination/spec.md + specs/brainstorm/spec.md
4. 状态管理（delta + rewind）    → specs/session/spec.md + specs/events/spec.md
5. Hooks 系统（6 种 callback）   → specs/events/spec.md（新增章节）
6. Pipeline（Runner + Processor）→ specs/runtime/spec.md + specs/daemon/spec.md
```

## 分阶段优先级 & Iter 分配

| 阶段 | 迭代 | 内容 | 成本 | 收益 |
|------|------|------|------|------|
| A | **Iter-8** | Toolset 抽象 + Pydantic schema + AgentConfig + model 继承链 + 原 Iter-8 写工具 | 中 | 高 |
| B | **Iter-9** | Hooks 系统（8 种 HookPoint）+ 原 Iter-9 异步自主模式 | 中 | 高 |
| C | **Iter-10** | Agent 树 + transfer 工具 + **events 全量**（EventBus/CloudEvents/持久化/DLQ） | 大 | 高 |
| D | **Iter-11** | **coordination 全量**（Coordinator/LaneManager/DAG/MessageBus）+ delta state + rewind | 大 | 高 |

**Iter-10 vs Iter-11 的依赖关系：**
- `events` (EventBus) 是纯基础设施，不依赖任何模块 → Iter-10
- `coordination` (Coordinator) 需要 EventBus 做 task 事件分发 → 必须在 events 之后 → Iter-11
- Phase C 的 Agent 树 + transfer 工具不依赖 EventBus → 可以和 events 一起放 Iter-10
- Phase D 的 delta state 依赖 events 的持久化机制 → Iter-11

## 决策

| 问题 | 决策 |
|------|------|
| 是否一步到位做到 ADK 级别 | 否。分 A→B→C→D 四个阶段，每个阶段练核心能力 |
| Pydantic schema 是否替代手动 inspect | 是。`core/tools/` 的 `_infer_json_schema` 替换为 Pydantic `create_model` + `model_json_schema()` |
| Agent 层级是否替代平铺 Team | 渐进迁移。先加 `parent_agent` 字段 + model 继承链，再引入 transfer 工具，BrainstormEngine 逐步退化为编排组件之一 |
| Hooks 是否单独建模块 | 是。`core/hooks/` 独立实现，不侵入现有代码。先在 `run_tool_loop` 和 `BrainstormEngine` 中插入 hook 调用点 |
| EventBus + Coordination 谁先做 | EventBus 是基建先做（Iter-10），Coordinator 依赖 EventBus 后做（Iter-11） |
| events spec 15KB 全量是否全做 | 是。Event模型 + EventBus + EventHandler + 可靠投递 + WorkflowRule 全量纳入 Iter-10 |
| coordination spec 16KB 全量是否全做 | 是。Coordinator + LaneManager + MessageBus + DAG + Worktree + StuckDetector 全量纳入 Iter-11 |

## 范围外（本次不做）

- A2A 协议兼容
- YAML 配置加载（`from_config`）
- Session rewind
- Agent-as-Tool（用子 agent 当工具调用）
