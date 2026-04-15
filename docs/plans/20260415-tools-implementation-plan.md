# Sloth Agent 工具实现计划

> 版本: v0.1.0
> 日期: 2026-04-15
> 基于: docs/specs/sloth-agent-tools-spec.md

---

## 1. 概述

本文档是 Sloth Agent 工具系统的实现计划，按照 spec 中定义的优先级分阶段实现。

### 1.1 实现范围

- **核心**: 文件系统工具、任务管理工具、Sloth 特色工具
- **第一阶段**: 立即需要的工具
- **第二阶段**: 建议增加的工具
- **第三阶段**: 按需扩展

---

## 2. 目录结构

```
src/
├── src/
│   └── sloth_agent/
│       └── tools/
│           ├── __init__.py
│           ├── base.py           # 工具基类定义
│           ├── registry.py      # 工具注册表
│           ├── fs/              # 文件系统工具
│           │   ├── __init__.py
│           │   ├── read.py
│           │   ├── write.py
│           │   ├── edit.py
│           │   ├── glob.py
│           │   └── grep.py
│           ├── runtime/         # 运行时工具
│           │   ├── __init__.py
│           │   ├── bash.py
│           │   └── task_run.py
│           ├── code/            # 代码智能工具
│           │   ├── __init__.py
│           │   ├── lsp.py
│           │   └── rust_analyzer.py
│           ├── task/            # 任务管理工具
│           │   ├── __init__.py
│           │   ├── task_create.py
│           │   ├── task_list.py
│           │   └── task_update.py
│           ├── web/              # Web 工具
│           │   ├── __init__.py
│           │   └── web_fetch.py
│           ├── sloth/           # Sloth 特色工具
│           │   ├── __init__.py
│           │   ├── checkpoint.py
│           │   ├── heartbeat.py
│           │   ├── skill_generate.py
│           │   ├── skill_revise.py
│           │   ├── coverage_check.py
│           │   └── test_runner.py
│           └── interaction/      # 交互工具
│               ├── __init__.py
│               ├── ask_question.py
│               └── approval_request.py
│
├── configs/
│   ├── tools.yaml              # 工具配置
│   └── permissions.yaml        # 权限配置
│
└── tests/
    └── tools/
        ├── test_registry.py
        ├── test_read.py
        ├── test_write.py
        └── ...
```

---

## 3. 第一阶段实现（核心必需）

### 3.1 工具基类和注册表

**文件**: `src/sloth_agent/tools/base.py`

```python
@dataclass
class Tool:
    """工具基类"""
    name: str
    description: str
    group: str
    risk_level: int = 1
    permission: str = "auto"  # auto / plan_approval / explicit_approval

    def execute(self, **kwargs) -> Any:
        raise NotImplementedError
```

**文件**: `src/sloth_agent/tools/registry.py`

```python
class ToolRegistry:
    """工具注册表"""
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_all(self) -> list[Tool]:
        return list(self._tools.values())
```

### 3.2 文件系统工具

| 工具 | 文件 | 优先级 |
|------|------|--------|
| Read | `fs/read.py` | P0 |
| Write | `fs/write.py` | P0 |
| Edit | `fs/edit.py` | P0 |
| Glob | `fs/glob.py` | P0 |
| Grep | `fs/grep.py` | P0 |

### 3.3 任务管理工具

| 工具 | 文件 | 优先级 |
|------|------|--------|
| TaskCreate | `task/task_create.py` | P0 |
| TaskList | `task/task_list.py` | P0 |
| TaskUpdate | `task/task_update.py` | P0 |

### 3.4 Sloth 特色工具

| 工具 | 文件 | 优先级 |
|------|------|--------|
| CheckpointSave | `sloth/checkpoint.py` | P0 |
| CheckpointLoad | `sloth/checkpoint.py` | P0 |
| Heartbeat | `sloth/heartbeat.py` | P0 |
| SkillGenerate | `sloth/skill_generate.py` | P0 |
| SkillRevise | `sloth/skill_revise.py` | P0 |

### 3.5 交互工具

| 工具 | 文件 | 优先级 |
|------|------|--------|
| AskUserQuestion | `interaction/ask_question.py` | P0 |
| ApprovalRequest | `interaction/approval_request.py` | P0 |

---

## 4. 第二阶段实现（建议）

### 4.1 运行时工具

| 工具 | 文件 | 优先级 |
|------|------|--------|
| Bash | `runtime/bash.py` | P1 |
| TaskRun | `runtime/task_run.py` | P1 |

### 4.2 代码智能工具

| 工具 | 文件 | 优先级 |
|------|------|--------|
| LSP | `code/lsp.py` | P1 |
| rust_analyzer | `code/rust_analyzer.py` | P1 |

### 4.3 Web 工具

| 工具 | 文件 | 优先级 |
|------|------|--------|
| WebFetch | `web/web_fetch.py` | P1 |
| WebSearch | `web/web_search.py` | P2 |

### 4.4 TDD 工具

| 工具 | 文件 | 优先级 |
|------|------|--------|
| TestRunner | `sloth/test_runner.py` | P1 |
| CoverageCheck | `sloth/coverage_check.py` | P1 |

---

## 5. 第三阶段实现（按需）

| 工具 | 文件 | 优先级 |
|------|------|--------|
| apply_patch | `fs/apply_patch.py` | P2 |
| exec | `runtime/exec.py` | P2 |
| code_execution | `runtime/code_execution.py` | P3 |
| typescript_lsp | `code/typescript_lsp.py` | P3 |

---

## 6. 任务分解

### 任务 1: 基础架构

```
- [ ] 创建 tools/ 目录结构
- [ ] 实现 base.py (工具基类)
- [ ] 实现 registry.py (工具注册表)
- [ ] 实现工具权限配置 (configs/permissions.yaml)
- [ ] 编写单元测试
```

### 任务 2: 文件系统工具

```
- [ ] Read 工具
- [ ] Write 工具
- [ ] Edit 工具
- [ ] Glob 工具
- [ ] Grep 工具
- [ ] apply_patch 工具 (P2)
```

### 任务 3: 任务管理工具

```
- [ ] TaskCreate 工具
- [ ] TaskList 工具
- [ ] TaskUpdate 工具
```

### 任务 4: Sloth 特色工具

```
- [ ] Checkpoint 工具
- [ ] Heartbeat 工具
- [ ] SkillGenerate 工具
- [ ] SkillRevise 工具
```

### 任务 5: 交互工具

```
- [ ] AskUserQuestion 工具
- [ ] ApprovalRequest 工具
```

### 任务 6: 运行时工具

```
- [ ] Bash 工具
- [ ] TaskRun 工具
- [ ] exec 工具 (P2)
```

### 任务 7: 代码智能工具

```
- [ ] LSP 工具
- [ ] rust_analyzer 工具
- [ ] typescript_lsp 工具 (P3)
```

### 任务 8: Web 和 TDD 工具

```
- [ ] WebFetch 工具
- [ ] WebSearch 工具 (P2)
- [ ] TestRunner 工具
- [ ] CoverageCheck 工具
```

---

## 7. 实现细节

### 7.1 工具执行流程

```
用户请求
    │
    ▼
ToolRegistry.get(name)
    │
    ▼
检查权限 (PermissionChecker)
    ├── L1 (auto) → 直接执行
    ├── L2 (plan_approval) → 检查计划是否已审批
    └── L3 (explicit_approval) → 暂停等待审批
    │
    ▼
Tool.execute(**params)
    │
    ▼
返回结果 / 错误
```

### 7.2 配置示例

```yaml
# configs/tools.yaml
tools:
  groups:
    fs:
      - Read
      - Write
      - Edit
      - Glob
      - Grep
    task:
      - TaskCreate
      - TaskList
      - TaskUpdate
    sloth:
      - CheckpointSave
      - CheckpointLoad
      - Heartbeat
      - SkillGenerate
      - SkillRevise
```

---

## 8. 测试策略

| 测试类型 | 说明 | 覆盖率目标 |
|---------|------|-----------|
| 单元测试 | 每个工具独立测试 | ≥ 80% |
| 集成测试 | 工具组合测试 | 关键路径 |
| 回归测试 | 确保不破坏现有功能 | 全部 |

---

## 9. 验收标准

### 第一阶段验收

- [ ] ToolRegistry 可以注册和获取工具
- [ ] Read/Write/Edit/Glob/Grep 可以正常工作
- [ ] TaskCreate/List/Update 可以管理工作任务
- [ ] Checkpoint 可以保存和恢复状态
- [ ] Heartbeat 可以发送心跳
- [ ] 基础权限检查正常工作

### 第二阶段验收

- [ ] Bash 可以执行 Shell 命令
- [ ] LSP 可以进行代码跳转和类型检查
- [ ] WebFetch 可以获取网页内容
- [ ] TestRunner 可以运行测试
- [ ] CoverageCheck 可以检查覆盖率

### 第三阶段验收

- [ ] apply_patch 可以批量修改文件
- [ ] exec 可以管理后台进程
- [ ] typescript_lsp 可以支持 React 项目

---

## 10. 后续计划

1. **MCP 适配**: 支持连接外部 MCP 服务器
2. **自定义工具**: 用户可注册自己的工具
3. **工具市场**: 分享和发现优秀工具
4. **IDE 集成**: VS Code / JetBrains 插件

---

*计划版本: v0.1.0*
*创建日期: 2026-04-15*
