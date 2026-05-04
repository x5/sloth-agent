# 变更提案: Iter-7 Tool 系统 — 装饰器模式 + Agent-Tool 绑定（重新设计）

> 日期: 2026-05-05（修订）
> 影响模块: core/tools/spec.md, desktop/adapters/tools.md, plans/20260425-mvp-desktop-app-plan.md

## 动机

### 原方向（已放弃）

初版提案计划通过 path dependency 复用 CLI `src/sloth_agent/core/tools/` 层。但深入分析后发现 CLI 工具层存在严重问题：

1. **重复实现**：`tool_registry.py` 有一套 `FileReadTool/BashTool/GitTool`，`builtin/` 目录又有另一套 `ReadFileTool/WriteFileTool/EditFileTool`，两套互不关联。
2. **死代码**：`builtin/` 目录中的工具从未被 `ToolRegistry` 注册，是废弃代码。
3. **OOP 继承风格**：`Tool` 抽象基类 + `ToolRegistry` 的设计偏重继承，扩展性差，与现代 SDK 的函数式风格不符。
4. **CLI 污染**：`ToolOrchestrator` 依赖 `RunState`（CLI 特有），引入该包会带入不必要的 CLI 依赖。

### 新方向（装饰器模式，参考 OpenAI/Anthropic SDK）

研究了 OpenAI Agents SDK（`@function_tool`）和 Anthropic Claude Agent SDK（`@tool`）后，采用以下核心设计：

| SDK 模式 | Sloth 适配 |
|---------|-----------|
| `@function_tool` 装饰器 → `FunctionTool` dataclass | `@desktop_tool` 装饰器 → `ToolDef` dataclass |
| 自动从类型注解生成 JSON Schema（Pydantic） | 同上（`inspect` + Pydantic） |
| 自动从 docstring 提取 description | 同上 |
| Tool 是 Agent 属性（`Agent(tools=[...])`） | `AgentTemplate.tools` 字段（工具名列表） |
| `ToolContext`（run context + tool metadata） | `ToolContext(project_root, agent_id)` |
| `allowed_tools` 白名单 | 两层白名单：`ROLE_BASE_TOOLS[role]` + `AgentTemplate.tools`（个性化追加） |
| `cwd` 沙箱隔离 | `ToolContext.project_root` 路径沙箱 |

## 决策

| 问题 | 决策 |
|------|------|
| 是否复用 CLI 工具层 | ❌ 不复用。Desktop 自成一套，不引入 path dependency |
| Tool 定义方式 | `@desktop_tool` 装饰器：Python async function → `ToolDef` dataclass |
| Schema 生成 | 自动从函数类型注解生成（`inspect` + `pydantic.TypeAdapter`） |
| 全局工具注册 | 模块级 `TOOL_POOL: dict[str, ToolDef]`，装饰器自动注册 |
| Agent-Tool 绑定 | 两层：`ROLE_BASE_TOOLS`（role 基础） + `AgentTemplate.tools`（agent 追加） |
| 路径沙箱 | `ToolContext.project_root`，每次调用验证 `os.path.realpath()` 在 project_root 内 |
| Tool-call 触发格式 | 原生 OpenAI function calling（`tools=` 参数 + `tool_calls` 响应） |
| 前端展示 | SSE 事件 `tool_call`，`ToolCallBlock` 组件解析展示 |

## 架构总览

```
backend/app/
  core/
    tool_engine.py    # ToolDef, ToolContext, @desktop_tool, TOOL_POOL
    context_engine.py # 共享 Context Engine（上下文裁剪与链路保护）
  services/
    tool_defs.py      # 所有内置工具的具体实现（用 @desktop_tool 定义）
    context.py        # Context Engine 服务层适配
    brainstorm.py     # 修改：集成 tool-call 循环 + Context Engine（首轮接入）
  models.py           # 修改：AgentTemplate.tools 字段
```

## 范围

1. `backend/app/core/tool_engine.py`（新建）— `ToolDef`, `ToolContext`, `@desktop_tool`, `TOOL_POOL`
2. `backend/app/services/tool_defs.py`（新建）— `read`, `read_range`, `grep`, `grep_repo`, `glob`, `ls_dir` 工具实现
3. `backend/app/models.py` — `AgentTemplate.tools` 字段
4. `backend/app/services/brainstorm.py` — Tool-call 循环集成
5. `backend/app/core/context_engine.py` — 共享 Context Engine（模式无关）
6. `backend/app/services/context.py` — Context Engine 适配层（Brainstorm 首轮接入）
6. `frontend/src/components/AgentDetail.tsx` — 展示 Agent tools 列表（只读）
7. `frontend/src/components/ToolCallBlock.tsx`（新建）— 展示 tool-call 执行记录

### Role 口径（与当前 seed 一致）

- `lead`: 基础工具 `read`, `grep`
- `fortune`: 基础工具 `read`, `read_range`, `glob`, `grep`, `grep_repo`, `ls_dir`

运行时：
- `effective_tools = ROLE_BASE_TOOLS[role] ∪ AgentTemplate.tools`

## 不在本次范围

- 写 Tools（write_file 等）的桌面端集成 → Iter-8
- 网络只读工具（`websearch`, `webfetch`）→ Iter-8（受限策略）
- 用户在 UI 自定义 Tool 并绑定到 Agent → 未来迭代
- Chat / Autonomous 接入共享 Context Engine → 后续迭代（Iter-7 仅 Brainstorm 首轮接入）
- 复杂的 approval/needs_approval 机制 → 未来迭代
