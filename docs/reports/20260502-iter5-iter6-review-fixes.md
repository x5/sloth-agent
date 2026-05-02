# Iter-5 / Iter-6 Review Fixes Report

> 日期: 2026-05-02  
> 触发: Code Review + Spec Cross-Reference 分析  
> 测试验证: 后端 34 passed · 前端 36 passed

---

## 概述

本次 review 覆盖 Iter-5（一次性 SSE 讨论引擎）与 Iter-6（持久连接 + Reply + 彩色线程），共识别 **12 项问题**，其中 2 项代码 Bug 修复、2 项注释增强、8 项文档同步，涵盖功能 Bug、竞态条件、逻辑错误、文档不一致四类。

---

## 修复项汇总

### 🔴 P0 — 功能/逻辑 Bug（必须修复）

#### 1. CoolingTimer 竞态：LLM 生成期间错误触发冷却

**文件**: `backend/app/services/brainstorm.py`  
**问题**: `heartbeat()` 仅在 agent 发言**保存入库后**调用。LLM 调用通常耗时 5-30 秒，期间无任何心跳，`check()` 会将此段空闲时间误判为"无活动"，提前进入 `COOLING_DOWN` 状态，导致讨论在 agent 还在发言时被截断。  
**修复**:
- 新增 `keep_alive()` 方法 — 仅重置 `_last_activity` 时间戳，不递增 `message_count`
- 在 `_run_rounds()` 中 `agent_start` 事件推送后立即调用 `self.timer.keep_alive()`
- 同步更新 `heartbeat()` docstring 明确区分：`heartbeat()` = 发言入库后调用（递增计数），`keep_alive()` = 开始生成时调用（仅重置计时）

#### 2. session 切换导致跨会话消息污染

**文件**: `frontend/src/stores/brainstormStore.ts`  
**问题**: `activateSession()` 切换到新 session 时，不清空 `discussionMessages`。切换后原 session 的历史消息仍显示在新 session 的界面上，直到 `loadMessages` 异步请求完成才覆盖，导致用户看到错误内容。  
**修复**: `activateSession()` 的 `set()` 调用中增加：
```ts
discussionMessages: [],
discussionActive: false,
activeAgentId: null,
activeAgentName: null,
activeAgentNumber: null,
streamingContent: "",
```

---

### 🟡 P1 — 代码可维护性问题（强烈建议修复）

#### 3. 旧引擎路径 deprecated 注释不明确

**文件**: `backend/app/routers/brainstorm.py`, `backend/app/services/brainstorm.py`, `frontend/src/stores/brainstormStore.ts`  
**问题**: `_active_engines`、`brainstorm_discuss()`、`abort_discussion()`、`run()` 方法、`startDiscussion()` / `stopDiscussion()` 都是已被 Iter-6 持久连接取代的旧路径，但 deprecated 注释不够醒目，容易被误用。  
**修复**:
- `_active_engines` dict：注释改为 `# DEPRECATED: 仅由 /discuss 端点使用。Iter-7 删除。`
- `brainstorm_discuss()` docstring：改为 `[DEPRECATED — remove in Iter-7] One-shot SSE discussion endpoint.`
- `abort_discussion()` docstring：改为 `[DEPRECATED — remove in Iter-7] Abort a one-shot discussion.`
- `BrainstormEngine.run()` docstring：改为 `[DEPRECATED — remove in Iter-7] One-shot discussion run.` 并说明替代方案
- `startDiscussion()` / `stopDiscussion()` 注释块：增加完整说明（何时删除、替代方案是什么）

#### 4. `startDiscussion` 清空 `discussionMessages` 原因未文档化

**文件**: `frontend/src/stores/brainstormStore.ts`  
**问题**: `startDiscussion()` 中 `set({ discussionActive: true, discussionMessages: [] })` 的 `discussionMessages: []` 让人疑惑——为什么这里要清空？这和 `connectSession` 不清空的行为形成对比，但原因不明。  
**修复**: 增加注释说明：  
> `// NOTE: legacy path clears discussionMessages on each call (each call is a new one-shot SSE).`  
> `// The persistent path (connectSession) does NOT clear here — messages accumulate across injections.`

---

### 📄 P2 — 文档一致性问题

#### 5. spec 存在大段重复内容（约 165 行）

**文件**: `docs/specs/brainstorm/spec.md`  
**问题**: 文件后半段（原 lines 196-360）是 "已实现" 部分的完整复制，同时还包含一份完全错误的旧版迭代计划表（Iter-6 = "彩色线程 UI ⬜"，与实际不符）。  
**修复**: 删除全部重复内容；合并为单一权威"已实现（Iter-4 ~ Iter-6）"节。

#### 6. spec "待实现（Iter-6）" 节 — 描述的是已完成功能

**文件**: `docs/specs/brainstorm/spec.md`  
**问题**: Iter-6 所有功能（持久连接、inject、Reply UI、彩色线程）均已实现，但 spec 中整个 "待实现（Iter-6）" 节仍以未来式描述，迭代计划表中 Iter-6 标记为 `⬜`。  
**修复**: 
- 将 "待实现（Iter-6）" 节内容合并到 "已实现" 节
- 更新迭代计划表：Iter-6 `⬜` → `✅`，Iter-7 补充"删除 deprecated 路径"描述
- 添加 header：`> Iter-6 完成: 2026-05-02`

#### 7. 数据模型字段名错误：`topic` → `title`

**文件**: `docs/specs/brainstorm/spec.md`  
**问题**: spec 数据模型章节写 `topic` 字段，但 `backend/app/models.py` 实际为 `title: Mapped[str]`（最大长度 200），且 `PATCH` API、`BrainstormSessionResponse` schema、前端接口均用 `title`。  
**修复**: spec 数据模型改为 `title (String 200)`，同时列出完整字段集（含 `max_messages`、`cooldown_seconds` 等之前缺失的字段）。

#### 8. SSE 事件表缺失字段

**文件**: `docs/specs/brainstorm/spec.md`  
**问题**:
- `message_done` 载荷缺 `parent_message_id`（代码中实际发送）
- `discussion_end` 载荷缺 `summary: null`（代码中实际发送）
- `user_message` 载荷缺 `parent_message_id`（代码中实际发送）

**修复**: SSE 事件完整列表更新所有 10 个事件的实际载荷，并增加脚注说明 `summary` 当前固定为 `null`。

#### 9. 消息队列行为描述错误：合并 vs. 逐条

**文件**: `docs/specs/brainstorm/spec.md`  
**问题**: 旧 spec 写"队列中所有消息**合并为一条**批量发送"，而实际实现是**逐条发送**：每条消息独立调用 `inject`，各自触发完整的 agent 轮次流程。  
**修复**: 改为"消息**逐条发送**（不合并）：每条消息独立触发一次完整的 inject → agent 轮次流程"。

#### 10. `discussionConnected` 描述错误："替代 discussionActive"

**文件**: `docs/specs/brainstorm/spec.md`  
**问题**: 旧 spec 写 `discussionConnected: boolean // 持久连接是否活跃（替代 discussionActive）`。但实际代码中两者**共存**，语义不同：
- `discussionConnected`：SSE 连接是否活跃（进入 brainstorm 模式即建立）
- `discussionActive`：是否有 agent 正在生成响应（user_message 后 true，discussion_end 后 false）

**修复**: 增加明确的注释块区分两者语义。

#### 11. `keep_alive()` 方法未在 spec 中记录

**文件**: `docs/specs/brainstorm/spec.md`  
**问题**: Iter-6 Review 期间新增了 `keep_alive()` 方法，是 CoolingTimer 状态机理解的关键，但 spec 完全没有提及。  
**修复**: CoolingTimer 节增加 `keep_alive()` 的描述及调用场景。

#### 12. spec 概述仍以"Iter-6 目标"口吻描述已完成功能

**文件**: `docs/specs/brainstorm/spec.md`  
**问题**: 概述末段"**Iter-6 目标**：改为持久连接模型……"以未来式表述已完成的架构。  
**修复**: 改为陈述句，直接描述当前架构，去掉"目标"措辞。

---

## 变更文件索引

| 文件 | 变更类型 | 对应修复 |
|------|----------|----------|
| `backend/app/services/brainstorm.py` | 功能 + 注释 | #1, #3 |
| `backend/app/routers/brainstorm.py` | 注释 | #3 |
| `frontend/src/stores/brainstormStore.ts` | 功能 + 注释 | #2, #3, #4 |
| `docs/specs/brainstorm/spec.md` | 文档重写 | #5, #6, #7, #8, #9, #10, #11, #12 |

---

## 测试验证

```
Backend:  34 passed in 0.58s
Frontend: 36 passed (15 test files)
```

所有既有测试通过，CoolingTimer `keep_alive()` 变更无破坏性。

---

## 未来工作（Iter-7）

- 删除 deprecated 路径：`/discuss` 端点、`run()`、`startDiscussion()`、`stopDiscussion()`
- 补充 `keep_alive()` 的专项单元测试（目前通过集成测试覆盖）
