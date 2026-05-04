# 架构总览

> 归档参考: archive/initial-specs/00000000-00-architecture-overview.md
> 最后更新: 2026-05-04
> Scope: Core（跨 CLI/Desktop 的总规）

## 产品定位

Sloth Agent — 一站式自主开发智能 Agent。输入一份 Plan，输出已开发、测试通过、部署上线的完整项目。

核心流水线：`Plan → Builder → Gate1 → Reviewer → Gate2 → Deployer → Gate3 → Done`

## 技术栈

| 层 | 技术 |
|---|------|
| 核心运行时 (CLI) | Python 3.10+, typer, pydantic |
| 后端 Sidecar | Python 3.12+, FastAPI, SQLAlchemy async, aiosqlite |
| 前端 | React 18, TypeScript, Vite, Zustand |
| 桌面壳 | Tauri v2 (Rust) |
| 数据库 | SQLite (sloth.db / agent.db) |
| 向量存储 | ChromaDB |
| LLM | OpenAI/Anthropic 双格式，多 Provider 路由 |

## 设计原则

- **3-Agent 串行流水线**（v1.0）：Builder → Reviewer → Deployer
- **工具优先**：Agent 通过工具层执行操作，所有操作可审计
- **技能即指令**：SKILL.md prompt 模板，运行时注入，兼容 Claude Code
- **文件系统即真相**：JSON/jsonl 存储，可回溯、可手动编辑
- **质量保障**：3 道自动门控（lint/type → test/coverage → smoke test）
- **自适应重规划**：门控失败时触发 replan，最多 N 次重试
- **上下文优先**：Context Engine 作为共享运行时能力，统一服务 Chat、Brainstorm、Autonomous 等执行模式
- **复用即 Core**：凡是可被 CLI/Desktop 复用的能力，一律归 Core；CLI/Desktop 仅保留 adapter 与端侧集成

## 新功能准入门禁（必须）

每个新功能在进入实现前，必须完成以下三问：

1. 既有 CLI 组件是否可直接复用？
2. 若可复用，是否已从 CLI 实现上提为 Core（而非继续标注为 CLI）？
3. 若必须端侧专有，专有边界和回收为 Core 的条件是什么？

交付要求：
- 在对应 change 的 `proposal.md` 中显式记录三问结论。
- 在对应 `tasks.md` 中增加一条“Core 抽象或复用”任务。
- 若选择端侧专有实现，必须写明回收路径（何时、如何合并回 Core）。

## 系统全景

```
CLI 入口 (sloth run)
     │
     ▼
Orchestrator (Plan 解析 → 流水线调度)
     │
     ├── Builder Agent  → Gate1 (lint/type)
     ├── Reviewer Agent → Gate2 (test/coverage)
     └── Deployer Agent → Gate3 (smoke test)
```

同时有一套独立的桌面应用（Tauri + React + FastAPI），支持 Inspiration 管理、Agent Pool、团队对话、Brainstorm 模式。

## 共享上下文引擎

Context Engine 是跨模式共享的核心模块，不归属于单一业务流（例如 Brainstorm）。

- 职责：在 token 预算内构建可发送给 LLM 的上下文，并保护关键消息链路。
- 输入：会话消息、工具结果、模式参数（chat/brainstorm/autonomous）、预算配置。
- 输出：ModelVisibleContext（可发送）与 RuntimeOnlyContext（仅运行时保留）。
- 接入：Iter-7 先由 Brainstorm 首轮接入，Chat 与 Autonomous 后续复用同一引擎。

与其他模块关系：
- Memory：存储原始消息、摘要与工具结果引用。
- Session：提供 run_id/session_id 生命周期与恢复锚点。
- Observability：记录 token 预算利用率、压缩率、截断率、上下文构建耗时。
- Daemon：在后台/断线恢复场景中恢复上下文快照并继续执行。

## 共享核心层（Shared Core）

`src/sloth_agent/` 中的纯逻辑模块同时服务于 CLI 和 Desktop（backend）。  
**判定原则**：不依赖 CLI 入口（typer/RunState）、不依赖 FastAPI/SQLAlchemy 的模块为"共享安全（shared-safe）"。

### 共享安全模块（backend 可直接 import）

| 模块路径 | 能力 | CLI 状态 | Desktop 应用方式 |
|----------|------|----------|-----------------|
| `sloth_agent.core.token_counter.TokenCounter` | tiktoken + 字符回退的 token 计数 | ✅ 已有 | 直接 import，不重建 |
| `sloth_agent.core.context_window.ContextWindowManager` | token 预算截断 + 摘要压缩 + 关键消息保护 | ✅ 已有 | 继承/扩展为 `ContextEngine`，不重建 |
| `sloth_agent.providers.llm_providers.BaseLLMProvider` | LLM 抽象基类 + `LLMMessage` / `LLMResponse` | ✅ 已有 | `LLMService` 包装，不重写 httpx 调用 |
| `sloth_agent.providers.llm_providers.*Provider` | DeepSeek / GLM / Ollama 等具体实现 | ✅ 已有 | 直接复用，DB config 仅做注入 |
| `sloth_agent.providers.llm_router.LLMRouter` | 按 agent 路由 + 熔断回退 | ✅ 已有 | Desktop 按需接入，补 DB config 注入适配 |

### 接入规则

1. `backend/pyproject.toml` 添加 path dependency：
   ```
   "sloth-agent @ file:///../"
   ```
2. Backend 只 import 上表列出的共享安全模块，禁止 import `sloth_agent.cli.*`、`sloth_agent.core.runner`、`sloth_agent.core.orchestrator` 等 CLI 专属模块。
3. 共享模块变更需在 `backend/tests/` 中同步测试。

### 适配层原则（backend/app/shared/）

Desktop 特有的关注点（DB config 注入、SSE 推送、FastAPI 生命周期）封装在 `backend/app/shared/` 的薄适配层，不写入共享模块：

```
backend/app/
  shared/
    llm_adapter.py     # 从 DB 读 LLMConfig → 构造 BaseLLMProvider 实例
    context_adapter.py # 包装 ContextWindowManager → mode=brainstorm/chat 适配
```

### Iter 演进与重复出现问题的根源

| Iter | 本应共享的模块 | 当前状态 | 修复方向 |
|------|---------------|----------|---------|
| Iter-4 | LLM Provider（httpx 调用逻辑） | `backend/services/llm.py` 重写了完整 httpx 调用 | 用 `llm_adapter.py` 包装 `BaseLLMProvider`，删除重复 httpx 代码 |
| Iter-7 | ContextWindowManager → ContextEngine | 计划重建 `core/context_engine.py` | 改为扩展 `ContextWindowManager`，补充 mode 参数 + diagnostics |
| Iter-7 | TokenCounter | Desktop 未使用 | `context_engine.py` 直接 import，不重建 |

## Spec 分层治理

### 分类规则

- `Core`：算法、协议、数据契约、策略逻辑，可被 CLI/Desktop 共同复用。
- `CLI`：仅命令行运行时相关（runner loop、runstate、hooks、orchestrator、terminal UX）。
- `Desktop`：仅桌面 sidecar / frontend / tauri 相关（SSE、DB 注入、UI 交互、会话面板）。

Scope 判定规则：
- **目录位置即 Scope**：`core/` 下的 spec 即为 Core，`cli/` 即 CLI，`desktop/` 即 Desktop，无需另行标注。
- 若能力可被 CLI 和 Desktop 复用，归入 `core/`，不得拆分。
- Desktop/CLI 的适配细节写在各自目录，不污染 Core spec。

### 目录结构

```
docs/specs/
  architecture/
    spec.md               <- 本文件：治理规则 + 全局索引
  core/                   <- 跨端可复用能力（18 个领域）
    context/spec.md
    llm/spec.md
    memory/spec.md
    session/spec.md
    chat/spec.md
    brainstorm/spec.md
    events/spec.md
    observability/spec.md
    knowledge/spec.md
    reports/spec.md
    notifications/spec.md
    feishu/spec.md
    coordination/spec.md
    skills/spec.md
    tools/spec.md
    errors/spec.md
    cost/spec.md
    sandbox/spec.md
  cli/                    <- CLI 专有能力（3 个领域）
    runtime/spec.md
    eval/spec.md
    onboarding/spec.md
  desktop/                <- Desktop 专有能力 + Core 适配层
    app/spec.md           <- 桌面产品面与 UI 行为
    daemon/spec.md        <- sidecar 守护与健康检查
    adapters/
      tools.md            <- Desktop Tool 装饰器系统（Core tools 的 Desktop 实现）
      context.md          <- ContextEngine 适配（Iter-7，待补充）
      llm.md              <- LLM adapter（Iter-7，待补充）
```

### 新功能 Spec 归属决策

新增功能 spec 时，先回答：
1. 该能力能否被 CLI 和 Desktop 同时使用？→ `core/`
2. 仅在 CLI 运行时需要？→ `cli/`
3. 仅在 Desktop sidecar/frontend 需要？→ `desktop/`
4. 是 Core 能力对某端的适配细节？→ `desktop/adapters/` 或 `cli/` 中的专属文件

### 完整归属索引

| Spec | 路径 | 说明 |
|------|------|------|
| 上下文引擎 | `core/context/spec.md` | Desktop 首接入，CLI 后续接入 |
| 记忆管理 | `core/memory/spec.md` | CLI/desktop 均消费同一契约 |
| 会话生命周期 | `core/session/spec.md` | CLI/desktop 会话实现按此契约适配 |
| LLM 路由 | `core/llm/spec.md` | CLI provider 与 desktop `llm_adapter` 对齐 |
| 事件总线 | `core/events/spec.md` | Hook/Bus 作为端侧事件桥接基础 |
| 可观测性 | `core/observability/spec.md` | CLI 与 desktop 分别上报实现 |
| 知识库 | `core/knowledge/spec.md` | CLI/desktop 检索入口适配 |
| 报告 | `core/reports/spec.md` | 输出渠道由端侧决定 |
| 通知 | `core/notifications/spec.md` | 渠道接入由 adapter 决定 |
| Feishu 集成 | `core/feishu/spec.md` | 作为通知渠道 adapter |
| 协调编排 | `core/coordination/spec.md` | CLI/desktop 协调编排可复用 |
| 技能管理 | `core/skills/spec.md` | 注入入口端侧适配 |
| 工具系统 | `core/tools/spec.md` | CLI/desktop 各自工具执行器适配 |
| Brainstorm | `core/brainstorm/spec.md` | Desktop 首发 adapter，CLI adapter 后续实现 |
| 对话模式 | `core/chat/spec.md` | CLI REPL 与 desktop Chat UI 适配 |
| 错误恢复 | `core/errors/spec.md` | CLI runner 与 desktop sidecar 统一恢复语义 |
| 成本追踪 | `core/cost/spec.md` | CLI 命令/UI 展示均为 adapter |
| 沙箱 | `core/sandbox/spec.md` | desktop 先落地，CLI 可复用策略层 |
| CLI 运行时 | `cli/runtime/spec.md` | CLI 主循环状态机专有 |
| 评测框架 | `cli/eval/spec.md` | 当前评测执行器在 CLI |
| 初始化引导 | `cli/onboarding/spec.md` | CLI 安装与初始化专有 |
| 桌面应用 | `desktop/app/spec.md` | 桌面产品面与 UI 行为专有 |
| Sidecar 守护 | `desktop/daemon/spec.md` | sidecar 健康检查与重启策略 |
| Desktop Tool 适配 | `desktop/adapters/tools.md` | Desktop Tool 装饰器系统实现细节 |

---

## 代码目录结构

```
agent-evolve/
├── src/sloth_agent/     # 核心运行时（含共享安全模块）
│   ├── core/            # Runner, Orchestrator, Builder, Gates
│   │   ├── token_counter.py    # ← SHARED-SAFE
│   │   └── context_window.py   # ← SHARED-SAFE（Desktop 扩展为 ContextEngine）
│   ├── agents/          # Agent 定义与注册
│   ├── tools/           # Tool 调用、编排、风险门控
│   ├── memory/          # 记忆存储、技能管理
│   ├── providers/       # LLM Provider 路由
│   │   ├── llm_providers.py    # ← SHARED-SAFE
│   │   └── llm_router.py       # ← SHARED-SAFE
│   ├── chat/            # REPL、对话会话
│   ├── cost/            # 成本追踪
│   ├── errors/          # 熔断、错误恢复
│   └── cli/             # CLI 入口（非共享）
├── backend/             # FastAPI Sidecar
│   └── app/
│       └── shared/      # 薄适配层（DB 注入 + 模式适配）
│           ├── llm_adapter.py      # ← Desktop LLM 接入点
│           └── context_adapter.py  # ← Desktop Context 接入点
├── frontend/            # React + Tauri 桌面应用
├── skills/              # SKILL.md 技能定义
├── configs/             # YAML 配置
└── docs/
    ├── specs/           # Spec 源头（Layer-first 结构）
    │   ├── architecture/ # 治理规则 + 全局索引
    │   ├── core/        # 跨端可复用能力（18 个领域）
    │   ├── cli/         # CLI 专有能力（3 个领域）
    │   └── desktop/     # Desktop 专有能力 + adapters
    ├── changes/         # 进行中的 Delta 变更
    ├── archive/         # 历史归档
    └── plans/           # 实现计划
```
      llm.md              <- LLM adapter（Iter-7，待补充）
```

### 新功能 Spec 归属决策

新增功能 spec 时，先回答：
1. 该能力能否被 CLI 和 Desktop 同时使用？ `core/`
2. 仅在 CLI 运行时需要？ `cli/`
3. 仅在 Desktop sidecar/frontend 需要？ `desktop/`
4. 是 Core 能力对某端的适配细节？ `desktop/adapters/` 或 `cli/` 中的专属文件

### 完整归属索引

| Spec | 路径 | 说明 |
|------|------|------|
| 上下文引擎 | `core/context/spec.md` | Desktop 首接入，CLI 后续接入 |
| 记忆管理 | `core/memory/spec.md` | CLI/desktop 均消费同一契约 |
| 会话生命周期 | `core/session/spec.md` | CLI/desktop 会话实现按此契约适配 |
| LLM 路由 | `core/llm/spec.md` | CLI provider 与 desktop `llm_adapter` 对齐 |
| 事件总线 | `core/events/spec.md` | Hook/Bus 作为端侧事件桥接基础 |
| 可观测性 | `core/observability/spec.md` | CLI 与 desktop 分别上报实现 |
| 知识库 | `core/knowledge/spec.md` | CLI/desktop 检索入口适配 |
| 报告 | `core/reports/spec.md` | 输出渠道由端侧决定 |
| 通知 | `core/notifications/spec.md` | 渠道接入由 adapter 决定 |
| Feishu 集成 | `core/feishu/spec.md` | 作为通知渠道 adapter |
| 协调编排 | `core/coordination/spec.md` | CLI/desktop 协调编排可复用 |
| 技能管理 | `core/skills/spec.md` | 注入入口端侧适配 |
| 工具系统 | `core/tools/spec.md` | CLI/desktop 各自工具执行器适配 |
| Brainstorm | `core/brainstorm/spec.md` | Desktop 首发 adapter，CLI adapter 后续实现 |
| 对话模式 | `core/chat/spec.md` | CLI REPL 与 desktop Chat UI 适配 |
| 错误恢复 | `core/errors/spec.md` | CLI runner 与 desktop sidecar 统一恢复语义 |
| 成本追踪 | `core/cost/spec.md` | CLI 命令/UI 展示均为 adapter |
| 沙箱 | `core/sandbox/spec.md` | desktop 先落地，CLI 可复用策略层 |
| CLI 运行时 | `cli/runtime/spec.md` | CLI 主循环状态机专有 |
| 评测框架 | `cli/eval/spec.md` | 当前评测执行器在 CLI |
| 初始化引导 | `cli/onboarding/spec.md` | CLI 安装与初始化专有 |
| 桌面应用 | `desktop/app/spec.md` | 桌面产品面与 UI 行为专有 |
| Sidecar 守护 | `desktop/daemon/spec.md` | sidecar 健康检查与重启策略 |
| Desktop Tool 适配 | `desktop/adapters/tools.md` | Desktop Tool 装饰器系统实现细节 |

---



