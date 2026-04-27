# Chat Message Management — Sloth Agent

> 当前实现方式文档（v0.5.1）
> 最后更新：2026-04-27

---

## 1. 存储层

### 数据库

**引擎**：SQLite（SQLAlchemy async + aiosqlite）

**表结构** — `messages`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | UUID (TEXT) | 主键 |
| `inspiration_id` | TEXT FK | 所属 Inspiration |
| `agent_id` | TEXT FK (nullable) | 发送消息的 Agent（human 消息为 NULL） |
| `role` | TEXT | `"human"` / `"agent"` / `"system"` |
| `content` | TEXT | 消息正文 |
| `created_at` | DATETIME | 创建时间（UTC） |

**特点**：
- 纯文本存储，不做压缩或分块
- 无 token 计数列（当前不做 token 级管理）
- 无归档机制（单表存储所有历史消息）

---

## 2. 上下文构建

### 2.1 消息查询

```python
# backend/app/routers/chat.py — chat() & chat_stream()
stmt = (
    select(Message)
    .where(Message.inspiration_id == inspiration_id)
    .order_by(Message.created_at.desc())
    .limit(1000)
)
history = list(result.scalars().all())[::-1]
```

- 取最近 **1000 条**消息（v0.5.1 调整，原为 20）
- 按时间倒序查询后反转，保证时间正序送入 LLM

### 2.2 上下文组装

```python
llm_messages = []

# Layer 1: System Prompt（来自 AgentTemplate）
if tpl and tpl.system_prompt:
    llm_messages.append({"role": "system", "content": tpl.system_prompt})

# Layer 2: 历史消息（role 映射）
llm_messages += [
    {"role": _map_role(m.role), "content": m.content}
    for m in history
]

# Layer 3: 当前用户输入
llm_messages.append({"role": "user", "content": req.content})
```

**Role 映射**：
```python
ROLE_MAP = {"human": "user", "agent": "assistant", "system": "system"}
```

### 2.3 模型调用

```python
# backend/app/services/llm.py
llm = LLMService()
reply = await llm.chat(agent.model, llm_messages)
```

- 使用 OpenAI-compatible `/v1/chat/completions` 接口
- `messages` 数组一次性传入 → **标准多轮对话模式**
- 不拆轮次、不做摘要、不做分层压缩

---

## 3. SSE 流式传输

### 3.1 非流式端点

`POST /api/inspirations/{id}/chat`
- 等待 LLM 完整回复 → 存库 → 返回完整 MessageResponse

### 3.2 流式端点

`POST /api/inspirations/{id}/chat/stream`
- 使用 `StreamingResponse` + `text/event-stream`
- token 逐个 yield：`data: {"token": "..."}\n\n`
- 流结束发送：`data: [DONE]\n\n`
- **存档时机**：流全部完成后，在新的 db session 中一次性保存完整回复
- 错误时 agent 状态设为 `"error"`，有回复则设为 `"idle"`

---

## 4. Agent 信息关联

每条消息返回时，附带其所属 Agent 的元信息：

```python
# backend/app/routers/chat.py — _build_agent_map()
agent_map[a.id] = (a.name, i + 1, model)
```

- **agent_name**：Agent 模板名称（如 "General Manager"）
- **agent_number**：按 `joined_at` 排序后的序号（从 1 开始）
- **agent_model**：Agent 指定的模型 → 默认 LLM 配置的模型

---

## 5. 当前限制

| 项目 | 现状 | 说明 |
|------|------|------|
| 上下文窗口 | 最近 1000 条 | 不设 token 预算，依赖模型自身窗口（DeepSeek v4 支持 1M） |
| 摘要/压缩 | 无 | 不做分层摘要或滑动窗口压缩 |
| 消息归档 | 无 | 所有消息永久保留在 SQLite 单表中 |
| 多 Agent 对话 | 不支持 | 当前只有 Lead Agent 回复，其他 Agent 不参与对话 |
| 分支/编辑 | 不支持 | 没有消息编辑、回滚或对话分支 |
| Prompt Cache | 不使用 | 没有锚定 system prompt 或其他可缓存前缀 |

---

## 6. 与自主流水线模式的区别

| | Chat 模式 | 自主流水线模式 (`sloth run`) |
|------|-----------|------|
| 存储 | SQLite `messages` 表 | JSONL 文件（`memory_store`） |
| 上下文 | 1000 条消息 | ContextWindowManager 做 token 截断 + 摘要 |
| 模式 | 多轮对话 | Agent 单次任务执行 |
| 压缩 | 无 | 有（对话摘要压缩） |
