# Sloth Agent 工具规格文档

> 版本: v0.1.0
> 日期: 2026-04-15
> 状态: 进行中

---

## 1. 概述

本文档定义 Sloth Agent 的工具集设计，融合了 Claude Code、Open Claw 的优秀设计，并针对 Rust 项目（卡牌游戏、五行运势 APP）进行了定制优化。

### 1.1 设计原则

| 原则 | 说明 |
|------|------|
| **YAGNI** | 不构建不需要的工具，按需扩展 |
| **融合优秀设计** | 继承 Claude Code / Open Claw 的精华 |
| **Rust 优先** | 两个项目都用 Rust，Rust 工具优先 |
| **风险分级** | 工具按风险分级，高风险需要审批 |

---

## 2. 工具分类体系

### 2.1 工具分组（参考 Open Claw）

```
group:fs          # 文件系统工具
group:runtime     # 运行时/执行工具
group:code        # 代码智能工具
group:task        # 任务管理工具
group:web         # Web 工具
group:sloth       # Sloth 特色工具
```

---

## 3. 核心工具清单

### 3.1 文件系统工具 (group:fs)

| 工具名 | 功能 | 风险等级 | 继承来源 | 优先级 |
|--------|------|----------|----------|--------|
| `Read` | 读取文件内容 | L1 | Claude Code | ✅ 必需 |
| `Write` | 创建/覆盖文件 | L2 | Claude Code | ✅ 必需 |
| `Edit` | 精准编辑文件 | L2 | Claude Code | ✅ 必需 |
| `apply_patch` | 多-hunk 批量补丁 | L2 | Open Claw | ✅ 建议 |
| `Glob` | 按模式匹配文件 | L1 | Claude Code | ✅ 必需 |
| `Grep` | 搜索文件内容 | L1 | Claude Code | ✅ 必需 |

#### 3.1.1 Read

```yaml
name: Read
description: 读取文件内容
risk_level: 1
permission: auto
```

```python
def read(path: str, encoding: str = "utf-8") -> str:
    """读取文件全部内容"""
    pass

def read_lines(path: str, start: int = 1, end: int = None) -> list[str]:
    """按行读取文件"""
    pass
```

#### 3.1.2 Write

```yaml
name: Write
description: 创建或覆盖文件
risk_level: 2
permission: plan_approval
```

#### 3.1.3 Edit

```yaml
name: Edit
description: 精准编辑文件的特定位置
risk_level: 2
permission: plan_approval
```

#### 3.1.4 apply_patch

```yaml
name: apply_patch
description: 应用多-hunk 文件补丁，支持批量修改多个文件
risk_level: 2
permission: plan_approval
inherit_from: OpenClaw
```

#### 3.1.5 Glob

```yaml
name: Glob
description: 按 glob 模式匹配文件
risk_level: 1
permission: auto
```

#### 3.1.6 Grep

```yaml
name: Grep
description: 正则搜索文件内容
risk_level: 1
permission: auto
```

---

### 3.2 运行时工具 (group:runtime)

| 工具名 | 功能 | 风险等级 | 继承来源 | 优先级 |
|--------|------|----------|----------|--------|
| `Bash` | 执行 Shell 命令 | L3 | Claude Code | ✅ 必需 |
| `exec` | 带进程管理的 Shell | L3 | Open Claw | ⚠️ 增强 |
| `code_execution` | 沙箱 Python 执行 | L2 | Open Claw | ⚠️ 按需 |
| `TaskRun` | 运行任务 | L2 | Sloth | ✅ 必需 |

#### 3.2.1 Bash

```yaml
name: Bash
description: 执行 Shell 命令
risk_level: 3
permission: explicit_approval
```

#### 3.2.2 exec

```yaml
name: exec
description: 执行命令并管理后台进程
risk_level: 3
permission: explicit_approval
inherit_from: OpenClaw
features:
  - background_process: 后台运行命令
  - process_kill: 终止进程
  - process_list: 列出进程
```

#### 3.2.3 TaskRun

```yaml
name: TaskRun
description: 在 workspace 中执行任务（Rust cargo / npm）
risk_level: 2
permission: auto_after_plan_approval
```

---

### 3.3 代码智能工具 (group:code)

| 工具名 | 功能 | 风险等级 | 继承来源 | 优先级 |
|--------|------|----------|----------|--------|
| `LSP` | 语言服务器（跳转定义/类型检查） | L1 | Claude Code | ✅ 必需 |
| `rust_analyzer` | Rust 代码分析 | L1 | Sloth | ✅ 必需 |
| `typescript_lsp` | TS/JS 代码分析 | L1 | Sloth | ⚠️ React 需要 |

#### 3.3.1 LSP

```yaml
name: LSP
description: 通过语言服务器提供代码智能（跳转定义、类型检查、错误提示）
risk_level: 1
permission: auto
inherit_from: ClaudeCode
features:
  - goto_definition: 跳转到定义
  - find_references: 查找引用
  - type_check: 类型检查
  - diagnostics: 错误诊断
```

#### 3.3.2 rust_analyzer

```yaml
name: rust_analyzer
description: Rust 专用语言服务器支持
risk_level: 1
permission: auto
```

---

### 3.4 任务管理工具 (group:task)

| 工具名 | 功能 | 风险等级 | 继承来源 | 优先级 |
|--------|------|----------|----------|--------|
| `TaskCreate` | 创建任务 | L1 | Claude Code | ✅ 必需 |
| `TaskList` | 列出任务 | L1 | Claude Code | ✅ 必需 |
| `TaskUpdate` | 更新任务状态 | L1 | Claude Code | ✅ 必需 |
| `TaskGet` | 获取任务详情 | L1 | Claude Code | ⚠️ 建议 |

#### 3.4.1 TaskCreate

```yaml
name: TaskCreate
description: 在任务列表中创建新任务
risk_level: 1
permission: auto
```

#### 3.4.2 TaskUpdate

```yaml
name: TaskUpdate
description: 更新任务状态（pending/running/completed/failed）
risk_level: 1
permission: auto
```

---

### 3.5 Web 工具 (group:web)

| 工具名 | 功能 | 风险等级 | 继承来源 | 优先级 |
|--------|------|----------|----------|--------|
| `WebFetch` | 获取 URL 内容 | L2 | Claude Code | ✅ 必需 |
| `WebSearch` | 网络搜索 | L2 | Claude Code | ⚠️ 建议 |

#### 3.5.1 WebFetch

```yaml
name: WebFetch
description: 获取指定 URL 的内容
risk_level: 2
permission: auto
use_cases:
  - 获取 AI API 文档
  - 抓取寺庙信息
  - 获取第三方 API 文档
```

---

### 3.6 交互工具

| 工具名 | 功能 | 风险等级 | 继承来源 | 优先级 |
|--------|------|----------|----------|--------|
| `AskUserQuestion` | 向用户提问 | L1 | Claude Code | ✅ 审批必需 |
| `ApprovalRequest` | 发送审批请求 | L1 | Sloth | ✅ 必需 |

#### 3.6.1 AskUserQuestion

```yaml
name: AskUserQuestion
description: 向用户提问以收集需求或澄清歧义
risk_level: 1
permission: auto
```

#### 3.6.2 ApprovalRequest

```yaml
name: ApprovalRequest
description: 发送计划/高风险操作给用户审批
risk_level: 1
permission: auto
channels:
  - feishu: 飞书卡片消息
  - email: 邮件通知
```

---

## 4. Sloth 特色工具

### 4.1 可靠性工具 (group:sloth/reliability)

| 工具名 | 功能 | 风险等级 | 优先级 |
|--------|------|----------|--------|
| `CheckpointSave` | 保存执行状态到磁盘 | L1 | ✅ 必需 |
| `CheckpointLoad` | 从磁盘恢复执行状态 | L1 | ✅ 必需 |
| `Heartbeat` | 发送心跳给 Watchdog | L1 | ✅ 必需 |

#### 4.1.1 CheckpointSave

```yaml
name: CheckpointSave
description: 将当前任务状态保存到检查点文件
risk_level: 1
permission: auto
storage: .sloth-agent/checkpoints/
format: JSON
```

#### 4.1.2 Heartbeat

```yaml
name: Heartbeat
description: 向 Watchdog 发送心跳信号
risk_level: 1
permission: auto
interval: 180  # 3 分钟
```

---

### 4.2 技能进化工具 (group:sloth/evolution)

| 工具名 | 功能 | 风险等级 | 优先级 |
|--------|------|----------|--------|
| `SkillGenerate` | 从错误生成新技能 | L1 | ✅ 必需 |
| `SkillRevise` | 修正/完善已有技能 | L1 | ✅ 必需 |
| `SkillSearch` | 搜索相关技能 | L1 | ✅ 必需 |

#### 4.2.1 SkillGenerate

```yaml
name: SkillGenerate
description: 从执行错误或成功经验中生成新的技能文档
risk_level: 1
permission: auto
output: Markdown with YAML frontmatter
storage: .sloth-agent/skills/
```

#### 4.2.2 SkillRevise

```yaml
name: SkillRevise
description: 修正或扩展已有技能
risk_level: 1
permission: auto
triggers:
  - error_driven: 错误驱动修正
  - experience_accumulation: 经验沉淀
  - periodic_audit: 定期审计
```

---

### 4.3 TDD 工具 (group:sloth/tdd)

| 工具名 | 功能 | 风险等级 | 优先级 |
|--------|------|----------|--------|
| `TestRunner` | 运行测试用例 | L2 | ✅ 必需 |
| `CoverageCheck` | 检查测试覆盖率 | L1 | ✅ 必需 |
| `CoverageGate` | 覆盖率门槛检查 | L1 | ✅ 必需 |

#### 4.3.1 TestRunner

```yaml
name: TestRunner
description: 运行项目测试（cargo test / pytest / npm test）
risk_level: 2
permission: auto_after_plan_approval
supported:
  - cargo: Rust 项目
  - pytest: Python 项目
  - npm: Node.js 项目
```

#### 4.3.2 CoverageCheck

```yaml
name: CoverageCheck
description: 检查测试覆盖率是否达标
risk_level: 1
permission: auto
threshold: 80  # 可配置
```

---

## 5. 项目定制配置

### 5.1 通用配置（所有项目）

```yaml
# 通用工具 - 所有项目都需要
core_tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
  - TaskCreate
  - TaskList
  - TaskUpdate
  - LSP
  - WebFetch
  - AskUserQuestion
  - CheckpointSave
  - CheckpointLoad
  - Heartbeat
  - SkillGenerate
  - SkillRevise
  - TestRunner
  - CoverageCheck
```

### 5.2 Rust 项目配置

```yaml
# 适用于：卡牌游戏、五行运势后端
rust_tools:
  cargo: true
  rust_analyzer: true
  rustfmt: true
  clippy: true

  # 构建目标
  build_targets:
    - cargo build
    - cargo test
    - cargo clippy

  # 特定工具
  extra_tools:
    - wasm-pack  # 如果需要 WebAssembly
```

### 5.3 前端 React 配置（五行运势 APP）

```yaml
react_tools:
  npm: true
  typescript_lsp: true
  eslint: true

  build_targets:
    - npm run build
    - npm test
    - npm run lint
```

### 5.4 游戏项目配置（卡牌游戏）

```yaml
game_tools:
  # Rust 游戏引擎
  bevy: true      # 或 macroquad
  wasm-pack: true # WebAssembly 构建

  # iOS/Android 构建
  xcodebuild: true
  android_sdk: true

  # 特定工具
  extra_tools:
    - wasm-pack build --target web  # H5 版本
```

---

## 6. 权限分级

### 6.1 权限等级

| 等级 | 说明 | 审批要求 |
|------|------|---------|
| L1 | 只读、低风险操作 | 自动执行 |
| L2 | 写操作、不破坏性 | 计划审批一次 |
| L3 | Shell 执行、可能破坏 | 逐次审批 |
| L4 | 系统级操作 | 明确标注+额外审批 |

### 6.2 权限配置示例

```yaml
# .sloth-agent/configs/permissions.yaml
permissions:
  default_policy: ask  # 默认需要审批

  # 自动执行的工具
  auto:
    - Read
    - Glob
    - Grep
    - TaskCreate
    - TaskList
    - TaskUpdate
    - Heartbeat
    - CheckpointSave
    - CheckpointLoad

  # 需要计划审批的
  plan_approval:
    - Write
    - Edit
    - apply_patch
    - TestRunner

  # 需要逐次审批的
  explicit_approval:
    - Bash
    - exec

  # 高风险操作
  high_risk:
    - delete_file
    - git_force_push
```

---

## 7. 工具注册机制

### 7.1 工具注册表

```python
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool, group: str):
        """注册工具到指定分组"""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """获取工具"""
        return self._tools.get(name)

    def list_by_group(self, group: str) -> list[Tool]:
        """按分组列出工具"""
        return [t for t in self._tools.values() if t.group == group]

    def list_all(self) -> list[Tool]:
        """列出所有工具"""
        return list(self._tools.values())
```

### 7.2 工具定义

```python
@dataclass
class Tool:
    name: str
    description: str
    group: str
    risk_level: int
    permission: str  # auto / plan_approval / explicit_approval
    execute: Callable
    params: dict  # 参数定义
    inherit_from: str | None = None  # 继承自哪个框架
```

---

## 8. 扩展机制

### 8.1 MCP 工具适配（后续）

```yaml
# MCP 工具配置（后续版本）
mcp:
  enabled: false
  servers: []
```

### 8.2 自定义工具注册

```yaml
# 用户可以注册自己的工具
custom_tools:
  - name: my_tool
    command: "python scripts/my_tool.py"
    risk_level: 2
```

---

## 9. 实现优先级

### 第一阶段（核心必需）

```
✅ Read, Write, Edit, Glob, Grep
✅ Bash, TaskCreate, TaskList, TaskUpdate
✅ CheckpointSave, CheckpointLoad, Heartbeat
✅ WebFetch, AskUserQuestion
✅ SkillGenerate, SkillRevise
```

### 第二阶段（建议）

```
⚠️ apply_patch (多文件编辑)
⚠️ TestRunner, CoverageCheck
⚠️ LSP (rust_analyzer)
⚠️ WebSearch
```

### 第三阶段（按需）

```
⚠️ exec (进程管理)
⚠️ code_execution (沙箱执行)
⚠️ typescript_lsp
⚠️ wasm-pack, xcodebuild, android_sdk
```

---

## 10. 参考来源

| 来源 | 工具 | 说明 |
|------|------|------|
| Claude Code | Read, Write, Edit, Glob, Grep, Bash, Task*, LSP | 核心必需 |
| Claude Code | WebFetch, WebSearch, AskUserQuestion | Web + 交互 |
| Open Claw | apply_patch | 多-hunk 补丁 |
| Open Claw | exec | 进程管理 |
| Open Claw | code_execution | 沙箱执行 |
| Sloth 设计 | Checkpoint, Heartbeat | 可靠性 |
| Sloth 设计 | SkillGenerate/Revise | 自进化 |
| Sloth 设计 | CoverageCheck | TDD |

---

*文档版本: v0.1.0*
*最后更新: 2026-04-15*
