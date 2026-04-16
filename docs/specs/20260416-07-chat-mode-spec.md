# Chat Mode 设计规格

> 版本: v1.1.0
> 日期: 2026-04-16
> 状态: 待审批

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

### 3.6 配置模型

**文件**: `src/core/config.py`（新增字段）

```python
class ChatConfig(BaseModel):
    max_context_turns: int = 20
    prompt_prefix: str = "sloth> "
    session_dir: str = "./memory/sessions/"
    auto_save: bool = True
```

### 3.7 飞书集成（v1.2）

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

*规格版本: v1.1.0*
*创建日期: 2026-04-16*
