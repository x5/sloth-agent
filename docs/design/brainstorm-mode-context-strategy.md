# Brainstorm 模式 — 上下文策略设计

> 状态: DRAFT
> 日期: 2026-04-28
> 关联: `docs/design/chat-message-management.md`, `docs/ref/agent-message-management-research.md`

---

## 1. 模式定义

Brainstorm 是 Chat 之外的第二种对话模式。在一个 Inspiration 中，用户和多个 Agent、Agent 和 Agent 之间可以自由讨论，每条消息都可以针对上一条消息进行发散辩论。

### 与 Chat 模式的核心区别

| 维度 | Chat 模式 | Brainstorm 模式 |
|------|----------|----------------|
| 回复者 | 单一 Agent（Lead Agent 调度或直接回复） | 所有 Team 成员 |
| 消息可见性 | 按 Agent 隔离 | 全局共享，所有人看到所有消息 |
| 发言决策 | 无（唯一回复者） | 每个 Agent 自主决定是否发言 |
| 上下文结构 | 扁平数组 | 带 `reply_to` 引用关系 |
| 结束条件 | 用户发下一条 | 所有 Agent PASS 或达到最大轮数 |
| 收敛机制 | 无 | Lead Agent 生成讨论总结 |
| 单轮 LLM 调用 | 1 次 | N 次短调用 + M 次长调用 |

---

## 2. 消息可见性

### Chat 模式

```
User ──→ Lead Agent
          ↑ 只有 Lead 看见完整上下文
          其他 Agent 不可见
```

### Brainstorm 模式

```
User ──→ 全体可见
          ↑ ↓
          所有 Agent 互相可见
```

**查询策略：**

```sql
-- Chat 模式: 按 agent 过滤上下文
SELECT * FROM messages
WHERE inspiration_id = ? AND (agent_id = ? OR role = 'human')
ORDER BY created_at;

-- Brainstorm 模式: 全量上下文
SELECT * FROM messages
WHERE inspiration_id = ?
ORDER BY created_at;
```

同一个 `messages` 表，两种查询策略。**不需要改表结构。**

---

## 3. 发言决策：两轮判断

Brainstorm 的核心难题：新消息进来后，N 个 Agent，谁该回复？

### Round 1 — 意图收集（短、并行）

给每个 Agent 一个极短的 prompt：

```
"用户说：'这个登录应该用什么认证？'
 你是否有话要说？只回复 YES 或 NO，加一句话说明你想说什么方向。"
```

N 个 Agent **并行**调用，每个只生成 ~10 个 token。总成本 ≈ 1 次聊天。

| Agent | 回复 | 代价 |
|-------|------|------|
| FE-1 | YES — JWT 的前端实现 | ~5 tokens |
| FE-2 | YES — 移动端兼容性 | ~5 tokens |
| BE-1 | YES — Session 方案 | ~5 tokens |
| QA | NO | ~2 tokens |
| Reviewer | YES — 安全角度 | ~5 tokens |

### Round 2 — 正式发言（并行）

愿意发言的 Agent 并行生成完整回复。**关键**：每个发言 Agent 的上下文包含 Round 1 的所有意向，可以做针对性回应。

```
FE-1 的上下文:
  [system prompt]           ← FE-1 的角色定义
  [用户原始消息]             ← 当前话题
  [Round 1 发言意向]
    "FE-2 想聊移动端兼容性"
    "BE-1 想聊 Session 方案"
    "Reviewer 想聊安全角度"
  [生成你自己的发言]
```

**效果**：FE-1 的发言可以直接引用 BE-1 的观点进行反驳，模拟真实辩论。

```
FE-1: "BE-1 提到 Session 方案，但在这个移动端场景下，
       Session 有几个问题：1. 服务端状态管理复杂 2. 跨设备体验差
       我建议 JWT + refresh token..."
```

---

## 4. 多轮辩论推进

不使用固定轮数，改用**冷却计时**模型。因为 C 回复 B，B 回复 A——本质上都在讨论同一个话题，不能简单按轮数切割。

```
用户发消息 (或系统触发讨论)
  │
  ├─ 初始发言阶段
  │   Agent A 发言, Agent B 发言, Agent C 发言 (并行)
  │
  ├─ 冷却期开始
  │   有新发言 → 重置冷却计时器 → 再等 5 秒
  │   冷却期内无人发言 → 冷却结束
  │
  ↓
讨论自然结束 → Lead Agent 生成总结
```

### 时间线示例

```
0s    User: "用什么认证？"
0.5s  Agent A 发言          ← 冷却计时器: 5s
1.2s  Agent B 发言          ← 冷却计时器重置: 5s
2.0s  Agent C 回复 B         ← 冷却计时器重置: 5s
7.0s  无新发言              ← 冷却结束!
7.5s  Lead Agent 总结
```

### 二重保护

冷却计时器可能永远无法触发（Agent 控节奏轮流发言），加两个硬保护：

| 保护 | 值 | 说明 |
|------|---|------|
| 冷却计时 | 5 秒 | 无人发言 N 秒后自然结束 |
| 最大消息数 | 500 条 | 本轮讨论最多 500 条发言，硬截断 |

**用户可随时插话**：用户发新消息 → 上一轮立即结束 → 生成总结 → 新话题开始。

---

## 5. 上下文组织

Brainstorm 的上下文不是扁平的 `messages[]` 数组，而是带引用关系的结构：

```python
def build_brainstorm_context(history, current_round, agent):
    """
    返回:
    [
        {role: system,  content: agent.system_prompt},
        {role: user,    content: "用户原始问题", id: msg_1},

        # Round 1 发言意向（注入为 system 消息）
        {role: system,  content: "本轮流言意向: FE-1(YES:JWT), BE-1(YES:Session), QA(NO)"},

        # Round 2 发言
        {role: assistant, content: "[FE-1]: JWT 方案...", id: msg_2, reply_to: msg_1},
        {role: assistant, content: "[BE-1]: Session 更好...", id: msg_3, reply_to: msg_2},
        {role: assistant, content: "[Reviewer]: 安全角度...", id: msg_4, reply_to: msg_1},

        # Round 3 意向
        {role: system,  content: "上轮总结: FE-1 支持 JWT, BE-1 反对, Reviewer 关注安全"},
    ]
    """
```

**注意**：Round 1 的发言意向以 `role: system` 注入上下文，不混入对话流。前端不展示意向消息。

---

## 6. 停止机制

### 核心模型：冷却计时

不使用固定轮数。用冷却计时器 + 最大消息数：

```
状态机:
  RUNNING ──有新发言──> RUNNING (重置冷却计时器 5s)
  RUNNING ──5s 无人发言──> COOLING_DOWN
  COOLING_DOWN ──有新发言──> RUNNING
  COOLING_DOWN ──3s 无新发言──> ENDED
  RUNNING ──达到 500 条──> ENDED (硬截断)
  RUNNING ──用户发新消息──> ENDED (用户打断)
```

### 触发条件

| 条件 | 说明 |
|------|------|
| 冷却期无人发言 | 5s 冷却 + 3s 确认，共 8s 无人发言 |
| 达到 500 条 | 本轮讨论累计 500 条发言，硬截断 |
| 用户打断 | 用户在讨论中发新消息，立即结束并总结 |

### 冷却计时器参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `cooldown_seconds` | 5s | 有新发言后等待的冷却时间 |
| `confirmation_seconds` | 3s | 冷却到期后的确认期，防止正好有 Agent 在打字 |
| `max_messages` | 500 | 本轮绝对上限 |
| `intent_timeout` | 3s | 意图收集阶段，超时未回复视为 PASS |

### 收敛

结束 → Lead Agent 生成总结:

```
"讨论共识:
 - 移动端使用 JWT + refresh token
 - Web 端使用 Session + Redis
 - 统一通过 API Gateway 处理认证

 下一步:
 - FE-1: 实现 JWT 中间件
 - BE-1: 搭建 Redis Session 服务
 - Reviewer: 审查认证代码的安全性"
```

---

## 7. 模式切换

在 ChatArea TopBar 加模式开关：

```
[💬 Chat]  [🧠 Brainstorm]
  默认       新模式
```

两个模式共享同一套数据，但后端行为完全不同。

---

## 8. 数据模型改动

**只需加一个字段：**

```python
# messages 表
parent_message_id: Mapped[str | None] = mapped_column(
    CHAR(36), ForeignKey("messages.id", ondelete="SET NULL"), nullable=True
)
```

- `NULL`：新话题、直接回复用户
- 有值：回复某条具体消息（在 Brainstorm 中形成引用链）

`mode` 字段**不需要存数据库**，通过 API 请求参数传递。

---

## 9. 前端 UI 结构

**不使用缩进**，否则嵌套 5 层后消息会挤到屏幕边缘。改用**左侧色彩竖线 + 回复标签**：

```
┌──────────────────────────────────────────────────────────────┐
│ User: "用什么认证方案？"                                       │
│                                                              │
│ ┃ 🤖 FE-1 (deepseek)                                        │  ← 蓝色竖线（#6841EA）
│ ┃ │ "JWT，无状态好扩展"                                       │
│ ┃ │                                                          │
│ ┃ │ 🤖 BE-1 (deepseek)       回复 FE-1                       │  ← @标签
│ ┃ │ │ "Session 更安全，因为..."                               │
│ ┃ │ │                                                        │
│ ┃ │ │ 🤖 QA (qwen)            回复 BE-1                      │
│ ┃ │ │ │ "同意，还要考虑 token 刷新"                           │
│ ┃ │ │                                                          │
│ ┃ │ │ 🤖 FE-2 (qwen)          回复 BE-1                      │
│ ┃ │ │   "移动端场景下 Session 太重了"                         │
│ ┃ │                                                          │
│ ┃ 🤖 Reviewer (claude)        回复 User                      │  ← 同一蓝色竖线（同一线程）
│ ┃   "不管用哪个，XSS 防护是前提"                               │
│                                                              │
│ ┊ User: "好，先按 JWT 方案来"                                  │  ← 新消息，无竖线（新话题根）
│ ┊ 🤖 FE-1 (deepseek)          回复 User                      │  ← 橙色竖线（#D4710A，新线程）
│ ┊   "收到，我开始写 JWT 中间件..."                             │
└──────────────────────────────────────────────────────────────┘
```

**线程颜色规则**：
- 每条消息的线程色 = 追溯到根消息，对根消息 ID 做 hash → `hsl(hash % 360, 45%, 55%)`
- 同一根消息下的所有回复共享同一种左侧竖线颜色
- 新话题（`parent_message_id = NULL`）无竖线，颜色通过 hash 自动分配
- 竖线宽度 3px，圆角，位于消息气泡左侧 8px

**回复标签规则**：
- 消息有 `parent_message_id` 时，在 header 右侧显示 `回复 XX`
- 格式：`回复 FE-1`、`回复 User`
- 颜色与竖线一致，10px 字号，半透明背景

**消息对齐**：所有消息左对齐，不使用缩进。

### 用户回复功能

用户在 Brainstorm 中有两种回复方式：

**方式 1：泛回复（广播）**

直接在输入框打字，不指定回复目标。`parent_message_id = NULL`，等于开启新话题或对整场讨论发表意见。

**方式 2：指定回复（精准引用）**

Hover 某条消息 → 出现"回复"按钮 → 点击后输入框上方出现回复标签：

```
 ┌──────────────────────────────────────────────┐
 │ 回复 FE-1 · "JWT，无状态好扩展"          [✕] │  ← 回复标签，可取消
 ├──────────────────────────────────────────────┤
 │                                              │
 │ 我觉得 JWT 的 refresh token 方案...           │  ← 用户输入
 │                                              │
 ├──────────────────────────────────────────────┤
 │                                  [📎]  [→]   │
 └──────────────────────────────────────────────┘
```

- 点击 [✕] → 取消回复标签 → 回到广播模式
- 发送后 `parent_message_id` 指向目标消息
- 用户的回复同样显示左侧竖线（继承目标的线程色）

**回复标签规格：**
- 位于 textarea 上方，flex row，`gap: 6px`
- 内容：`回复 {agent_name} · "{原文前 30 字}"  [✕]`
- 背景：`--color-accent-bg`，圆角 8px，padding 4px 10px
- 字号 12px，颜色 `--text-accent-dark`
- [✕] 关闭按钮点击取消引用，不发送请求

---

## 10. API 设计

```
POST /api/inspirations/{id}/brainstorm
  Body: {
    "content": "用户消息",
    "parent_message_id": null,    // 可选, 回复特定消息时传入
    "cooldown_seconds": 5,        // 可选, 冷却时间, 默认 5s
    "max_messages": 500           // 可选, 最大消息数, 默认 500
  }
  Response: SSE 流式
    事件类型:
      - "agent_start"     → {agent_id, agent_name}    ← 开始意图判断
      - "agent_intent"    → {agent_id, intent: "YES/NO", direction: "..."}
      - "message_token"   → {agent_id, message_id, token: "..."}
      - "message_done"    → {agent_id, message_id, parent_message_id, full_content}
      - "cooldown_start"  → {seconds: 5}              ← 进入冷却
      - "cooldown_reset"  → {triggered_by: agent_id}  ← 有新发言, 重置冷却
      - "discussion_end"  → {summary: "...", message_count: 23}
      - "max_reached"     → {limit: 500}              ← 达到上限, 硬截断
      - "error"           → {error: "..."}
```

前端根据事件类型渲染不同 UI：
- `intent` → 显示"FE-1 正在输入..."或"QA 跳过"
- `message_token` → 逐 token 渲染对应 Agent 的发言气泡
- `round_summary` → 展示当前轮总结
- `discussion_end` → 展示 Lead Agent 的讨论总结

---

## 11. 成本模型

Brainstorm 的单轮成本：

```
假设: 5 个 Agent, 3 个愿意发言

Round 1 (意图): 5 × ~10 tokens 输入 + ~5 tokens 输出 ≈ 75 tokens
Round 2 (发言): 3 × ~200 tokens 输入 + ~150 tokens 输出 ≈ 1050 tokens
                        ↑ 比普通 Chat 多 3 倍

3 轮辩论 ≈ 3000-4000 tokens （vs 普通 Chat 单轮 ~300-500 tokens）
```

成本是 Chat 模式的 **6-10 倍**。这也是为什么 P0（Token 计数）在 Brainstorm 场景下从 "暂缓" 变成 "必要"。

---

## 12. 双模上下文引擎

理清 Brainstorm 后，上下文引擎需要支持两种策略：

| 模式 | Chat | Brainstorm |
|------|------|-----------|
| 可见性 | 按 agent_id 隔离 | 全量共享 |
| 上下文构建 | `get_messages_for_agent()` | `get_all_messages()` |
| 发言决策 | 无（单一回复者） | 两轮判断（intent → speak） |
| 滑动窗口 | 按 agent 独立裁剪 | 全局裁剪，保留 reply_to 链完整性 |
| 摘要 | 按需（单 Agent） | 轮次总结（多 Agent） |

### ContextWindowManager 接口

```python
class ContextWindowManager:
    def __init__(self, mode: Literal["chat", "brainstorm"]):
        self.mode = mode
        self.max_messages = 1000
        self.tail_rounds = 20  # Chat 模式
        self.max_brainstorm_messages = 500  # Brainstorm 模式

    def build(self, agent_id: str | None, history: list[Message]) -> list[dict]:
        if self.mode == "chat":
            return self._build_chat(agent_id, history)
        else:
            return self._build_brainstorm(history)

    def _build_chat(self, agent_id, history):
        """按 agent 过滤 + Head/Tail 保护"""

    def _build_brainstorm(self, history):
        """全量 + reply_to 链保护"""
```

### Reply-to 链保护算法

窗口裁剪时，从最新的消息反向遍历 `parent_message_id` 链。**只要后代在窗口里，祖宗就不丢弃。**

```python
def _protect_reply_chains(self, messages: list[Message]) -> list[Message]:
    """
    输入: 按时间排序的消息列表
    输出: 裁剪后的消息，保证 reply_to 链完整
    """
    if len(messages) <= self.max_brainstorm_messages:
        return messages

    # 从最新的消息开始，保留最近 max_messages 条
    tail = messages[-self.max_brainstorm_messages:]
    protected: set[str] = set()
    queue: list[str] = [m.id for m in tail]

    # 反向遍历，标记所有被引用的祖先
    for msg in reversed(messages):
        if msg.id in queue:
            protected.add(msg.id)
            if msg.parent_message_id:
                queue.append(msg.parent_message_id)

    # 保留: 受保护的链 或 在 Tail 中
    tail_ids = {m.id for m in tail}
    return [m for m in messages if m.id in protected or m.id in tail_ids]
```

### 示例

```
消息树:
  msg_1 (User)
  ├─ msg_2 (FE-1)          ← 太旧，但被 msg_5 引用 → 保护
  │  └─ msg_5 (QA)         ← 在 Tail 内 → 保护
  │     └─ msg_7 (FE-2)    ← 在 Tail 内 → 保护
  ├─ msg_3 (BE-1)          ← 太旧，但被 msg_6 引用 → 保护
  │  └─ msg_6 (Reviewer)   ← 在 Tail 内 → 保护
  └─ msg_4 (User 插话)     ← 太旧，无后代引用 → 丢弃

反向遍历队列:
  msg_7 → msg_5 → msg_2 → msg_1
  msg_6 → msg_3
  msg_4 不在队列 → 丢弃
```

---

## 13. 对 P1-P4 的影响

| 原优先级 | 能力 | 重新评估 |
|----------|------|---------|
| P0 | Token 计数 | **不再暂缓** — Brainstorm 成本是 Chat 的 6-10 倍，必须追踪 |
| P1 | Cache 锚定 | **保留 P1** — Chat 和 Brainstorm 的 system prompt 不同，缓存收益大 |
| P2 | 滑动窗口 | **升级为刚需** — Brainstorm 多轮 × 多 Agent 消息量暴增 |
| P3 | 摘要压缩 | **方向调整** — 不是"压缩中间消息"，而是"生成轮次总结" |
| P4 | 消息隔离 | **拆分为二** — Chat 用隔离，Brainstorm 用共享。变成双模引擎 |

### 建议新优先级

```
Iter-3 消息管理: 双模上下文引擎
  ├─ Phase A: Token 计数 + 成本追踪（Brainstorm 的前提）
  ├─ Phase B: 双模 ContextWindowManager（Chat 隔离 + Brainstorm 共享）
  ├─ Phase C: Cache 锚定（两种模式的 system prompt 各自缓存）
  └─ Phase D: 摘要/轮次总结（Chat 压缩 + Brainstorm 轮次总结）
```
