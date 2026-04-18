# Chat Mode 设计规格

> 版本: v1.3.0
> 日期: 2026-04-18
> 状态: 已实现 (v0.2)

---

## 1. 需求描述

### 1.1 问题

Sloth Agent 目前只有半自主模式（日/夜循环），用户无法与 Agent 进行实时交互式对话。需要支持 chat 模式，让用户可以：

- 自由提问、讨论代码或架构
- 手动触发单个技能处理简单任务（如 `/skill review` 审查代码）
- 查看可用技能和场景
- 启动/中止自主模式
- 通过飞书进行对话（webhook 通道）

### 1.2 目标

| 版本 | 能力 | 说明 |
|------|------|------|
| **v1.0** | 自由对话 + 上下文管理 | REPL 交互，消息历史，基础斜杠命令 |
| **v1.1** | 技能触发 + 自主模式控制 | `/skill <name>` 处理任务，`/start autonomous` 控制自主模式 |
| **v1.2** | Phase 触发 + 飞书集成 | `/run <scenario>` 执行工作流，飞书 webhook 对话 |
| **v1.3** | CLI 友好化 | 启动欢迎屏、自然语言帮助、中文优先、结构化输出、确认卡片、进度可视化 |

**v1.0 范围：**
- `sloth chat` 命令进入交互 REPL
- 自由对话，LLM 响应
- 消息历史截断管理
- 斜杠命令：`/clear`, `/context`, `/help`, `/quit`
- 复用现有 LLM providers

**v1.1 范围：**
- `/skill <name>` 触发单个技能
- `/start autonomous` 启动自主模式
- `/stop` 中止自主模式
- `/status` 查看自主模式状态
- 工具调用（LLM 决定，用户确认）

**v1.2 范围：**
- `/run <scenario>` 触发工作流场景
- Phase 切换时的上下文衔接
- 飞书 webhook server
- 对话持久化

### 1.3 约束

- 不影响现有自主模式代码
- 最小依赖，不引入重量级 REPL 库
- 所有对话记录可回溯

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLI 入口 (typer)                           │
│                     sloth_agent/__main__.py                       │
│               app: run / chat / status / skills                   │
└───────────┬───────────────────────────────┬─────────────────────┘
            │                               │
            ▼                               ▼
┌────────────────────────┐  ┌─────────────────────────────────────┐
│   AUTONOMOUS MODE       │  │           CHAT MODE                  │
│   AgentEvolve.run()     │  │       ChatSession.loop()             │
│   (半自主，可被控制)      │  │       (新增)                        │
└───────────┬────────────┘  └──────────────┬──────────────────────┘
            │                              │
            │     ┌────────────────────────┼──────────────────┐
            │     ▼                        ▼                  ▼
            │ ┌──────────┐    ┌──────────────┐    ┌──────────────┐
            │ │LLMProvider│   │Conversation  │    │SessionManager│
            │ │Manager    │   │Context       │    │(新增)        │
            │ │(现有)     │   │(新增)        │    │              │
            │ └──────────┘    └──────────────┘    └──────────────┘
            │                                          │
            └──────────────────┬───────────────────────┘
                               ▼
              ┌────────────────────────────────────┐
              │           MEMORY LAYER              │
              │  ┌──────────┐  ┌────────────────┐  │
              │  │sessions/ │  │scenarios/      │  │
              │  │(chat +   │  │(phase data     │  │
              │  │ metadata)│  │ + phase chat)  │  │
              │  └──────────┘  └────────────────┘  │
              └────────────────────────────────────┘
```

### 2.2 设计原则

1. **独立执行路径**：Chat mode 是 `AgentEvolve` 的平行入口，不修改现有自主模式
2. **共享基础设施**：复用 `LLMProviderManager`、`ToolRegistry`、`MemoryRetrieval`、`SkillRegistry`
3. **分阶段交付**：v1.0 最小可用，v1.1 技能 + 控制，v1.2 工作流 + 飞书
4. **typer CLI**：用 typer 管理子命令（已有 pydantic，typer 自然集成）

---

## 3. 模块定义

### 3.1 CLI 入口

**文件**: `src/cli/app.py`

| 命令 | 说明 | 参数 |
|------|------|------|
| `sloth` (无参数) | 默认：自主模式（现有行为） | — |
| `sloth run` | 自主模式 | `--phase night|day` |
| `sloth chat` | 交互对话 | `--model`, `--provider` |
| `sloth status` | 显示状态 | `--project` |
| `sloth skills [name]` | 列出/查看技能 | `name` (可选) |
| `sloth scenarios` | 列出场景 | — |

### 3.2 Chat REPL

**文件**: `src/cli/chat.py`

```
职责: ChatSession 类，管理 REPL 循环
```

**核心流程**:
```
while True:
  1. 显示提示符 "sloth> "
  2. 读取用户输入
  3. 如果是 "/" 开头 → 处理斜杠命令
  4. 否则 → SessionManager.save(user_input) → 发送到 LLM → 显示响应
  5. 将对话追加到上下文
```

### 3.3 对话上下文

**文件**: `src/cli/context.py`

```
职责: ConversationContext 类，管理活跃消息窗口
```

**核心能力**:
- 添加消息（user / assistant / system）
- 获取消息列表（格式化给 LLM API）
- 截断旧消息（保留最近 N 轮）
- 清空对话（`/clear`）
- 显示摘要（`/context`）

**截断策略**: 保留最近 `max_turns` 轮（默认 20），超出部分直接丢弃。首轮不做 LLM 压缩，后续按需增加。

### 3.4 Session Manager

**文件**: `src/memory/session.py`

```
职责: SessionManager 类，管理 session 生命周期和 memory 存储
```

**三层 Memory 结构**:

```
memory/
├── sessions/                              # 会话层
│   └── {session_id}/
│       ├── chat.jsonl                     # 所有对话记录（时间序，含自由对话和 phase 对话）
│       ├── context.json                   # 当前上下文（活跃对话摘要）
│       └── metadata.json                  # session 元信息
│
├── scenarios/                             # 场景层（Phase-Role-Architecture）
│   └── {scenario_id}/
│       ├── phase-1/
│       │   ├── input.json                 # phase 输入数据
│       │   ├── output.json                # phase 输出数据
│       │   ├── chat.jsonl                 # 该 phase 执行时的对话记录
│       │   └── artifacts/                 # phase 产生的文件
│       └── phase-2/
│           └── ...
│
└── shared/                                # 共享层（跨 session 知识）
    ├── skills/                            # 技能进化记录
    └── knowledge/                         # 长期学习成果
```

**Session 生命周期**:

| 事件 | 操作 |
|------|------|
| `sloth chat` 启动 | 创建新 session，生成 session_id，写入 `metadata.json` |
| 用户发送消息 | 追加到 `chat.jsonl`，更新 `context.json` |
| `/run standard` 触发场景 | 在 `scenarios/standard/` 下创建 phase 目录，写入 phase 对话 |
| Phase 切换 | 1. 保存当前对话摘要到 phase `output.json`<br>2. 加载新 phase 配置<br>3. 切换 LLM<br>4. 注入 phase 系统提示 + 前序摘要 |
| `sloth chat` 退出 | 保存最终摘要到 `context.json`，关闭 session |
| 下次启动 | 加载 `context.json` 恢复上下文 |

**Phase 切换时的上下文衔接**:

```
用户输入: /run standard

ChatSession:
  1. SessionManager.start_phase("standard", "phase-1")
     → 创建 scenarios/standard/phase-1/
     → 从 PhaseRegistry 获取 phase-1 配置
  2. 切换 LLM: chat LLM → phase-1 LLM (GLM-4)
  3. 构建系统提示:
     - phase-1 的系统提示（需求分析师角色）
     - 前序对话摘要（从 session context.json 提取）
     - phase-1 可用技能列表
  4. 执行 phase-1 对话
  5. Phase 完成:
     → 输出写入 scenarios/standard/phase-1/output.json
     → 对话写入 scenarios/standard/phase-1/chat.jsonl
     → 生成摘要追加到 session context.json
  6. 进入 phase-2，重复步骤 1-5
```

**不丢失信息的保证**:
- 每次 LLM 切换前，生成当前对话的 summary
- Summary 注入到下一个 phase 的系统提示中
- 所有原始对话持久化到 `chat.jsonl`（可随时回溯完整历史）

### 3.5 斜杠命令

| 命令 | 说明 | 版本 |
|------|------|------|
| `/clear` | 清空对话历史 | v1.0 |
| `/context` | 显示上下文信息 | v1.0 |
| `/help` | 显示帮助 | v1.0 |
| `/quit` / `/exit` | 退出 | v1.0 |
| `/skills` | 列出可用技能 | v1.0 |
| `/scenarios` | 列出工作流场景 | v1.0 |
| `/tools` | 列出可用工具 | v1.0 |
| `/skill <name>` | 触发单个技能 | v1.1 |
| `/start autonomous` | 启动自主模式 | v1.1 |
| `/stop` | 中止自主模式 | v1.1 |
| `/status` | 查看自主模式状态 | v1.1 |
| `/run <scenario>` | 触发工作流场景 | v1.2 |
| `/phase <id>` | 执行单个 phase | v1.2 |

### 3.6 CLI 友好化（面向非技术用户）

**版本**: v1.3 新增
**目标用户**: 产品经理、项目管理人员，无代码基础

#### 3.6.1 启动欢迎屏

**参考**: OpenClaw CLI 启动时显示 ASCII 艺术 logo + 版本号 + 幽默 tagline（如 "Your terminal just grew claws"）；Claude Code 显示填充式 ASCII logo + 版本号 + 使用提示；Gemini CLI 显示渐变色 ASCII logo + 版本 commit hash；Crush (Charm) 使用 bubbletea TUI 渲染品牌标识。

**设计原则**: 品牌识别 + 信息密度 + 上下文感知。不只是 "hello"，而是给用户一个 "我了解你的项目" 的第一印象。

**欢迎屏结构**（从上到下）:

```
┌─────────────────────────────────────────────────┐
│                  ASCII Logo                      │  ← 品牌标识，固定内容
│         🦥 Sloth Agent v0.3.0                    │  ← 版本号（语义化）
│        你的 AI 开发搭档                          │  ← Slogan / tagline
├─────────────────────────────────────────────────┤
│ 当前项目: agent-evolve                           │  ← 当前目录名 / git repo 名
│ 活跃模型: qwen3.6-plus (DeepSeek v3.2 备用)       │  ← 当前配置的默认模型
│ 已加载技能: 12 个                                 │  ← 可用能力概览
├─────────────────────────────────────────────────┤
│ 你可以这样开始:                                  │  ← 预设问题（上下文感知）
│  1. 帮我写一个登录页面的需求文档                  │
│  2. 审查当前项目的代码质量                        │
│  3. 执行 plan.md 中的开发计划                     │  ← 有 plan 文件时出现
│  4. 总结一下今天的工作进度                        │
├─────────────────────────────────────────────────┤
│ 输入你的问题，或输入 /help 查看更多              │
└─────────────────────────────────────────────────┘
```

**预设问题动态生成规则**:

| 检测条件 | 生成的预设问题 |
|----------|----------------|
| 当前目录有 `.md` 文件含 "plan" | "执行 plan.md 中的开发计划" |
| 当前目录有 `.py` / `.ts` / `.js` 文件 | "审查当前代码质量" |
| 当前目录有 `test_` 文件 | "运行测试并分析报告" |
| 当前目录有 `requirements.txt` / `pyproject.toml` | "分析项目依赖结构" |
| 当前目录有 `TODO.md` | "查看当前任务清单" |
| git 有未提交的更改 | "查看当前的代码变更" |
| 默认（无特殊文件） | "帮我写一个需求文档" |

**预设问题交互**: 用户可直接输入数字（1-4）选择对应问题，等同于输入完整文本。

**欢迎屏渲染**: 使用 Rich Panel 包裹，分隔线使用暗灰色，Logo 使用品牌色，预设问题使用可交互列表（支持数字快捷选择）。

#### 3.6.2 自然语言帮助

**参考**: Claude Code 的 `/help` 显示分类命令列表 + 自然语言描述；Copilot Studio 的欢迎帮助使用 "你能让我做什么" 的能力描述而非命令列表。

**设计原则**: 能力优先，命令其次。非技术用户关心 "你能帮我做什么"，不关心 "有哪些斜杠命令"。

**帮助屏结构**:

```
┌─────────────────────────────────────────────────┐
│ 我能帮你做什么                                    │
├─────────────────────────────────────────────────┤
│ 📝 写文档     需求文档、技术方案、会议纪要...     │
│ 🔍 审代码     代码审查、架构分析、Bug 排查...     │
│ 📋 做计划     项目计划、任务拆解、排期估算...      │
│ 🚀 跑任务     执行开发计划、自动编码、部署上线...  │
│ 💬 聊想法     讨论产品方案、技术选型、头脑风暴...  │
├─────────────────────────────────────────────────┤
│ 常用命令:                                       │
│  /help      显示这个帮助信息                     │
│  /clear     清空当前对话历史                     │
│  /status    查看自主模式执行状态                  │
│  /skills    查看可用技能列表                     │
│  /quit      退出对话                             │
│                                                   │
│ ── 高级命令（展开查看完整列表）───                │
├─────────────────────────────────────────────────┤
│ 当前会话: sess-abc123 | 已加载 12 个技能          │
└─────────────────────────────────────────────────┘
```

**自然语言帮助的内容规范**:

| 区块 | 规范 |
|------|------|
| 能力描述 | 使用动词短语（"写文档"、"审代码"），不用技术术语 |
| 命令解释 | 白话解释命令的效果，不是命令的语法说明 |
| 高级命令 | 折叠/收起，标注"高级"，避免信息过载 |
| 状态信息 | 一行摘要，不展开详情 |

**完整命令列表**（展开后显示）:

| 命令 | 说明 | 版本 |
|------|------|------|
| `/help` | 显示帮助信息 | v1.0 |
| `/clear` | 清空当前对话历史 | v1.0 |
| `/context` | 显示当前上下文信息 | v1.0 |
| `/quit` / `/exit` | 退出对话 | v1.0 |
| `/skills` | 列出可用技能 | v1.0 |
| `/scenarios` | 列出工作流场景 | v1.0 |
| `/tools` | 列出可用工具 | v1.0 |
| `/skill <name>` | 触发单个技能 | v1.1 |
| `/start autonomous` | 启动自主模式 | v1.1 |
| `/stop` | 中止自主模式 | v1.1 |
| `/status` | 查看自主模式状态 | v1.1 |
| `/run <scenario>` | 触发工作流场景 | v1.2 |
| `/phase <id>` | 执行单个 phase | v1.2 |

#### 3.6.3 中文优先

**设计原则**: 默认中文，但不排斥英文用户。语言跟随用户。

**系统提示规范**:

```
你是 Sloth Agent，一个 AI 开发助手。
你的用户可能是产品经理、项目经理或开发者。
请使用中文回复，除非用户使用英文输入。
你可以帮用户写文档、审查代码、制定计划、执行开发任务。
```

**语言跟随规则**:

| 用户输入 | 响应语言 |
|----------|----------|
| 中文 | 中文 |
| 英文 | 英文 |
| 中英混合 | 跟随主要语言（>50% 字符） |
| 其他语言 | 跟随用户语言 |

**错误信息中文规范**:

| 场景 | 错误信息示例 |
|------|-------------|
| LLM 调用失败 | "无法连接到 AI 服务，请检查网络连接或 API Key 配置" |
| 工具执行失败 | "命令执行失败：uv run pytest 返回了退出码 1" |
| 文件操作失败 | "找不到文件 plan.md，请确认文件路径是否正确" |
| 权限不足 | "没有写入权限，请检查文件权限设置" |

**验收标准**: 首次启动 chat 时，所有可见文本（欢迎屏、帮助、错误信息、确认提示、进度描述）均为中文。

#### 3.6.4 结构化输出

**参考**: GitHub Copilot CLI 的 diff 预览（绿色=新增、红色=删除）；Claude Code 的文件变更摘要（列出修改的文件和行数）；Gemini CLI 的工具调用可视化（显示工具名和参数）。

**设计原则**: 结构化信息 ≠ 大段文字。每项信息用 Rich 组件渲染，让用户一眼看懂。

**各场景的渲染规范**:

| 场景 | 渲染方式 | Rich 组件 |
|------|----------|-----------|
| **代码审查结果** | Table，按严重程度排序 | `Table(columns=["文件", "问题", "严重程度"])`，严重程度用颜色编码（红=高，黄=中，绿=低） |
| **文件修改预览** | Diff 样式，行号标注 | `Panel` 包裹 diff，绿色=新增行，红色=删除行，黄色=修改行 |
| **工具执行结果** | 结构化面板 | `Panel` + `Table`，显示工具名、输入、输出摘要、耗时 |
| **任务进度** | 进度条 + 步骤列表 | `Progress` (spinner + bar) + `Group` 步骤列表，已完成打 ✓ |
| **技能列表** | 表格 | `Table(columns=["技能", "用途", "触发方式"])` |
| **工具列表** | 表格 + 风险标签 | `Table(columns=["工具", "用途", "风险等级"])`，风险用颜色标签 |
| **配置摘要** | Key-Value 表格 | `Table(columns=["配置项", "当前值"])` |
| **场景列表** | 表格 | `Table(columns=["场景", "包含 Phases"])` |

**通用排版规则**:

- 表格宽度自适应终端宽度，超出时截断长文本
- 使用 Panel 包裹相关内容组，Panel 标题描述内容
- 颜色使用 Rich 的语义色（red=错误/高危，green=成功/安全，yellow=警告）
- 避免连续 3 行以上的纯文字输出，超过时分段或折叠

#### 3.6.5 确认卡片

**参考**: Gemini CLI 的 `(Y/n)` 确认 + diff 预览；Claude Code 的 "press Enter to approve" 文件写入确认；Copilot CLI 的权限系统（用户反馈"缺乏上下文导致盲目审批"）；研究表明 "审批疲劳" 会降低安全性（用户盲目点击 approve）。

**设计原则**: 提供足够上下文让用户做出有信息的决策，同时减少审批疲劳。

**确认卡片结构**:

```
┌─────────────────────────────────────────────────┐
│ ⚠️  即将执行以下操作                             │
├─────────────────────────────────────────────────┤
│ 📝 修改 3 个文件:                                │
│   src/app.py        修改 17 行 (第 42-58 行)     │
│   tests/test_app.py 新增文件                     │
│   README.md         修改 1 行 (第 12 行)         │
│                                                   │
│ 🚀 运行命令:                                     │
│   uv run pytest                                  │
├─────────────────────────────────────────────────┤
│ 确认执行？[Y/n]:                                 │
└─────────────────────────────────────────────────┘
```

**确认规则**:

| 操作类型 | 确认方式 | 显示内容 |
|----------|----------|----------|
| 写文件（单文件） | 直接确认 | 文件名 + 变更摘要 |
| 写文件（多文件） | 列表确认 | 所有文件列表 + 各自变更摘要 |
| 运行命令 | 命令预览确认 | 完整命令字符串 |
| 删除文件 | 二次确认 | 文件名 + 内容摘要，需输入 "DELETE" 确认 |
| 网络请求 | URL 预览确认 | 目标 URL + 请求方法 |

**默认选项**: 除删除操作外，所有确认默认选项为 `Y`（用户直接回车即确认）。

**审批疲劳缓解**:

- 合并多个同类操作为一张卡片（如连续写 3 个文件，合并显示）
- 提供 "全部确认" 选项（当有多个独立确认时）
- 显示变更摘要而非全文（用户可要求查看 diff 全文）
- 对已知安全操作（如 `pytest`、`lint`）跳过确认

#### 3.6.6 进度可视化

**参考**: Claude Code 的 spinner "Thinking..."；OpenClaw 的多步骤进度条 + 步骤完成打钩；Gemini CLI 的工具调用实时显示。

**设计原则**: 用户永远不应该盯着一个闪烁的光标发呆。任何超过 1 秒的操作都要有可见的进度指示。

**各级进度指示**:

| 操作类型 | 进度形式 | 显示内容 |
|----------|----------|----------|
| LLM 请求（单次） | Spinner | "正在思考…" |
| 工具执行（单次） | Spinner | "正在执行 {工具名}…" |
| 多步骤任务 | Progress Bar | 当前步骤名 + 完成度 + 总步骤数 |
| 自主模式运行 | 多行状态面板 | 当前阶段 + 已完成步骤 + 预计剩余时间 |
| 文件操作 | 行内提示 | "正在读取 app.py…" |

**多步骤进度条示例**:

```
[●●●●○○○○○○] 40% (2/5) 正在执行 Builder 阶段...
  ✓ 初始化环境
  ✓ 解析 Plan 文件
  ●● 执行 Builder 阶段
  ○ 执行 Reviewer 阶段
  ○ 执行 Deployer 阶段
```

**状态面板规范**（自主模式）:

```
┌─────────────────────────────────────────────────┐
│ 🤖 自主模式运行中                                │
├─────────────────────────────────────────────────┤
│ 当前阶段: Builder (编码)                         │
│ 进度: [●●●○○○] 33%                               │
│ 运行时间: 2m 34s                                 │
│                                                   │
│ 已完成:                                         │
│   ✓ 初始化环境                                   │
│   ✓ 解析 Plan 文件                               │
│ 进行中:                                         │
│   ● Builder 编码中...                            │
│ 等待中:                                         │
│   ○ Reviewer 代码审查                            │
│   ○ Deployer 部署上线                            │
│   ○ Smoke Test 验证                              │
├─────────────────────────────────────────────────┤
│ 输入 /stop 中止执行                              │
└─────────────────────────────────────────────────┘
```

**错误状态指示**:

| 场景 | 显示 |
|------|------|
| LLM 请求超时 | `[red]✗[/red] AI 服务响应超时，正在重试...` |
| 工具执行失败 | `[red]✗[/red] 命令执行失败，正在尝试修复...` |
| Gate 失败 | `[red]⚠[/red] Gate 1 失败: lint 检查未通过，正在重试...` |
| 全部重试失败 | `[red]✗[/red] 执行失败，已重试 3 次，请检查后重试` |

**性能要求**:

- Spinner 必须在操作开始后 0.5s 内出现
- 进度条每步切换间隔不超过 2s（即使步骤未完成也要有"处理中"提示）
- 长时间无输出时（>10s），每 10s 追加一条"仍在处理中…"提示

---

### 3.7 配置模型

**文件**: `src/core/config.py`（新增字段）

```python
class ChatConfig(BaseModel):
    max_context_turns: int = 20
    prompt_prefix: str = "sloth> "
    session_dir: str = "./memory/sessions/"
    auto_save: bool = True
```

### 3.8 飞书集成（v1.2）

**文件**: `src/cli/feishu_server.py`

```
职责: FeishuWebhook 类，处理飞书消息转发
```

**工作模式**:
- 飞书机器人接收用户消息 → POST 到 webhook endpoint
- Webhook 解析消息 → 创建/恢复 session → 发送到 ChatSession 处理
- ChatSession 响应 → 通过飞书消息 API 回复用户
- 飞书卡片交互（审批按钮）→ 触发 workflow 操作

**与 CLI chat 的区别**:
- CLI: 同步 REPL，用户直接在终端输入
- 飞书: 异步 webhook，用户通过飞书消息交互

---

## 4. 接口定义

### 4.1 LLM 交互

**现有接口**: `LLMProviderManager.chat(messages)` — 已有，直接复用

**消息格式**:
```python
[
    {"role": "system", "content": "..."},
    {"role": "user", "content": "hello"},
    {"role": "assistant", "content": "hi"},
]
```

### 4.2 Session 管理

**新接口**:

| 方法 | 说明 |
|------|------|
| `SessionManager.create_session()` | 创建新 session，返回 session_id |
| `SessionManager.load_session(session_id)` | 加载已有 session 的上下文 |
| `SessionManager.save_message(session_id, role, content)` | 追加消息到 chat.jsonl |
| `SessionManager.start_phase(session_id, scenario_id, phase_id)` | 开始 phase，返回 phase 配置 |
| `SessionManager.end_phase(session_id, phase_id, output)` | 结束 phase，保存输出 |
| `SessionManager.get_context(session_id)` | 获取当前上下文摘要 |

### 4.3 Skill 展示

**现有接口**: `SkillRegistry.get_all()`, `SkillRegistry.get(id)` — 已有，直接复用

### 4.4 Scenario 展示

**现有接口**: `PhaseRegistry.list_scenarios()`, `PhaseRegistry.get_by_scenario(id)` — 已有，直接复用

### 4.5 Tool 展示

**现有接口**: `ToolRegistry.list_tools()` — 已有，直接复用

### 4.6 自主模式控制

**新接口**:

| 方法 | 说明 |
|------|------|
| `AutonomousController.start()` | 启动自主模式（后台进程） |
| `AutonomousController.stop()` | 中止自主模式 |
| `AutonomousController.status()` | 返回当前状态 |

---

## 5. 文件结构

```
src/
  cli/
    __init__.py              # 新增，空 init
    app.py                   # 新增，typer CLI 入口
    chat.py                  # 新增，ChatSession REPL
    context.py               # 新增，ConversationContext
    chat_ux.py               # 新增 (v1.3)，欢迎屏/自然语言帮助/确认卡片/进度可视化
    autonomous_controller.py # 新增 (v1.1)，自主模式控制
    feishu_server.py         # 新增 (v1.2)，飞书 webhook
  memory/
    session.py               # 新增，SessionManager
  __main__.py                # 修改，从 AgentEvolve() 改为 typer app
  core/
    config.py                # 修改，添加 ChatConfig
tests/
  cli/
    __init__.py              # 新增
    test_chat.py             # 新增，ChatSession 和 Context 测试
    test_config.py           # 新增，ChatConfig 测试
    test_chat_ux.py          # 新增 (v1.3)，CLI 友好化测试
  memory/
    __init__.py              # 新增
    test_session.py          # 新增，SessionManager 测试
configs/
  agent.yaml                 # 修改，添加 chat 配置段
pyproject.toml               # 修改，添加 typer 依赖
```

---

## 6. 依赖变更

| 依赖 | 版本 | 说明 |
|------|------|------|
| typer | >= 0.9.0 | 新增，CLI 框架 |
| fastapi | >= 0.100.0 | 新增 (v1.2)，飞书 webhook server |
| uvicorn | >= 0.23.0 | 新增 (v1.2)，ASGI server |

---

## 7. 测试策略

| 测试 | 说明 | 版本 |
|------|------|------|
| `test_context_add_message` | 消息添加正确 | v1.0 |
| `test_context_truncation` | 超过 max_turns 时正确截断 | v1.0 |
| `test_context_clear` | 清空后消息列表为空 | v1.0 |
| `test_context_system_prompt` | system prompt 正确包含 | v1.0 |
| `test_chat_config_defaults` | ChatConfig 默认值正确 | v1.0 |
| `test_config_has_chat_field` | Config 包含 chat 字段 | v1.0 |
| `test_session_create` | 创建 session，目录和文件存在 | v1.0 |
| `test_session_save_load_message` | 保存/加载消息，数据一致 | v1.0 |
| `test_session_phase_start_end` | Phase 开始/结束，目录和文件正确 | v1.1 |
| `test_session_context_preservation` | Phase 切换后上下文不丢失 | v1.1 |
| `test_welcome_screen_shown` | 启动时显示欢迎信息和预设问题 | v1.3 |
| `test_welcome_context_aware` | 预设问题根据当前目录上下文动态生成 | v1.3 |
| `test_help_natural_language` | /help 显示自然语言帮助而非命令列表 | v1.3 |
| `test_chinese_default_prompt` | 系统提示默认使用中文 | v1.3 |
| `test_structured_output_table` | 审查结果等结构化信息使用 Rich table | v1.3 |
| `test_confirm_card_file_change` | 文件修改前显示确认卡片 | v1.3 |
| `test_confirm_card_default_yes` | 确认提示默认选项为 Y | v1.3 |
| `test_progress_spinner` | 长时间任务显示 Rich spinner | v1.3 |
| `test_progress_bar_multistep` | 多步骤任务显示进度条 | v1.3 |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| LLM API 调用失败 | 用户得不到响应 | 捕获异常，显示错误信息，不崩溃 |
| 上下文过长 | 超出 LLM token 限制 | 截断旧消息，保留最近 N 轮 |
| 终端编码问题 | 中文乱码 | 使用 rich 的 Console 处理输出 |
| Phase 切换时信息丢失 | 上下文断裂 | 每次切换前生成摘要，持久化所有对话 |
| 飞书 webhook 认证失败 | 消息无法转发 | 实现 token 验证，失败时记录日志 |

---

## 9. 与自主模式的关系

### 9.1 昼夜模式说明

| 模式 | 时段 | 自主程度 | 说明 |
|------|------|---------|------|
| 夜模式 | 22:00 - 09:00 | **半自主** | 阶段一(需求分析) → 阶段二(计划制定) → **Human 审批** → 确认执行 |
| 日模式 | 09:00 - 22:00 | **全自主** | 阶段三(编码) → 阶段八(监控)，TDD + 验证门控，不需要人工介入 |

### 9.2 Chat mode 对自主模式的控制

```
Chat mode (控制面):
  /start autonomous    → 启动自主模式（当前时段对应日/夜模式）
  /stop autonomous     → 中止自主模式（保存当前状态）
  /status              → 显示：当前阶段、进度、运行时间

自主模式 (被控制):
  启动时 → 检查是否有未完成的 plan
  运行中 → 定期写入 status.json（供 chat mode 读取）
  被中止时 → 保存 checkpoint，安全退出
  遇到未解决问题 → 记录问题 + 尝试方法，等晚上 review
```

---

*规格版本: v1.3.0*
*创建日期: 2026-04-16*
*最后更新: 2026-04-18*
