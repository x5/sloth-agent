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
> **v0.1 已发布** — 3-Agent 自主流水线 MVP，189 tests pass。
> [查看 Release](https://github.com/x5/sloth-agent/releases/tag/v0.1) · [安装指南](docs/guides/20260417-v0.1-installation-guide.md)

---

## 产品定位

Sloth Agent 是一个**产品级的 AI 开发助手**，可理解为 OpenClaw + Hermes Agent 的组合体，借鉴 Claude Code 和 Codex 的最佳实践，并针对中国开发者生态进行深度定制。

v0.1 聚焦于 **Plan → 全自主开发 → 部署** 的核心场景：输入一份已完成的 Plan，全自主执行编码、审查、部署，关键节点由自动门控把关质量。

---

## 核心特性

### v0.1：3-Agent 串行流水线

```
Plan ─→ [Builder Agent] ─→ Gate 1 ─→ [Reviewer Agent] ─→ Gate 2 ─→ [Deployer Agent] ─→ Gate 3 ─→ Done
         deepseek            lint      qwen/claude        test      deepseek            smoke
         + reasoner          type      代码审查+质量验证   coverage   部署+验证            test
         编码+调试+测试
```

| Agent | 推荐模型 | 职责 | 上下文量级 |
|-------|---------|------|-----------|
| **Builder** | deepseek-v3.2（编码）/ deepseek-r1-0528（调试） | Plan 解析、编码、调试、单元测试 | ~50-60K tokens |
| **Reviewer** | qwen3.6-plus 或 claude | 独立审查 Builder 产出（**必须使用不同模型**） | ~10-15K tokens |
| **Deployer** | deepseek-v3.2 | 执行部署脚本、smoke test、验证上线 | ~3-5K tokens |

核心设计：
- **Reviewer 必须使用不同于 Builder 的 LLM**（同一模型审自己的代码几乎无价值）
- **Agent 间通过结构化 Pydantic 模型交接**（git diff、pytest 输出、覆盖率数字，非 LLM 摘要）
- **自动门控**取代人工审批（lint / type-check / test / coverage / smoke-test）

### v0.1 内置能力

| 能力 | 状态 | 说明 |
|------|------|------|
| **Runtime Kernel** | ✅ | 单一 Runner 内核 + RunState + NextStep 协议 |
| **Reflection + Stuck Detection** | ✅ | 执行失败自动反思，检测重复错误模式并切换策略 |
| **Adaptive Planning** | ✅ | 执行中发现 plan 假设不成立时自动触发 replan |
| **Code Understanding** | ✅ | tree-sitter 解析代码结构，精准定位修改范围 |
| **Tool-Use Learning** | ✅ | 记录工具调用成功率，自动优化参数和选择 |
| **Context Window Manager** | ✅ | 滑动窗口 + 工具结果压缩，三层上下文边界 |
| **Hallucination Guard** | ✅ | 路径存在性验证 + 命令白名单 + import 模式检查 |
| **Streaming** | ✅ | StreamProcessor: text/tool_call 交织处理 + CLI 实时渲染 |
| **Git Checkpoint** | ✅ | 3 级检查点（task/stage/session），门控失败自动回滚 |
| **Structured Handoff** | ✅ | BuilderOutput / ReviewerOutput / DeployResult 交接协议 |
| **Skill Loading** | ✅ | SKILL.md 加载与按需注入（Claude Code 兼容格式） |
| **Memory Store** | ✅ | 纯文件系统 jsonl 存储（sessions/scenarios/shared） |
| **LLM Router** | ✅ | 阶段级模型路由配置 |
| **Eval Framework** | ✅ | smoke test + 标准任务集，189 tests pass |

### 远期目标：8+1 Agent 架构（v0.5~v1.0）

| Agent 角色 | 所属 Phase | 推荐模型 |
|-----------|-----------|---------|
| **Analyst** | 需求分析 | qwen3.6-plus |
| **Planner** | 计划制定 | qwen3-max |
| **Engineer** | 编码实现 | deepseek-v3.2 |
| **Debugger** | 调试排错 | deepseek-r1-0528 |
| **Reviewer** | 代码审查 | glm-5.1 / claude-sonnet |
| **QA** | 质量验证 | glm-5.1 / claude-sonnet |
| **Release** | 发布上线 | deepseek-v3.2 |
| **Monitor** | 上线监控 | qwen3.5-plus |
| **General** | 无（通用） | 可配置 |

8+1 Agent 扩展后支持并行执行、上下文隔离、角色专业化、多场景编排。

### 工作模式演进

| 版本 | 模式 | 说明 |
|------|------|------|
| v0.1 | 自主模式 | 输入 Plan，全自主执行 3-Agent 流水线 |
| v0.2 | + 对话模式 | REPL 交互，技能触发，工作流控制 |
| v0.3 | + 可观测性 | 结构化日志 + Trace ID + 错误恢复 |
| v0.5 | + 多 Agent 并行 | 知识库 + 事件总线 + Speculative Execution |
| v0.8 | + 昼夜循环 | Persistent Daemon 常驻，夜间分析→日间执行 |
| v1.0 | 完整架构 | 8+1 Agent + 37 技能 + 8 场景编排 |

---

## 设计原则

| 原则 | v0.1 | 远期（v0.5+） |
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

| 特性 | OpenClaw | Hermes | Claude Code | Codex | **Sloth v0.1** |
|------|----------|--------|-------------|-------|----------------|
| 多 Agent 架构 | ❌ | ✅ 子代理 | ❌ | ❌ | ✅ **3-Agent Pipeline** |
| 自动门控 | ❌ | ❌ | ❌ | ❌ | ✅ **lint/type/test/smoke** |
| Reflection | 部分 | ❌ | 部分 | ❌ | ✅ **Stuck Detection** |
| 技能系统 | ✅ | ✅ | ✅ | ❌ | ✅ SKILL.md (兼容) |
| 代码理解 | ❌ | ✅ | 部分 | ❌ | ✅ **tree-sitter** |
| 安全防护 | ✅ | ✅ | Risk levels | Risk | ✅ **幻觉防护 + 白名单** |
| 模型路由 | ✅ | ✅ | ❌ | ❌ | ✅ **Stage 级路由** |
| 自动回滚 | ❌ | ❌ | ❌ | ❌ | ✅ **3 级 Git Checkpoint** |
| 成本控制 | ❌ | ❌ | ❌ | ❌ | 🚧 v0.2 |
| 中国生态 | ❌ | ❌ | ❌ | ❌ | ✅ **DeepSeek/Qwen/Kimi** |

**v0.1 差异化**：3-Agent 自动流水线 + Reflection 自纠错 + Stage 级模型路由 + 中国 LLM 原生支持。

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

v0.1 需配置 DeepSeek + Qwen 即可跑通。自动降级将在 v0.2 实现。

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
git clone git@github.com:x5/sloth-agent.git
cd sloth-agent
uv sync --dev
uv run sloth --help
```

### Windows (PowerShell)

```powershell
iwr -useb https://raw.githubusercontent.com/x5/sloth-agent/main/scripts/install.ps1 | iex
```

或手动安装：

```powershell
git clone git@github.com:x5/sloth-agent.git $HOME\sloth-agent
cd sloth-agent
uv sync --dev
uv run sloth --help
```

### 验证安装

```bash
# 查看帮助
uv run sloth --help

# 运行测试（189 tests）
uv run pytest tests/ evals/ -v

# Smoke test
uv run python -c "from evals.smoke_test import run_smoke_test; r = run_smoke_test(); print(f'PASS' if r.passed else 'FAIL')"
```

详细安装步骤见 [v0.1 安装指南](docs/guides/20260417-v0.1-installation-guide.md)。

---

## 快速开始

```bash
# 1. 准备一份 Plan 文件（Markdown 格式）

# 2. 执行自主流水线
uv run sloth run --plan plan.md

# 3. 查看执行状态
uv run sloth status

# 4. 查看日志
uv run sloth logs --level INFO --limit 50
```

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

| 模块 | 文档 | v0.1 状态 |
|------|------|-----------|
| 总体架构 | [architecture-overview](docs/specs/00000000-00-architecture-overview.md) | ✅ 含 v0.1~v1.0 路线图 |
| #01 Phase-Role Arch | [spec](docs/specs/20260416-01-phase-role-architecture-spec.md) | ✅ Runner/NextStep 已实现 |
| #02 Tools Invocation | [spec](docs/specs/20260416-02-tools-invocation-spec.md) | ✅ ToolRegistry/Executor 已实现 |
| #04 Memory Management | [spec](docs/specs/20260416-04-memory-management-spec.md) | ✅ FS MemoryStore 已实现 |
| #06 Skill Management | [spec](docs/specs/20260416-06-skill-management-spec.md) | ✅ SKILL.md 加载已实现 |
| #13 Session Lifecycle | [spec](docs/specs/20260416-13-session-lifecycle-spec.md) | ✅ Git Checkpoint 已实现 |
| #20 LLM Routing | [spec](docs/specs/20260417-20-llm-router-spec.md) | ✅ LLMRouter 已实现 |
| #21 Eval Framework | [spec](docs/specs/20260417-21-eval-framework-spec.md) | ✅ smoke test 已实现 |
| #07 Chat Mode | [spec](docs/specs/20260416-07-chat-mode-spec.md) | 🚧 v0.2 |
| #08 Observability | [spec](docs/specs/20260416-08-observability-logging-spec.md) | 🚧 v0.3 |
| #09 Error Recovery | [spec](docs/specs/20260416-09-error-handling-recovery-spec.md) | 🚧 v0.3 |
| #12 Cost & Budget | [spec](docs/specs/20260416-12-cost-budget-spec.md) | 🚧 v0.2 |

### 指南

| 文档 | 说明 |
|------|------|
| [v0.1 安装指南](docs/guides/20260417-v0.1-installation-guide.md) | 安装、配置、快速开始、常见问题 |

---

*Sloth Agent v0.1*
*最后更新: 2026-04-17*
*189 tests pass*
