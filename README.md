<p align="center">
  <img src="docs/assets/sloth-agent-banner.png" alt="sloth agent banner - the beast for beasts" width="100%">
</p>

---

# Sloth Agent

> **Sloth**: 你是在职的牛马吗？
>
> **我**: 是！

> **Sloth**: 你想有自己的牛马吗？
>
> **我**: 想！

> **Sloth**: Try Me，我来做你的牛马~

> [!NOTE]
> **最新版本 v0.3.6** — 安装脚本兼容性修复，产品描述统一。
> [查看 Release](https://github.com/x5/sloth-agent/releases) · [安装指南](docs/guides/20260417-v0.1-installation-guide.md)

---

## 产品定位

Sloth Agent 是一站式全能开发智能 Agent。整合了 OpenClaw、Hermes Agent 的核心能力，借鉴参考了 Claude Code、Codex 这类行业顶尖工具的好用经验，同时适配优化了咱们国内的技术环境与各类工具生态。

主要面向产品经理、项目经理：你擅长构思产品、梳理业务逻辑，有完整的想法和规划，唯独缺少编程功底和项目工程落地能力。

有了它，从想法落地、写代码、代码审核检查，再到云端上线部署，全部流程它自己独立完成。过程中自带多层自动质量把关，关键节点层层校验质量，不用你懂开发，就能把脑子里的产品想法直接做成可运行的完整项目。

---

## 核心特性

### 全自主流水线

```
Plan ─→ [Builder] ─→ Gate 1 ─→ [Reviewer] ─→ Gate 2 ─→ [Deployer] ─→ Gate 3 ─→ Done
         deepseek      lint      qwen/claude     test       deepseek         smoke
         编码+调试     type      审查+验证       coverage   部署+验证        test
```

一份 Plan 文件，一键跑完编码、审查、部署全流程：

```bash
sloth run --plan plan.md
```

- **三个 Agent 接力执行**，Builder 写代码 → Reviewer 审查 → Deployer 上线
- **Review 必须用不同模型**，同一个模型审自己的代码没有意义
- **三道质量门控**自动把关：lint、测试覆盖率、smoke test，不过就回滚
- **出错自动调整**：失败多次后自动重规划，不卡死在一条路上

### 技能系统

支持 SKILL.md 格式技能（兼容 Claude Code），即插即用：

```bash
sloth skills list          # 查看所有技能
sloth skills show <name>   # 查看技能详情
sloth skills search <kw>   # 搜索相关技能
```

- 3 级自动匹配：精确名称 → 触发词 → 关键词
- 可以自己写技能文件放进项目目录，自动加载

### 成本管控

每次 LLM 调用自动记录花费：

```bash
sloth cost summary     # 查看总览
sloth cost breakdown   # 按模型/Provider 分解
```

- 内置多模型定价表，开箱即用
- 支持预算限额，快超了会提醒

### 聊天交互

```bash
sloth chat
```

- 启动显示欢迎屏和可用命令
- `/start autonomous` 启动流水线，`/status` 看进度
- `/skill` 查看和执行技能
- 全中文界面，帮助信息说人话

### 容错机制

- **CircuitBreaker**：某个 Provider 连续报错自动熔断
- **自动降级**：首选不行换备用，都不行用 Mock 兜底
- 支持 6 个 Provider（DeepSeek / Qwen / Kimi / GLM / MiniMax / 小米）

### 内置能力

| 能力 | 状态 | 说明 |
|------|------|------|
| **Runtime Kernel** | ✅ | 单一 Runner 内核 + RunState + NextStep 协议 |
| **Reflection + Stuck Detection** | ✅ | 执行失败自动反思，检测重复错误模式并切换策略 |
| **Adaptive Replanning** | ✅ | 门控失败/上下文溢出时自动调整方案 |
| **Context Window Manager** | ✅ | Token 计数截断 + 对话摘要压缩 |
| **Streaming** | ✅ | text/tool_call 交织处理 + CLI 实时渲染 |
| **Git Checkpoint** | ✅ | 3 级检查点（task/stage/session），门控失败自动回滚 |
| **Structured Handoff** | ✅ | BuilderOutput / ReviewerOutput / DeployResult 交接协议 |
| **Skill Management** | ✅ | Validator + Router + Injector，SKILL.md 加载 |
| **Cost Tracking** | ✅ | JSONL 持久化 + 预算限额 + CLI 查询 |
| **Provider Fallback** | ✅ | CircuitBreaker 三态机 + 自动降级链 |
| **Chat Mode** | ✅ | REPL + SessionManager + 自主模式 + 中文优先 |
| **Config Manager** | ✅ | 三级配置合并 + 交互式向导 + API Key 验证 |
| **LLM Router** | ✅ | Agent 级模型路由配置 |
| **Memory Store** | ✅ | 纯文件系统 jsonl 存储 |
| **Hallucination Guard** | ✅ | 路径验证 + 命令白名单 + import 检查 |
| **Tool Registry** | ✅ | Claude Code 对齐的工具层 + RiskGate |
| **Agent Registry** | ✅ | Agent-First 架构，从 agents/*.md 加载定义 |

### 远期目标：8+ Agent 架构

| Agent 角色 | 推荐模型 |
|-----------|---------|
| **Analyst** | qwen3.6-plus |
| **Planner** | qwen3-max |
| **Engineer** | deepseek-v3.2 |
| **Debugger** | deepseek-r1-0528 |
| **Reviewer** | glm-5.1 / claude-sonnet |
| **QA** | glm-5.1 / claude-sonnet |
| **Release** | deepseek-v3.2 |
| **Monitor** | qwen3.5-plus |
| **General** | 可配置 |

多 Agent 扩展后支持并行执行、上下文隔离、角色专业化、多场景编排。

### 工作模式演进

| 版本 | 模式 | 说明 |
|------|------|------|
| v0.1.0 | 自主模式 | 输入 Plan，全自主执行 3-Agent 流水线 |
| v0.2.0 | + 对话模式 | REPL 交互，聊天界面中文优先 |
| v0.3.0 | + 技能 + 成本 | Skill 系统 + Cost Tracking + 容错 + 自适应执行 |
| v0.3.x | + Agent-First | Agent 注册表替代 Stage 概念，自适应重规划 |
| v0.5 | + 多 Agent 并行 | 知识库 + 事件总线 + Speculative Execution |
| v0.8 | + 昼夜循环 | Persistent Daemon 常驻，夜间分析→日间执行 |
| v1.0 | 完整架构 | 8+ Agent + 多场景编排 |

---

## 设计原则

| 原则 | 当前 | 远期 |
|------|------|------|
| **Agent 架构** | Agent-First 串行流水线 | 多 Agent 并行执行 |
| **工具优先** | Agent 通过工具层操作，可审计 | + Plugin 扩展 |
| **技能即指令** | SKILL.md prompt 模板，兼容 Claude Code | + 自动进化 |
| **存储** | 纯文件系统（jsonl） | + SQLite 索引 + ChromaDB 向量 |
| **质量保障** | 自动门控（lint/type/test/coverage/smoke） | + 事件驱动规则 |
| **模型路由** | Agent 级（deepseek→编码, qwen→审查） | Agent 级配置 + 降级 |
| **安全默认** | 路径白名单 + 命令黑名单 + 幻觉防护 | 5 层安全 + 沙箱 |
| **文件系统即真相** | JSON/jsonl，可回溯、可审计、可手动编辑 | 同左 |

---

## 与参考框架的对比

| 特性 | OpenClaw | Hermes | Claude Code | Codex | **Sloth** |
|------|----------|--------|-------------|-------|-----------|
| 多 Agent 架构 | ❌ | ✅ 子代理 | ❌ | ❌ | ✅ **3-Agent Pipeline** |
| 自动门控 | ❌ | ❌ | ❌ | ❌ | ✅ **lint/type/test/smoke** |
| Reflection | 部分 | ❌ | 部分 | ❌ | ✅ **Stuck Detection** |
| 技能系统 | ✅ | ✅ | ✅ | ❌ | ✅ SKILL.md (兼容) |
| 安全防护 | ✅ | ✅ | Risk levels | Risk | ✅ **幻觉防护 + 白名单** |
| 模型路由 | ✅ | ✅ | ❌ | ❌ | ✅ **Agent 级路由** |
| 自动回滚 | ❌ | ❌ | ❌ | ❌ | ✅ **3 级 Git Checkpoint** |
| 成本控制 | ❌ | ❌ | ❌ | ❌ | ✅ **CostTracker + 预算限额** |
| 中国生态 | ❌ | ❌ | ❌ | ❌ | ✅ **DeepSeek/Qwen/Kimi** |

---

## 支持的 LLM Provider

| Provider | 模型 | 用途 |
|----------|------|------|
| **DeepSeek** | deepseek-v3.2 (最新)<br>deepseek-r1-0528 (推理)<br>deepseek-v4 (即将发布) | 主力编码与推理 |
| **Qwen** | qwen3.6-plus (最新旗舰)<br>qwen3.5-plus (多模态)<br>qwen3-max (文本旗舰) | 低成本到高性能全覆盖 |
| **Kimi** | kimi-k2.5 (最新旗舰)<br>kimi-k2 (上一代)<br>kimi-claw (浏览器Agent) | 视觉编码智能体 |
| **GLM** | glm-5.1 (最新)<br>glm-5 (旗舰)<br>glm-4.5-flash (免费) | 编程+8h持续工作 |
| **MiniMax** | minimax-m2.7 (最新)<br>minimax-m1 (MoE) | 自进化能力 |
| **Xiaomi** | mimo-v2-pro (最新旗舰)<br>mimo-v2-omni (全模态)<br>mimo-v2-flash (轻量) | 高强度 Agent 工作流 |

至少配置 DeepSeek + Qwen 即可跑通。

---

## 内置工具（对齐 Claude Code）

| 工具 | 说明 | 风险等级 |
|------|------|---------|
| `read_file` | 读取文件内容 | 只读 |
| `write_file` | 写入文件（新建/覆盖） | 低 |
| `edit_file` | 精确字符串替换 | 中 |
| `run_command` | 执行 Shell 命令 | 高 |
| `glob` | 文件模式匹配搜索 | 只读 |
| `grep` | 内容搜索 | 只读 |
| `use_mcp_tool` | 调用 MCP 工具 | 高 |
| `access_mcp_resource` | 访问 MCP 资源 | 中 |
| `skill_activate` | 激活技能 | 中 |

---

## 安装

### macOS / Linux / WSL2

```bash
curl -fsSL https://raw.githubusercontent.com/x5/sloth-agent/master/scripts/install.sh | bash
```

或手动安装：

```bash
git clone git@github.com:x5/sloth-agent.git ~/.sloth-agent
cd ~/.sloth-agent
uv sync --dev
uv run sloth --help
```

### Windows (PowerShell)

```powershell
iwr -useb https://raw.githubusercontent.com/x5/sloth-agent/master/scripts/install.ps1 | iex
```

或手动安装：

```powershell
git clone git@github.com:x5/sloth-agent.git $HOME\.sloth-agent
cd $HOME\.sloth-agent
uv sync --dev
uv run sloth --help
```

### 初始化配置

```bash
# 交互式配置向导（推荐）
sloth config init --interactive

# 或创建模板文件后手动编辑
sloth config init
cp ~/.sloth-agent/.env.example ~/.sloth-agent/.env
```

### 验证安装

```bash
# 查看帮助
uv run sloth --help

# 运行测试
uv run pytest tests/ evals/ -v

# Smoke test
uv run python -c "from evals.smoke_test import run_smoke_test; r = run_smoke_test(); print(f'PASS' if r.passed else 'FAIL')"
```

详细安装步骤见 [安装指南](docs/guides/20260417-v0.1-installation-guide.md)。

### 卸载

```bash
# 预览将删除的内容（不实际删除）
sloth uninstall --dry-run

# 卸载（交互式确认）
sloth uninstall

# 完整卸载（含配置和 API Key）
sloth uninstall --full

# 跳过确认
sloth uninstall --yes
```

---

## 快速开始

```bash
# 1. 初始化配置（首次使用）
sloth config init --interactive

# 2. 准备一份 Plan 文件（Markdown 格式）

# 3. 执行自主流水线
uv run sloth run --plan plan.md

# 4. 查看执行状态
uv run sloth status

# 5. 查看日志
uv run sloth logs --level INFO --limit 50
```

### 常用 CLI 命令

| 命令 | 说明 |
|------|------|
| `sloth config init --interactive` | 交互式配置向导 |
| `sloth config show` | 查看当前配置 |
| `sloth config env` | 检查 API Key 状态 |
| `sloth init` | 初始化项目目录 |
| `sloth run --plan <file>` | 运行自主流水线 |
| `sloth chat` | 进入对话模式 |
| `sloth status` | 查看执行状态 |
| `sloth logs` | 查看执行日志 |
| `sloth uninstall` | 卸载 Sloth Agent |
| `sloth skills` | 查看/搜索/验证技能 |
| `sloth cost summary` | 查看花费汇总 |
| `sloth cost breakdown` | 按模型/Provider 分解花费 |

---

## 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                       CLI 入口 (typer)                        │
│                   sloth run | chat | status                   │
└─────────────────────────────┬────────────────────────────────┘
                              │
                              ▼
                ┌──────────────────────────┐
                │       Orchestrator       │
                │   Plan 解析 → 流水线调度  │
                └────────────┬─────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Builder Agent │  │ Reviewer Agent │  │ Deployer Agent │
│  deepseek      │→ │ qwen/claude    │→ │ deepseek       │
│  编码+调试     │  │ 审查+验证      │  │ 部署+验证      │
│  Reflection    │  │                │  │                │
└───────┬────────┘  └───────┬────────┘  └───────┬────────┘
        │ Gate 1            │ Gate 2            │ Gate 3
        │ lint+type         │ test+coverage     │ smoke-test
        └───────────────────┼───────────────────┘
                            ▼
              ┌──────────────────────────────┐
              │        共享基础设施           │
              ├──────┬───────┬──────┬────────┤
              │Tools │Skills │Memory│LLM     │
              │(CC   │(SKILL │(FS/  │Agent   │
              │对齐)  │.md)   │jsonl)│Registry│
              ├──────┴───────┴──────┴────────┤
              │ContextWindowManager          │
              │HallucinationGuard            │
              │StreamProcessor               │
              │Git Checkpoint (3-level)      │
              └──────────────────────────────┘
```

---

## 文档

### 架构与规格

| 模块 | 文档 | 状态 |
|------|------|------|
| 总体架构 | [architecture-overview](docs/specs/00000000-00-architecture-overview.md) | ✅ 含路线图 |
| #01 Phase-Role Arch | [spec](docs/specs/20260416-01-phase-role-architecture-spec.md) | ✅ Runner/NextStep 已实现 |
| #02 Tools Invocation | [spec](docs/specs/20260416-02-tools-invocation-spec.md) | ✅ ToolRegistry/Executor 已实现 |
| #04 Memory Management | [spec](docs/specs/20260416-04-memory-management-spec.md) | ✅ FS MemoryStore 已实现 |
| #06 Skill Management | [spec](docs/specs/20260416-06-skill-management-spec.md) | ✅ SKILL.md 加载已实现 |
| #13 Session Lifecycle | [spec](docs/specs/20260416-13-session-lifecycle-spec.md) | ✅ Git Checkpoint 已实现 |
| #20 LLM Routing | [spec](docs/specs/20260417-20-llm-router-spec.md) | ✅ LLMRouter 已实现 |
| #21 Eval Framework | [spec](docs/specs/20260417-21-eval-framework-spec.md) | ✅ smoke test 已实现 |
| #07 Chat Mode | [spec](docs/specs/20260416-07-chat-mode-spec.md) | ✅ REPL + 自主模式 + 技能触发 |
| #08 Observability | [spec](docs/specs/20260416-08-observability-logging-spec.md) | 🚧 待开发 |
| #09 Error Recovery | [spec](docs/specs/20260416-09-error-handling-recovery-spec.md) | 🚧 待开发 |
| #12 Cost & Budget | [spec](docs/specs/20260416-12-cost-budget-spec.md) | ✅ CostTracker + 预算限额 |
| #18 Installation | [spec](docs/specs/20260416-18-installation-onboarding-spec.md) | ✅ 安装脚本 + 卸载命令 + 配置向导 |

### 指南

| 文档 | 说明 |
|------|------|
| [安装指南](docs/guides/20260417-v0.1-installation-guide.md) | 安装、配置向导、快速开始、常见问题 |

---

*Sloth Agent v0.3.6*
*最后更新: 2026-04-22*
