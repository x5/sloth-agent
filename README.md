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

> [!IMPORTANT]
> 项目仍在开发中，代码尚未实现。当前阶段为架构设计与规格定义。

---

## 产品定位

Sloth Agent 是一个**产品级的 AI 开发助手**，可理解为 OpenClaw + Hermes Agent 的组合体，借鉴 Claude Code 和 Codex 的最佳实践，并针对中国开发者生态进行深度定制。

通过 **Phase-Role-Architecture**（阶段-角色-技能架构），将开发流程标准化为 8 个阶段，每个阶段由专门的 Agent 角色执行，可在需要时调用 37 个预定义技能。同时提供一个通用 Agent，可跨阶段自由调用任意技能，处理非结构化任务。

---

## 核心特性

### 8 + 1 Agent 架构

| Agent 角色 | 所属 Phase | 推荐模型 | 最大实例 |
|-----------|-----------|---------|---------|
| **Analyst** | 需求分析 | qwen-plus | 1 |
| **Planner** | 计划制定 | qwen-max | 1 |
| **Engineer** | 编码实现 | deepseek-chat | 3 |
| **Debugger** | 调试排错 | deepseek-chat | 2 |
| **Reviewer** | 代码审查 | claude-sonnet | 2 |
| **QA** | 质量验证 | claude-sonnet | 2 |
| **Release** | 发布上线 | deepseek-chat | 1 |
| **Monitor** | 上线监控 | qwen-plus | 1 |
| **General** | 无（通用） | 可配置 | 1 |

设置专用 Agent 而非单一 Agent 的原因：**并行执行**、**上下文隔离**、**角色专业化**、**模型优化**。

### 两种工作模式

- **自主模式**：昼夜循环，夜间半自主（需求分析→计划制定→人工审批），日间全自主（编码→审查→测试→发布），支持 Persistent Daemon 常驻运行
- **对话模式**：REPL 交互，自由对话、技能触发、工作流控制，可从对话中启停自主模式

### 8 个 Phase + 8 个场景

```
Phase 1 需求分析 → Phase 2 计划制定 → Phase 3 编码实现
  → Phase 4 调试排错 → Phase 5 代码审查 → Phase 6 质量验证
  → Phase 7 发布上线 → Phase 8 上线监控
```

| 场景 | Phase 序列 | 用途 |
|------|-----------|------|
| standard | 1→2→3→4→5→6→7→8 | 标准开发流程 |
| hotfix | 4→5→6→8 | 紧急修复 |
| review-only | 5→6→8 | 仅代码审查 |
| feature | 1→2→3→4→5→6 | 新功能开发（不含发布） |
| night-analysis | 1→2 | 夜间分析（需审批） |
| day-execute | 3→4→5→6→7→8 | 日间执行 |
| deploy | 7→8 | 仅发布 |
| monitor | 8 | 仅监控 |

---

## 设计原则

| 原则 | 说明 |
|------|------|
| **专用 Agent + 通用 Agent** | 8 个专职 Agent 保障并行能力和上下文隔离；1 个通用 Agent 处理自由形态请求 |
| **工具优先** | Agent 通过工具层执行操作，不直接写文件或跑命令，所有操作可审计 |
| **技能即指令** | SKILL.md 就是 prompt 模板，运行时注入，与 Claude Code 生态兼容 |
| **渐进式记忆** | 文件系统为主（可回溯、可审计、可手动编辑），SQLite 为索引层（可选），ChromaDB 为向量层（可选） |
| **场景即工作流** | 场景 = Phase 调用序列 + 门控条件，Phase 间通过摘要传递上下文 |
| **事件驱动** | 模块间通过发布-订阅事件总线通信，而非直接调用 |
| **安全默认** | 5 层安全防护，沙箱隔离，路径白名单，命令黑名单，资源限制 |
| **多模型支持** | 6 个 LLM Provider 自动切换 + 熔断降级 |
| **文件系统即真相** | 所有状态、对话、产出物以 JSON/jsonl 存储于文件系统，可手动编辑 |

---

## 与参考框架的对比

| 特性 | OpenClaw | Hermes | Claude Code | Codex | **Sloth Agent** |
|------|----------|--------|-------------|-------|----------------|
| 多 Agent 架构 | ❌ | ✅ 子代理 | ❌ | ❌ | ✅ **8 专用 + 1 通用** |
| 持久常驻 | ✅ | ✅ | ❌ | ❌ | ✅ Daemon + Watchdog |
| 技能系统 | ✅ | ✅ | ✅ | ❌ | ✅ SKILL.md (兼容) |
| 持久记忆 + 学习 | ✅ | ✅ | Session | Session | ✅ **FS + Learning** |
| 自进化能力 | ❌ | ✅ | 部分 | ❌ | ✅ 技能进化 |
| 安全沙箱 | ✅ | ✅ | Risk levels | Risk | ✅ **5 层安全** |
| 多模型支持 | ✅ | ✅ | ❌ | ❌ | ✅ **6 Provider** |
| 可观测性 | ✅ | ✅ | ❌ | ❌ | ✅ 日志 + Trace + 指标 |
| 工作流编排 | ✅ | ❌ | ❌ | ❌ | ✅ Phase + Scenario |
| 成本控制 | ❌ | ❌ | ❌ | ❌ | ✅ **预算 + 定价 + 预测** |
| 事件驱动 | ❌ | ❌ | ❌ | ❌ | ✅ Pub-Sub Bus |
| 中国生态 | ❌ | ❌ | ❌ | ❌ | ✅ **6 中国 Provider** |

**差异化优势**：多 Agent 并行 + 事件驱动 + 成本控制 + 中国 LLM 生态 + 技能自进化 + 工作流编排。

---

## 支持的 LLM Provider

| Provider | 模型 | 用途 |
|----------|------|------|
| **DeepSeek** | deepseek-chat, deepseek-reasoner | 主力编码模型 |
| **Qwen** | qwen-turbo, qwen-plus, qwen-max | 低成本到高性能全覆盖 |
| **Kimi** | moonshot-v1-8k/32k/128k | 中等到超长上下文 |
| **GLM** | glm-4 | 智谱 |
| **MiniMax** | minimax-pro | MiniMax |
| **Xiaomi** | mimo-v2 | 小米 |

自动降级：首选模型不可用时按 fallback 顺序切换，全部 Provider 不可用时队列等待 + 定期重试。连续失败 5 次触发熔断，5 分钟后尝试恢复。

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
curl -fsSL https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.sh | bash
```

或手动安装：

```bash
git clone git@github.com:x5/sloth-agent.git ~/.sloth-agent
cd ~/.sloth-agent
uv venv .venv && source .venv/bin/activate
uv pip install -e .
```

### Windows (PowerShell)

```powershell
iwr -useb https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.ps1 | iex
```

或手动安装：

```powershell
git clone git@github.com:x5/sloth-agent.git $HOME\.sloth-agent
cd $HOME\.sloth-agent
uv venv .venv
.venv\Scripts\Activate.ps1
uv pip install -e .
```

### 初始化

```bash
sloth init --project ~/my-project
```

---

## 快速开始

```bash
# 运行自主模式（昼夜循环）
sloth run

# 进入对话模式
sloth chat

# 常驻运行（Daemon 模式）
sloth daemon

# 查看状态
sloth status

# 查看可用技能
sloth skills

# 查看可用场景
sloth scenarios

# 查看日志
sloth logs --level INFO --limit 50

# 查询 Trace
sloth logs --trace sloth-nightly-20260416-phase-1

# 生成报告
sloth report --type daily
```

---

## 架构总览

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLI 入口 (typer)                                    │
│         sloth run | sloth chat | sloth daemon | sloth status | sloth install     │
└──────────┬──────────────────────────────────────────────┬────────────────────────┘
           │                                              │
           ▼                                              ▼
┌──────────────────────────┐            ┌─────────────────────────────────────────┐
│    AUTONOMOUS MODE       │            │              CHAT MODE                   │
│  昼夜循环 / Persistent    │            │         REPL 交互                        │
│  后台常驻 / 健康检查      │            │         技能触发 / 工作流控制             │
└──────────┬───────────────┘            └────────────┬────────────────────────────┘
           └──────────────────────┬──────────────────┘
                                  ▼
              ┌──────────────────────────────────────────────────────────┐
              │                    共享基础设施层                          │
              ├────────────┬────────────┬────────────┬───────────────────┤
              │PhaseReg    │SkillReg    │ToolReg     │MemoryStore        │
              │istry       │istry       │istry       │+ Index (SQLite)   │
              │8 Phase +   │37 skills   │+ Plugin    │+ Vector (ChromaDB)│
              │8 Scenarios │SKILL.md    │对齐 CC     │                   │
              └────────────┴────────────┴────────────┴───────────────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           ▼                      ▼                      ▼
┌──────────────────┐  ┌────────────────────┐  ┌──────────────────────────┐
│  横切能力层        │  │  事件驱动层         │  │  外部集成层               │
│ Observability    │  │  Event Bus         │  │ Feishu (webhook + card)  │
│ Error Recovery   │◄─┤  (pub/sub)         │  │ LLM Providers (6)        │
│ Report Generator │  │  Workflow Rules    │  │ Email (SMTP)             │
│ Cost Tracker     │  │  Dead Letter Queue │  │ Generic Webhook          │
│ Knowledge Base   │  │  Event Replay      │  │ Notification Channels    │
│ Security Sandbox │  │                    │  │                          │
└──────────────────┘  └────────────────────┘  └──────────────────────────┘
```

---

## 文档

### 架构与规格

| 文档 | 说明 |
|------|------|
| [总体架构](docs/specs/00000000-architecture-overview.md) | 15 模块架构总览、Agent 架构、数据流、配置模型 |
| [Phase-Role Architecture](docs/specs/20260416-phase-role-architecture-spec.md) | 8 专职 Agent + 1 通用 Agent、8 阶段、37 技能 |
| [Tools Invocation](docs/specs/20260416-tools-invocation-spec.md) | 4 层调用链（Intent→Risk→Execute→Format）、Plugin 架构 |
| [Multi-Agent Coordination](docs/specs/20260416-multi-agent-coordination-spec.md) | 任务分发、Worktree 隔离、结果合并、冲突解决 |
| [Memory Management](docs/specs/20260416-memory-management-spec.md) | 三层记忆（FS 主 + SQLite 索引 + ChromaDB 向量） |
| [Session Management](docs/specs/20260416-session-management-spec.md) | 会话生命周期、checkpoint、摘要传递 |
| [Skill Management](docs/specs/20260416-skill-management-spec.md) | SKILL.md 加载、路由匹配、自动进化 |
| [Chat Mode](docs/specs/20260416-chat-mode-spec.md) | REPL 交互、斜杠命令、上下文管理 |
| [Observability & Logging](docs/specs/20260416-observability-logging-spec.md) | 统一日志、Trace ID、查询 CLI、健康诊断 |
| [Error Handling & Recovery](docs/specs/20260416-error-handling-recovery-spec.md) | 4 级错误分类、熔断器、优雅降级、人工介入 |
| [Report Generation](docs/specs/20260416-report-generation-spec.md) | 7 种报告类型、模板引擎、多渠道交付 |
| [Notification & Integration](docs/specs/20260416-notification-integration-spec.md) | 飞书/邮件/Webhook 适配器、通知路由、去重限流 |
| [Cost & Budget](docs/specs/20260416-cost-budget-spec.md) | 6 Provider 定价、预算软硬停机、费用预测 |
| [Session Lifecycle](docs/specs/20260416-session-lifecycle-spec.md) | 会话创建/暂停/恢复、分支映射、序列化 |
| [Event System](docs/specs/20260416-event-system-spec.md) | 发布-订阅事件总线、工作流触发、死信队列 |
| [Knowledge Base](docs/specs/20260416-knowledge-base-spec.md) | 项目上下文、代码库摘要、语义检索 |
| [Daemon & Health](docs/specs/20260416-daemon-health-spec.md) | Persistent Daemon、心跳检查、看门狗 |
| [Sandbox Security](docs/specs/20260416-sandbox-security-spec.md) | 5 层安全、路径白名单、资源限制 |

### 指南

| 文档 | 说明 |
|------|------|
| [用户手册](docs/guides/20260415-sloth-agent-user-guide.md) | 功能介绍和使用方法 |

---

*规格版本: v2.0.0*
*创建日期: 2026-04-16*
