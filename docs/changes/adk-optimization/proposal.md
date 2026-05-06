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
| A | **Iter-8** | Toolset 抽象 + Pydantic schema + AgentConfig + model 继承链 + 原 Iter-8 写工具 + **eval: 读/写工具能力评估** | 中 | 高 |
| B | **Iter-9** | Hooks 系统（8 种 HookPoint）+ 原 Iter-9 异步自主模式 + **eval: 自主讨论质量评估** | 中 | 高 |
| C | **Iter-10** | Agent 树 + transfer 工具 + Agent-as-Tool + **events 全量**（EventBus/CloudEvents/持久化/DLQ） + **eval: Agent 协作评估** | 大 | 高 |
| D | **Iter-11** | **coordination 全量**（Coordinator/LaneManager/DAG/MessageBus）+ delta state + rewind + YAML config + **eval: 编排效率评估** | 大 | 高 |
| E | **Iter-12+** | eval 体系化 + memory 长期记忆 + errors 接入 + cost 接入 + observability + sandbox 容器 + plugin 系统 + pipeline processors + A2A adapter | 大 | 中 |

**Iter-10 vs Iter-11 的依赖关系：**
- `events` (EventBus) 是纯基础设施 → Iter-10
- `coordination` (Coordinator) 需要 EventBus → 必须在 events 之后 → Iter-11
- Phase C 的 Agent 树 + transfer 不依赖 EventBus → 可以和 events 一起放 Iter-10
- Agent-as-Tool 依赖 Agent 树 + transfer（Iter-10） → Iter-11
- Phase D 的 delta state + rewind 依赖 events 持久化 → Iter-11
- YAML config 依赖 AgentConfig（Iter-8）+ Agent 树 → Iter-11

**Eval 就近评估原则：**
- Iter-7（已完成）：Agent 读文件/搜索能力 → eval 脚本验证 read/grep/glob 工具调用正确性
- Iter-8：Agent 写文件/执行命令能力 → eval 验证写工具不会越界、不会覆盖已有文件
- Iter-9：Agent 自主讨论和总结能力 → eval 验证多轮讨论不跑题、总结覆盖关键点
- Iter-10：Agent 协作能力 → eval 验证 transfer 正确性、多 Agent 通信可靠性
- Iter-11：编排效率 → eval 验证并行执行时间 < 串行时间、冲突检测准确率
- Iter-12+：eval 体系化（UserSimulator + LLM-as-judge + rubric evaluator）

**Iter-12+ 候选池（按收益排序，全来自 ADK 对标中发现的差距）：**

| # | 模块 | Sloth spec | 内容 | 依赖 |
|---|------|-----------|------|------|
| 1 | `eval/` 体系化 | 5971B | UserSimulator、LLM-as-judge、rubric evaluator、trajectory evaluator | Iter-11 eval 基础 |
| 2 | `memory/` 长期记忆 | 993B | BaseMemoryService、向量检索、跨 session 召回、memory bank | 无强依赖 |
| 3 | `errors/` 错误处理 | 1134B | 重试策略/熔断/降级体系化接入 Desktop（core 层已有 circuit_breaker.py） | hooks (Iter-9) |
| 4 | `cost/` 费用追踪 | 961B | BudgetAwareRouter 接入 Desktop、费用预测、按 agent 分账（core 层已有 budget_router.py） | 无强依赖 |
| 5 | `observability/` | 370B | OpenTelemetry tracing/metrics/logging、调用链追踪 | EventBus (Iter-10) |
| 6 | `sandbox/` 容器 | 526B | ContainerCodeExecutor、GkeCodeExecutor（ADK 的沙箱执行器） | 写工具 (Iter-8) |
| 7 | `skills/` 插件系统 | 1161B | PluginManager + 第三方插件加载、before/after hook at runner level | hooks (Iter-9) |
| 8 | `runtime/` processor 管道 | 2430B | 12+ 可组合 processor（instructions/contents/compaction/auth/...） | Runner (Iter-11) |
| 9 | `coordination/` A2A | §2.3 | A2A adapter、agent card 发布、跨组织互操作 | coordination (Iter-11) |

## 决策

| 问题 | 决策 |
|------|------|
| 是否一步到位做到 ADK 级别 | 否。分 A→B→C→D→E 五个阶段，每个阶段练核心能力 |
| Pydantic schema 是否替代手动 inspect | 是。`core/tools/` 的 `_infer_json_schema` 替换为 Pydantic `create_model` + `model_json_schema()` |
| Agent 层级是否替代平铺 Team | 渐进迁移。先加 `parent_agent` 字段 + model 继承链，再引入 transfer 工具，再 Agent-as-Tool |
| Hooks 是否单独建模块 | 是。`core/hooks/` 独立实现。先在 `run_tool_loop` 和 `BrainstormEngine` 中插入 hook 调用点 |
| EventBus + Coordination 谁先做 | EventBus 是基建先做（Iter-10），Coordinator 依赖 EventBus 后做（Iter-11） |
| events spec 全量是否全做 | 是。Event模型 + EventBus + EventHandler + 可靠投递 + WorkflowRule |
| coordination spec 全量是否全做 | 是。Coordinator + LaneManager + MessageBus + DAG + Worktree + StuckDetector |
| Agent-as-Tool 做不做 | 做。Transfer 做完后 Agent-as-Tool 只是加返回封装，放 Iter-11 |
| YAML config 做不做 | 做。依赖 AgentConfig（Iter-8）+ Agent树（Iter-10），放 Iter-11 |
| Session rewind 做不做 | 做。依赖 delta state（Iter-11），放 Iter-11 后端或 Iter-12 |
| Eval 什么时候做 | 每个 Iter 就近评估该 Iter 新增的能力。Iter-12+ 体系化 |

## 范围外（本次不做）

- A2A 协议（Iter-12+，coordination spec §2.3 预留 adapter 接口）
- 容器沙箱（Iter-12+，当前 sandbox 只做文件级隔离）
- LangGraph 集成
- 音频/视频 Live streaming（ADK 的 run_live 模式）
