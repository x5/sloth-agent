# Desktop Tool System

> 关联: specs/tools/spec.md（CLI Tool 系统），specs/desktop/spec.md（桌面端整体架构）
> 最后更新: 2026-05-03
> Scope: Desktop

## 概述

Desktop backend 独立实现的 Tool 系统，不依赖 CLI `src/sloth_agent` 包。
参考 OpenAI Agents SDK（`@function_tool`）和 Anthropic Claude Agent SDK（`@tool`）的装饰器模式。
所有 6 个内置 Provider（DeepSeek/Qwen/Kimi/GLM/MiniMax/Mimo）均兼容 OpenAI function calling 格式，使用统一接口。

---

## 核心架构

### 文件位置

| 文件 | 职责 |
|------|------|
| `backend/app/core/tool_engine.py` | ToolDef、ToolContext、@desktop_tool 装饰器、TOOL_POOL、ROLE_BASE_TOOLS |
| `backend/app/services/tool_defs.py` | 内置工具实现（read、read_range、grep、grep_repo、glob、ls_dir） |

---

## 核心数据结构

### ToolDef

```python
@dataclass
class ToolDef:
    name: str                                       # 工具名（全局唯一）
    description: str                                # 工具描述（自动从 docstring 提取）
    params_schema: dict                             # JSON Schema（自动从类型注解生成）
    invoke: Callable[[ToolContext, str], Awaitable[str]]  # 执行函数 (ctx, args_json) → result
```

### ToolContext

```python
@dataclass
class ToolContext:
    project_root: Path   # 项目根目录，用于路径沙箱
    agent_id: int        # 当前执行的 Agent ID
```

### TOOL_POOL

```python
TOOL_POOL: dict[str, ToolDef] = {}  # 模块级全局字典，@desktop_tool 装饰器自动注册
```

---

## @desktop_tool 装饰器

将 async Python 函数转换为 ToolDef 并注册到 TOOL_POOL：

1. 函数名 → `ToolDef.name`
2. 函数 docstring → `ToolDef.description`（支持 Google style）
3. 函数类型注解 → `ToolDef.params_schema`（通过 `inspect` + `pydantic.TypeAdapter` 生成 JSON Schema）
4. 函数本体包装为 `invoke(ctx, args_json)` 签名

```python
@desktop_tool
async def read(ctx: ToolContext, path: str) -> str:
    """Read file contents within the project.

    Args:
        path: Relative path to the file within the project root.
    """
    full_path = _resolve_safe_path(ctx.project_root, path)
    return full_path.read_text(encoding="utf-8")
```

---

## 内置工具

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `read` | 读取项目内任意文件内容 | `path: str` |
| `read_range` | 按行读取文件片段（最多 400 行） | `path: str, start_line: int, end_line: int` |
| `grep` | 在文件内搜索匹配行（re.finditer，最多 50 行） | `pattern: str, path: str` |
| `grep_repo` | 跨文件搜索匹配行（最多 200 条） | `pattern: str, include_glob: str="**/*"` |
| `glob` | 匹配项目内文件路径（最多 100 个） | `pattern: str` |
| `ls_dir` | 查看目录树（最多 300 个条目） | `path: str=".", max_depth: int=2` |

> 迭代边界：Iter-7 不包含 `websearch` / `webfetch`。
> 该两项计划在 Iter-8 以“受限网络只读工具”形式引入（仅 https、域名策略、超时与响应大小上限、结果来源追踪）。

### Iter-8 受限网络工具约束（预告）

- `websearch(query, top_k)`：`top_k` 最大 10，默认 5
- `webfetch(url)`：仅允许 `https`，禁止私网/回环地址
- 超时：连接 10s，整体 30s
- 响应体上限：300KB
- 失败返回结构化错误码（如 `NETWORK_TIMEOUT`、`NETWORK_FORBIDDEN_HOST`）
- 每次调用记录审计字段（agent/session/url/query/duration/bytes/error_code）

---

## 路径沙箱策略

`_resolve_safe_path(project_root: Path, user_path: str) → Path`：

1. 拼接 `project_root / user_path`
2. `os.path.realpath()` 解析符号链接
3. 验证结果必须以 `project_root` 开头，否则 `raise ToolSecurityError`
4. 验证路径实际存在（文件或目录）

---

## Agent-Tool 绑定模型（两层架构）

### 第一层：ROLE_BASE_TOOLS（代码常量）

Role 级别基础工具，同一 role 的所有 agent 共享：

当前内置 seed role 为 `lead` 与 `fortune`，此处配置需与 `backend/app/services/agent.py` 保持一致。

```python
ROLE_BASE_TOOLS: dict[str, list[str]] = {
    "lead":    ["read", "grep"],
    "fortune": ["read", "read_range", "glob", "grep", "grep_repo", "ls_dir"],
}
```

### 第二层：AgentTemplate.tools（DB 字段）

单个 Agent 的个性化追加工具，存储为 JSON 字符串，默认 `[]`。
可通过 UI 为某个 Agent 定制额外工具，不影响同 role 其他 agent。

### 运行时合并

```python
# BrainstormEngine 中
effective_tools = set(ROLE_BASE_TOOLS.get(agent.role, [])) | set(json.loads(template.tools))
```

---

## Tool 调用流程（OpenAI Function Calling）

```
BrainstormEngine
  │
  ├─ 1. 计算 effective_tools = ROLE_BASE_TOOLS[role] ∪ AgentTemplate.tools
  │
  ├─ 2. 构建 OpenAI tools schema：
  │      [{"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}]
  │
  ├─ 3. 调用 LLM，传入 tools= 参数
  │
  ├─ 4. LLM 返回 tool_calls 字段
  │      ├─ 验证 tool_name 在 effective_tools 白名单内
  │      ├─ 从 TOOL_POOL 取出 ToolDef
  │      ├─ 调用 invoke(ctx, args_json)（ToolContext 沙箱）
  │      └─ 发出 SSE 事件：{"event": "tool_call", "data": {"tool", "args", "result", "success"}}
  │
  ├─ 5. 将 {"role": "tool", "tool_call_id": ..., "content": result} 回写 messages
  │
  ├─ 6. 继续调用 LLM（最多循环 3 次）
  │
  └─ 7. LLM 不再返回 tool_calls → 流式输出最终回答
```

### 错误处理

| 场景 | 处理 |
|------|------|
| `tool_name` 不在白名单 | 返回"该工具不在权限范围内"，SSE `success=false` |
| `ToolSecurityError`（路径越界） | 返回"路径越界，拒绝访问"，SSE `success=false` |
| 其他执行异常 | 返回"执行错误: {str(e)}"，SSE `success=false` |
| 超过 3 次 tool-call | 截断，返回已有内容 |

---

## SSE 事件

```json
{
  "event": "tool_call",
  "data": {
    "tool": "read",
    "args": {"path": "README.md"},
    "result": "...",
    "success": true
  }
}
```

---

## 前端展示

- **AgentDetail**：展示 agent 的 `effective_tools`（只读 chips，`font-family: monospace`）
- **ToolCallBlock**：消息气泡内折叠展示 tool-call 执行记录，订阅 `tool_call` SSE 事件，按 `message_id` 聚合

---

## 约束

- 仅在 **Brainstorm 模式**下触发工具调用；Chat 模式不支持
- 工具均为只读（`read`/`read_range`/`grep`/`grep_repo`/`glob`/`ls_dir`），不修改项目文件
- `project_root` 从环境变量 `SLOTH_PROJECT_ROOT` 读取，fallback `Path.cwd()`
