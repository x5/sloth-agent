# Session 管理设计规格

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 待审批

---

## 1. 需求描述

### 1.1 问题

Sloth Agent 目前没有 session 概念：
- `AgentEvolve.run()` 每次启动都是独立的，不记录会话
- Chat mode 需要一个 session 来管理对话历史和上下文
- Phase 执行时，每个 phase 的对话需要关联到所属 session
- 切换 phase 时（涉及切换 agent 和 LLM），需要保证上下文不丢失

### 1.2 目标

| 版本 | 能力 | 说明 |
|------|------|------|
| **v1.0** | Session 生命周期管理 | 创建、加载、保存、关闭 session，管理 chat.jsonl |
| **v1.1** | Phase 切换上下文衔接 | Phase 切换时摘要传递，LLM 切换不丢失信息 |
| **v1.2** | 多 session 并行 | 同时支持 CLI chat + 飞书 chat 两个 session |

---

## 2. 架构设计

### 2.1 Session 模型

```
Session
├── session_id: str              # 唯一标识，如 "chat-20260416-100000"
├── mode: str                    # "chat" | "autonomous" | "feishu"
├── created_at: datetime
├── updated_at: datetime
├── current_phase: str | None    # 当前正在执行的 phase（null = 自由对话）
├── current_scenario: str | None # 当前正在执行的 scenario
├── context: dict                # 活跃上下文摘要
├── message_count: int           # 消息总数
└── phases_executed: list[str]   # 已执行的 phase 列表
```

### 2.2 Session 与 Memory 的关系

```
SessionManager
    ├── 管理 session 生命周期（创建/加载/保存/关闭）
    └── 使用 MemoryStore 存储数据
         ├── sessions/{session_id}/chat.jsonl
         ├── sessions/{session_id}/context.json
         └── sessions/{session_id}/metadata.json

当 session 触发 phase 执行时：
    ├── 在 scenarios/{scenario_id}/{phase_id}/ 下创建 phase 目录
    ├── Phase 对话写入 scenarios/{scenario_id}/{phase_id}/chat.jsonl
    └── Phase 输出写入 scenarios/{scenario_id}/{phase_id}/output.json

Session 是"容器"，Phase 是"内容"，MemoryStore 是"存储引擎"
```

### 2.3 Phase 切换时的上下文衔接

```
用户输入: /run standard

SessionManager 流程:
1. 保存当前 chat 上下文摘要
   → 从 session context.json 提取关键信息
   → 生成 summary: "用户想要开发一个卡片游戏，已完成需求分析..."

2. 创建 phase-1 目录
   → scenarios/standard/phase-1/
   → 写入 input.json（包含 chat 摘要作为初始输入）

3. 切换 LLM
   → 从 chat LLM (deepseek) 切换到 phase-1 LLM (glm-4)
   → 构建系统提示:
     - phase-1 角色定义: "你是需求分析师"
     - 前置上下文: summary（来自 step 1）
     - phase-1 可用技能列表

4. 执行 phase-1 对话
   → 用户与 analyst agent 交互
   → 每轮对话写入 scenarios/standard/phase-1/chat.jsonl

5. Phase-1 完成
   → 输出写入 output.json
   → 生成 phase 摘要
   → 摘要追加到 session context.json

6. 切换到 phase-2
   → 重复步骤 1-5
   → phase-2 的系统提示包含 phase-1 的摘要
```

**不丢失信息的三层保证**:

| 层级 | 保证 | 内容 |
|------|------|------|
| **完整层** | `chat.jsonl` | 所有原始对话，可完整回溯 |
| **摘要层** | `context.json` | 活跃摘要，供 LLM 快速理解上下文 |
| **结构层** | `output.json` | Phase 的结构化输出，供后续 phase 使用 |

---

## 3. 模块定义

### 3.1 SessionManager

**文件**: `src/memory/session.py`（新增）

```
职责: Session 生命周期管理
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `create_session(mode, **kwargs)` | 创建新 session，返回 session_id |
| `load_session(session_id)` | 加载 session 上下文 |
| `save_message(session_id, role, content)` | 追加消息到 chat.jsonl |
| `get_messages(session_id, limit)` | 获取最近 N 条消息 |
| `get_context(session_id)` | 获取当前上下文摘要 |
| `update_context(session_id, context)` | 更新上下文摘要 |
| `close_session(session_id)` | 关闭 session，保存最终状态 |
| `list_sessions()` | 列出所有 session |
| `start_phase(session_id, scenario_id, phase_id)` | 开始 phase，创建目录，加载配置 |
| `end_phase(session_id, phase_id, output)` | 结束 phase，保存输出和摘要 |
| `get_phase_messages(scenario_id, phase_id)` | 获取指定 phase 的对话 |

### 3.2 ContextSummarizer

**文件**: `src/memory/summarizer.py`（新增）

```
职责: 生成对话摘要，用于 Phase 切换时的上下文传递
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `summarize_conversation(messages)` | 从对话列表生成摘要 |
| `summarize_phase(output)` | 从 phase 输出生成摘要 |
| `merge_summaries(old, new)` | 合并旧摘要和新摘要 |

**摘要策略（v1.0）**:
- 规则式摘要：提取关键信息（用户目标、已完成的 phase、关键决策）
- 不依赖 LLM（减少成本和延迟）

**摘要策略（v1.1）**:
- 使用 LLM 生成更精准的摘要
- 摘要 token 控制在 300 tokens 以内

### 3.3 AutonomousController

**文件**: `src/cli/autonomous_controller.py`（新增，v1.1）

```
职责: 从 chat mode 控制自主模式
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `start()` | 启动自主模式（后台进程） |
| `stop()` | 中止自主模式 |
| `status()` | 返回当前状态 |

---

## 4. Session ID 生成

```python
def generate_session_id(mode: str) -> str:
    """生成 session ID。
    
    格式: {mode}-{YYYYMMDD}-{HHMMSS}-{random}
    示例: "chat-20260416-100000-a1b2"
    """
    now = datetime.now().strftime("%Y%m%d-%H%M%S")
    random_suffix = secrets.token_hex(2)
    return f"{mode}-{now}-{random_suffix}"
```

---

## 5. 数据格式

### 5.1 Session metadata.json

```json
{
  "session_id": "chat-20260416-100000-a1b2",
  "mode": "chat",
  "created_at": "2026-04-16T10:00:00Z",
  "updated_at": "2026-04-16T10:30:00Z",
  "model": "deepseek-chat",
  "provider": "deepseek",
  "current_phase": null,
  "current_scenario": null,
  "message_count": 42,
  "phases_executed": ["phase-5"],
  "context": {
    "user_goal": "开发一个卡片游戏",
    "completed_phases": [],
    "key_decisions": ["选择 React 作为前端框架"]
  }
}
```

### 5.2 Phase 切换时的 input.json

```json
{
  "type": "phase_input",
  "phase_id": "phase-1",
  "scenario_id": "standard",
  "chat_summary": "用户想要开发一个卡片游戏，目标是在两周内完成 MVP。",
  "previous_phases": [],
  "timestamp": "2026-04-16T10:05:00Z"
}
```

---

## 5.3 Continuation：恢复优先依赖自有 RunState

系统允许多种 continuation 来源，但 `RunState` 始终是第一真相源：

```python
class ContinuationState(BaseModel):
    session_id: str | None = None
    snapshot_id: str | None = None
    provider_name: str | None = None
    provider_token: str | None = None
    daemon_thread_id: str | None = None
```

其中 provider token 只是优化层，不能成为系统规范中的真相源。

---

## 6. 文件结构

```
src/
  memory/
    session.py               # 新增，SessionManager
    summarizer.py            # 新增，ContextSummarizer
  cli/
    autonomous_controller.py # 新增 (v1.1)
tests/
  memory/
    test_session.py          # 新增
    test_summarizer.py       # 新增
```

---

## 7. 测试策略

| 测试 | 说明 |
|------|------|
| `test_session_create` | 创建 session，目录和文件存在 |
| `test_session_save_load_message` | 保存/加载消息，数据一致 |
| `test_session_context_update` | 上下文能正确更新 |
| `test_session_phase_start_end` | Phase 开始/结束，目录和文件正确 |
| `test_session_close` | 关闭 session，最终状态保存 |
| `test_summarize_conversation` | 对话摘要生成正确 |
| `test_summarize_merge` | 摘要合并正确 |

---

## 8. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Session 未正常关闭 | 数据丢失 | 异常时自动保存（try/finally） |
| 摘要信息丢失 | Phase 切换后上下文断裂 | 完整对话始终保留在 jsonl |
| 多 session 并发写入 | 冲突 | 每个 session 独立文件，无共享写入 |

---

*规格版本: v1.0.0*
*创建日期: 2026-04-16*
