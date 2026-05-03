# Delta: Iter-7 Tool 系统 — 装饰器模式 + Agent-Tool 绑定（修订版）

> 关联模块: specs/tools/spec.md, specs/tools/desktop-spec.md（新建）
> 日期: 2026-05-05（修订）

---

## MODIFIED Requirements — specs/tools/spec.md

### 新增章节：Desktop Tool System（装饰器模式设计）

```
## Desktop Tool System（桌面端 Tool 架构）

Desktop backend 独立实现 Tool 系统，不依赖 CLI `src/sloth_agent` 包。
参考 OpenAI Agents SDK（@function_tool）和 Anthropic Claude Agent SDK（@tool）的设计模式。

### 核心数据结构

**ToolDef**（`backend/app/core/tool_engine.py`）
- name: str — 工具名（全局唯一）
- description: str — 工具描述（自动从 docstring 提取，或手动指定）
- params_schema: dict — JSON Schema（自动从函数类型注解生成）
- invoke: async Callable[[ToolContext, str], str] — 执行函数，签名 (ctx, args_json) → result

**ToolContext**（`backend/app/core/tool_engine.py`）
- project_root: Path — 项目根目录，用于路径沙箱
- agent_id: int — 当前执行的 Agent ID

**TOOL_POOL: dict[str, ToolDef]**
- 模块级全局字典，@desktop_tool 装饰器自动注册
- 所有内置工具在 `tool_defs.py` import 时注册完成

### @desktop_tool 装饰器

将 async Python 函数转换为 ToolDef 并注册到 TOOL_POOL：

1. 函数名 → ToolDef.name
2. 函数 docstring → ToolDef.description（支持 Google style）
3. 函数类型注解 → ToolDef.params_schema（通过 inspect + pydantic.TypeAdapter）
4. 函数本体包装为 invoke(ctx, args_json) 签名

示例：
  @desktop_tool
  async def read(ctx: ToolContext, path: str) -> str:
      """Read file contents within the project.
      
      Args:
          path: Relative path to the file within the project root.
      """
      full_path = _resolve_safe_path(ctx.project_root, path)
      return full_path.read_text(encoding="utf-8")

### 内置工具（tool_defs.py）

| 工具名 | 描述 | 参数 |
|--------|------|------|
| read | 读取项目内任意文件内容 | path: str |
| read_range | 按行读取文件片段（最多 400 行） | path: str, start_line: int, end_line: int |
| grep | 在文件内搜索匹配行 | pattern: str, path: str |
| grep_repo | 跨文件搜索匹配行（最多 200 条） | pattern: str, include_glob: str="**/*" |
| glob | 匹配项目内文件路径 | pattern: str |
| ls_dir | 查看目录树（最多 300 个条目） | path: str=".", max_depth: int=2 |

### 路径沙箱策略

_resolve_safe_path(project_root: Path, user_path: str) → Path：
1. 拼接 project_root / user_path
2. os.path.realpath() 解析符号链接
3. 验证结果必须以 project_root 开头，否则 raise ToolSecurityError
4. 验证路径实际存在（文件或目录）
```

### 新增章节：Agent-Tool 绑定模型

```
## Agent-Tool 绑定模型（两层架构）

Sloth (Global)
└── TOOL_POOL（所有注册工具的集合）
    ├── read
    ├── read_range
    ├── grep
    ├── grep_repo
    ├── glob
    └── ls_dir

第一层：ROLE_BASE_TOOLS（代码常量，Role 级别基础工具）
├── lead:    ["read", "grep"]
└── fortune: ["read", "read_range", "glob", "grep", "grep_repo", "ls_dir"]

第二层：AgentTemplate.tools（DB 字段，单个 Agent 的个性化追加工具）
├── 默认为 []（无追加）
└── 可通过 UI 为某个 Agent 定制额外工具

运行时 effective_tools：
effective = ROLE_BASE_TOOLS.get(role, []) ∪ json.loads(AgentTemplate.tools)

Inspiration.Team
├── Agent A → effective_tools → OpenAI tools=[] 参数 → 运行时白名单验证
└── Agent B → effective_tools → OpenAI tools=[] 参数 → 运行时白名单验证

规则：
- 所有 6 个内置 Provider 均兼容 OpenAI function calling 格式，使用统一接口
- 不在白名单内的 tool_name 调用，返回错误消息而非抛异常（LLM 可自我纠正）
- 工具执行在 ToolContext(project_root) 内沙箱化，防止路径遍历
```

### 新增章节：共享 Context Engine（非 Brainstorm 专属）

```
## 共享 Context Engine

Context Engine 是 Desktop Sidecar 的共享运行时能力，不隶属于单一业务模式。

模块：
- backend/app/core/context_engine.py   # 核心逻辑（模式无关）
- backend/app/services/context.py      # 业务适配层

首版能力：
- protect_reply_chains(messages, max_count)
    - 候选窗口：尾部 max_count 消息
    - 祖先保护：沿 parent_message_id 回溯并补齐祖先链
    - 输出：按时间顺序返回候选集 ∪ 祖先集合

接入策略：
- Iter-7：Brainstorm 首轮接入
- 后续：Chat / Autonomous 复用同一引擎，仅模式参数不同

约束：
- 上下文核心逻辑不得依赖 Brainstorm 状态机或 SSE 细节
- 通过 services/context.py 做模式映射与参数适配
```

---

## NEW — specs/tools/desktop-spec.md

新建文件，包含 Desktop Tool System 完整规格：
- @desktop_tool 装饰器模式与 ToolDef/ToolContext 数据结构
- 内置工具（read、read_range、grep、grep_repo、glob、ls_dir）定义
- 路径沙箱策略（_resolve_safe_path）
- 两层 Agent-Tool 绑定模型（ROLE_BASE_TOOLS + AgentTemplate.tools）
- OpenAI function calling 调用流程（含 SSE 事件格式）
- 前端展示规格（AgentDetail chips + ToolCallBlock）

并与共享 Context Engine 设计保持边界一致：Context Engine 为跨模式公用能力，Brainstorm 仅首轮接入方。

详见 `specs/tools/desktop-spec.md`。

---

## REMOVED Requirements

原提案中的"path dependency 复用 CLI Tool 层"方案废弃：
- 不添加 `sloth-agent @ file:///../` path dependency
- 不使用 `DesktopToolRegistry`（继承 CLI ToolRegistry）的方式
- 替换为 `@desktop_tool` + `TOOL_POOL` 的装饰器模式
