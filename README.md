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

v1.0 聚焦于 **Plan → 全自主开发 → 部署** 的核心场景：输入一份已完成的 Plan，全自主执行编码、审查、部署，关键节点由自动门控把关质量。

---

## 核心特性

### v1.0：3-Agent 串行流水线

```
Plan ─→ [Builder Agent] ─→ Gate 1 ─→ [Reviewer Agent] ─→ Gate 2 ─→ [Deployer Agent] ─→ Gate 3 ─→ Done
         deepseek-chat       lint      qwen-max/claude      test      deepseek-chat       smoke
         + reasoner          type      代码审查+质量验证     coverage   部署+验证            test
         编码+调试+测试
```

| Agent | 推荐模型 | 职责 | 上下文量级 |
|-------|---------|------|-----------|
| **Builder** | deepseek-chat（编码）/ deepseek-reasoner（调试） | Plan 解析、编码、调试、单元测试 | ~50-60K tokens |
| **Reviewer** | qwen-max 或 claude | 独立审查 Builder 产出（**必须使用不同模型**） | ~10-15K tokens |
| **Deployer** | deepseek-chat | 执行部署脚本、smoke test、验证上线 | ~3-5K tokens |

核心设计：
- **Reviewer 必须使用不同于 Builder 的 LLM**（同一模型审自己的代码几乎无价值）
- **Agent 间通过结构化 Pydantic 模型交接**（git diff、pytest 输出、覆盖率数字，非 LLM 摘要）
- **自动门控**取代人工审批（lint / type-check / test / coverage / smoke-test）

### v1.0 内置能力

| 能力 | 说明 |
|------|------|
| **Reflection + Stuck Detection** | 执行失败自动反思，检测重复错误模式并切换策略 |
| **Adaptive Planning** | 执行中发现 plan 假设不成立时自动触发 replan |
| **Code Understanding** | tree-sitter 解析代码结构，精准定位修改范围 |
| **Tool-Use Learning** | 记录工具调用成功率，自动优化参数和选择 |
| **Context Window Manager** | 动态 token 分区（system/history/tools/generation），确定性压缩 |
| **Hallucination Guard** | 路径存在性验证 + 命令白名单 + import 模式检查 |
| **Streaming** | StreamProcessor: text/tool_call 交织处理 + CLI 实时渲染 |
| **Git Checkpoint** | 3 级检查点（task/stage/session），门控失败自动回滚 |

### 远期目标：8+1 Agent 架构（v2.0+）

| Agent 角色 | 所属 Phase | 推荐模型 |
|-----------|-----------|---------|
| **Analyst** | 需求分析 | qwen-plus |
| **Planner** | 计划制定 | qwen-max |
| **Engineer** | 编码实现 | deepseek-chat |
| **Debugger** | 调试排错 | deepseek-chat |
| **Reviewer** | 代码审查 | claude-sonnet |
| **QA** | 质量验证 | claude-sonnet |
| **Release** | 发布上线 | deepseek-chat |
| **Monitor** | 上线监控 | qwen-plus |
| **General** | 无（通用） | 可配置 |

8+1 Agent 扩展后支持并行执行、上下文隔离、角色专业化、多场景编排。

### 工作模式演进

| 版本 | 模式 | 说明 |
|------|------|------|
| v1.0 | 自主模式 | 输入 Plan，全自主执行 3-Agent 流水线 |
| v1.1+ | + 对话模式 | REPL 交互，技能触发，工作流控制 |
| v2.0+ | + 昼夜循环 | Persistent Daemon 常驻，夜间分析→日间执行 |

---

## 设计原则

| 原则 | v1.0 | 远期（v2.0+） |
|------|------|--------------|
| **Agent 架构** | 3-Agent 串行流水线 | 8+1 Agent 并行执行 |
| **工具优先** | Agent 通过工具层操作，可审计 | + Plugin 扩展 |
| **技能即指令** | SKILL.md prompt 模板，兼容 Claude Code | + 自动进化 |
| **存储** | 纯文件系统（jsonl） | + SQLite 索引 + ChromaDB 向量 |
| **质量保障** | 自动门控（lint/type/test/coverage/smoke） | + 事件驱动规则 |
| **模型路由** | Stage 级（deepseek→编码, qwen→审查） | Agent 级配置 + 降级 |
| **安全默认** | 路径白名单 + 命令黑名单 + 幻觉防护 | 5 层安全 + 沙箱 |
| **文件系统即真相** | JSON/jsonl，可回溯、可审计、可手动编辑 | 同左 |

---

## 与参考框架的对比

| 特性 | OpenClaw | Hermes | Claude Code | Codex | **Sloth v1.0** |
|------|----------|--------|-------------|-------|----------------|
| 多 Agent 架构 | ❌ | ✅ 子代理 | ❌ | ❌ | ✅ **3-Agent Pipeline** |
| 自动门控 | ❌ | ❌ | ❌ | ❌ | ✅ **lint/type/test/smoke** |
| Reflection | 部分 | ❌ | 部分 | ❌ | ✅ **Stuck Detection** |
| 技能系统 | ✅ | ✅ | ✅ | ❌ | ✅ SKILL.md (兼容) |
| 代码理解 | ❌ | ✅ | 部分 | ❌ | ✅ **tree-sitter** |
| 安全防护 | ✅ | ✅ | Risk levels | Risk | ✅ **幻觉防护 + 白名单** |
| 模型路由 | ✅ | ✅ | ❌ | ❌ | ✅ **Stage 级路由** |
| 自动回滚 | ❌ | ❌ | ❌ | ❌ | ✅ **3 级 Git Checkpoint** |
| 成本控制 | ❌ | ❌ | ❌ | ❌ | ✅ **Token Budget** |
| 中国生态 | ❌ | ❌ | ❌ | ❌ | ✅ **DeepSeek/Qwen/Kimi** |

**v1.0 差异化**：3-Agent 自动流水线 + Reflection 自纠错 + Stage 级模型路由 + 中国 LLM 原生支持。

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
# 初始化项目
sloth init --project ~/my-project

# 执行自主流水线（输入 plan 文件）
sloth run --plan plan.md

# 查看执行状态
sloth status

# 查看日志
sloth logs --level INFO --limit 50

# v1.1+ 对话模式
sloth chat
```

---

## 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                       CLI 入口 (typer)                        │
│                   sloth run | sloth init                      │
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
              │(CC   │(SKILL │(FS/  │Stage   │
              │对齐)  │.md)   │jsonl)│Route   │
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
*最后更新: 2026-04-16*
