# Sloth Agent 工具实现计划

> 版本: v1.0.0
> 日期: 2026-04-15
> 基于: docs/specs/20260416-02-tools-invocation-spec.md（合并后权威基准）
> 关联: 工具执行运行时机制（同文档 §1-§9）

---

## 1. 概述

本文档是 Sloth Agent 工具系统的实现计划。所有工具定义以 `docs/specs/20260416-02-tools-invocation-spec.md` 为准。

### 1.1 实现范围

- **核心**: 文件系统工具、运行时工具、代码智能、任务管理、Web、交互、Sloth 特色工具
- **第一阶段**: 核心必需工具
- **第二阶段**: 建议增加的工具
- **第三阶段**: 按需扩展

---

## 2. 目录结构

```
src/
└── sloth_agent/
    └── core/
        └── tools/
            ├── __init__.py
            ├── models.py              # 数据模型（ToolCallRequest, ToolResult 等）
            ├── tool_registry.py       # Tool 基类 + ToolRegistry
            ├── hallucination_guard.py # 幻觉防护
            ├── risk_gate.py           # 风险门控
            ├── executor.py            # 执行器（超时/重试）
            ├── formatter.py           # 结果格式化
            ├── orchestrator.py        # 总调度器
            └── builtin/               # 内建工具实现
                ├── __init__.py
                ├── file_ops.py        # read_file, write_file, edit_file
                ├── shell.py           # run_command
                └── search.py          # glob, grep

configs/
├── tools.yaml              # 工具分组配置
└── permissions.yaml        # 权限配置

tests/
└── core/
    └── tools/
        ├── test_models.py
        ├── test_registry.py
        ├── test_file_ops.py
        ├── test_shell.py
        ├── test_search.py
        └── ...
```

> **注意**: 实际实现路径为 `src/sloth_agent/core/tools/`，不是计划文档最初写的 `src/sloth_agent/tools/`。
> 核心运行时组件（RiskGate, Executor 等）放在 core/tools/ 下，与 Runner 和 RunState 同层。

---

## 3. Tool 基类实现

基于权威 spec，Tool 基类应包含：

```python
class Tool:
    name: str                       # snake_case, e.g., "read_file"
    description: str
    group: str                      # "fs" | "runtime" | "code" | "task" | "web" | "sloth" | "interaction"
    risk_level: int = 1             # 1-4
    permission: str = "auto"        # "auto" | "plan_approval" | "explicit_approval" | "high_risk"
    category: ToolCategory          # 语义分类 (read/write/edit/execute/search/vcs/...)
    inherit_from: str | None = None # "Claude Code" | "Open Claw" | "Sloth" | None
    metadata: ToolMetadata          # timeout, retries, rollback_strategy, etc.
    params: dict = {}               # 参数定义

    @abstractmethod
    def execute(self, **kwargs) -> Any: ...

    def get_schema(self) -> dict: ...  # OpenAI-compatible function calling schema
```

## 4. ToolRegistry 实现

```python
class ToolRegistry:
    def __init__(self, config: Config): ...
    def register(self, tool: Tool): ...
    def get(self, name: str) -> Tool | None: ...
    def list_all(self) -> list[Tool]: ...
    def list_by_group(self, group: str) -> list[Tool]: ...
    def execute_tool(self, name: str, **kwargs) -> Any: ...
```

## 5. 配置

### 5.1 configs/tools.yaml

工具分组配置，定义哪些工具属于哪个组。见权威 spec §6.1。

### 5.2 configs/permissions.yaml

权限配置，定义 auto / plan_approval / explicit_approval 各包含哪些工具。见权威 spec §6.2。

---

## 6. 第一阶段实现（核心必需）

### 6.1 工具基类和注册表

- [x] `tool_registry.py` — Tool 基类 + ToolRegistry（含 `list_by_group`）
- [x] `models.py` — ToolCallRequest, ToolResult, ToolExecutionRecord, RiskDecision, Interruption, RejectedCall

### 6.2 文件系统工具

| 工具 | 文件 | 状态 |
|------|------|------|
| read_file (+ read_lines) | `builtin/file_ops.py` | ✅ 已实现 |
| write_file | `builtin/file_ops.py` | ✅ 已实现 |
| edit_file | `builtin/file_ops.py` | ✅ 已实现 |
| glob | `builtin/search.py` | ✅ 已实现 |
| grep | `builtin/search.py` | ✅ 已实现 |

### 6.3 运行时工具

| 工具 | 文件 | 状态 |
|------|------|------|
| run_command | `builtin/shell.py` | ✅ 已实现 |

### 6.4 执行运行时组件

| 组件 | 文件 | 状态 |
|------|------|------|
| HallucinationGuard | `hallucination_guard.py` | ✅ 已实现 |
| RiskGate | `risk_gate.py` | ✅ 已实现 |
| Executor | `executor.py` | ✅ 已实现 |
| ResultFormatter | `formatter.py` | ✅ 已实现 |
| ToolOrchestrator | `orchestrator.py` | ✅ 已实现 |

### 6.5 配置

| 文件 | 状态 |
|------|------|
| `configs/tools.yaml` | ⬜ 待创建 |
| `configs/permissions.yaml` | ⬜ 待创建 |

---

## 7. 第二阶段实现（建议）

| 工具 | 文件 | 优先级 |
|------|------|--------|
| apply_patch | `builtin/file_ops.py` | P1 |
| test_runner | `builtin/test_runner.py` | P1 |
| coverage_check | `builtin/coverage.py` | P1 |
| lsp | `builtin/lsp.py` | P1 |
| web_fetch | `builtin/web.py` | P1 |
| web_search | `builtin/web.py` | P1 |

---

## 8. 第三阶段实现（按需）

| 工具 | 文件 | 优先级 |
|------|------|--------|
| exec | `builtin/shell.py` | P2 |
| code_execution | `builtin/code_exec.py` | P2 |
| typescript_lsp | `builtin/lsp.py` | P2 |

---

## 9. 测试策略

| 测试类型 | 说明 | 覆盖率目标 |
|---------|------|-----------|
| 单元测试 | 每个工具独立测试 | ≥ 80% |
| 集成测试 | 工具组合测试 | 关键路径 |
| 回归测试 | 确保不破坏现有功能 | 全部 |

---

## 10. 验收标准

### 第一阶段验收

- [x] ToolRegistry 可以注册、获取、按组列出工具
- [x] read_file / write_file / edit_file / glob / grep 可以正常工作
- [x] run_command 可以执行 Shell 命令
- [x] HallucinationGuard 拦截路径越权、黑名单命令
- [x] RiskGate 按风险等级和权限正确放行/拒绝
- [x] Executor 支持超时和指数退避重试
- [x] ToolOrchestrator 串联 RiskGate → Executor → RunState
- [x] 所有测试通过

### 第二阶段验收（待实现）

- [ ] apply_patch 可以批量修改文件
- [ ] test_runner 可以运行测试
- [ ] coverage_check 可以检查覆盖率
- [ ] web_fetch 可以获取网页内容

### 第三阶段验收（待实现）

- [ ] exec 可以管理后台进程
- [ ] typescript_lsp 可以支持 React 项目

---

*计划版本: v1.0.0*
*创建日期: 2026-04-15*
*更新日期: 2026-04-17*
