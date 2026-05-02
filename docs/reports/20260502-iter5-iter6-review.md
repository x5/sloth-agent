# Iter-5 & Iter-6 架构/代码 Review

> 日期: 2026-05-02
> 范围: `docs/plans/20260425-mvp-desktop-app-plan.md` Iter-5 (讨论引擎) + Iter-6 (持久连接 + Reply + 彩色线程)
> 对照文档:
> - `docs/specs/brainstorm/spec.md` — Brainstorm 模式 Spec（权威）
> - `docs/specs/chat/spec.md` — 对话模式 Spec
> - `docs/plans/20260425-mvp-desktop-app-plan.md` — MVP Plan
> 审查文件:
> - `backend/app/services/brainstorm.py` — BrainstormEngine + CoolingTimer
> - `backend/app/routers/brainstorm.py` — SSE 端点 (discuss / connect / inject)
> - `frontend/src/stores/brainstormStore.ts` — 前端状态管理
> - `frontend/src/components/ChatArea.tsx` — 消息渲染 + 交互
> - `frontend/src/utils/threadColor.ts` — 线程颜色计算
> - `backend/app/models.py` — 数据模型

---

## A. Spec 交叉审查

> 对照 `docs/specs/brainstorm/spec.md` 逐项检查。Spec 是权威文档，Plan 是执行计划。

### A1. Spec 状态过期 — Iter-6 标记 ⬜ 但代码已实现

**严重程度: HIGH (文档)**

Spec 迭代计划表 (line 175) 仍标记 `Iter-6 | 持久连接 + Reply + 彩色线程 | ⬜`，但以下 Iter-6 功能已在代码中实现:
- `POST /connect` + `POST /inject` + `DELETE /connect` 端点
- `connectSession` / `disconnectSession` / `injectMessage` store 方法
- Reply 按钮 + 引用条
- `threadColor.ts` + 彩色竖线

Spec 的 "待实现（Iter-6）" 章节 (line 77-166) 也应移到 "已实现"。

### A2. Spec 重复内容 — 两处几乎相同的章节

**严重程度: MEDIUM (文档)**

Spec 包含两个几乎相同的章节块:
- **块 1** (line 14-74): "已实现（Iter-4 ~ Iter-5）" — SSE 事件表、Store 方法、聊天集成
- **块 2** (line 196-282): 同样内容的重复（SSE 事件表、Store 方法、聊天集成、RightPanel）

块 2 看起来是旧版内容未清理。两处的 SSE 事件表、Store 方法列表完全一致。

### A3. Plan vs Spec — TwoRoundVoting 是 Plan 独有，不在 Spec 中

**严重程度: INFO (澄清)**

原始 review 第 1 点指出 Plan 的 `DecisionStrategy` + `TwoRoundVoting` 未实现。但交叉对照后发现: **Spec 中从未定义 TwoRoundVoting**。Spec 描述的是 "多轮循环架构"（`while sub_round < MAX_ROUNDS`），这与实现一致。

结论: Plan 中的 TwoRoundVoting 是一个过度设计的方案，Spec 在某个时间点已经将其简化为多轮循环。Plan 和 Spec 之间存在分歧，应以 Spec 为准。**原 review 第 1 点降级为 Plan-Spec 分歧，非 Spec 违规。**

### A4. Plan vs Spec — SSE 事件数量差异已澄清

**严重程度: INFO (澄清)**

Plan 定义 13 种 SSE 事件，Spec 定义 7 种。实现与 Spec 一致（7 种）+ Iter-6 新增 3 种（`user_message`, `round_end`, `heartbeat`）= 共 10 种。Plan 中的 `agent_intent`、`cooldown_start/reset/confirm`、`round_aborted` 不在 Spec 中。**原 review 第 2 点降级为 Plan-Spec 分歧。**

### A5. Spec vs 实现 — 消息队列行为不一致

**严重程度: MEDIUM**

Spec (brainstorm/spec.md line 230-231):
> 系统响应完成后，队列中所有消息合并为一条批量发送

但 Chat Spec (chat/spec.md line 33) 说:
> 队列逐条发送（不合并），每条独立触发一次完整的 LLM 请求

实现遵循 Chat Spec（逐条发送），不遵循 Brainstorm Spec（合并发送）。**两个 Spec 对队列行为的定义互相矛盾。** 需要统一。

### A6. Spec vs 实现 — `run()` 未重构，`run_persistent()` 是新增

**严重程度: MEDIUM**

Spec (line 118):
> `run()` 改为持久 queue-driven 循环（`asyncio.Queue`）

实际: `run()` 保持原样（one-shot），新增了 `run_persistent()`。Spec 说的是"改"，实现是"加"。这导致两套引擎逻辑并存，与 review 第 3 点（旧引擎未废弃）重叠。

### A7. Spec vs 实现 — `discussionConnected` 未替代 `discussionActive`

**严重程度: MEDIUM**

Spec (line 136):
> `discussionConnected: boolean` // 持久连接是否活跃（**替代** `discussionActive`）

实际: 两者共存。`discussionActive` 由 `user_message` handler 设置为 true（line 128），由 `discussion_end` / `error` / `max_reached` 设置为 false。`discussionConnected` 由 `connectSession` / `disconnectSession` 管理。前端同时检查两者（`ChatArea.tsx:610`）。

Spec 说"替代"，但实现是"并存"。`discussionActive` 在 persistent 模式下仍被使用，语义模糊。

### A8. Spec vs 实现 — BrainstormSession 字段名 `topic` vs `title`

**严重程度: LOW**

Spec (line 52):
> `BrainstormSession` — id, inspiration_id, **topic**, status, sandbox_path

实际 model (`models.py:87`): 使用 `title` 而非 `topic`。Router 和 store 也使用 `title`。Spec 未同步更新。

### A9. Spec vs 实现 — `discussion_end` 载荷含额外 `summary` 字段

**严重程度: LOW**

Spec (line 41):
> `discussion_end` | `message_count, round` | 讨论结束

实际 (`brainstorm.py:416`): `{summary: None, message_count, round}`。多了 `summary` 字段（当前固定为 None，Iter-9 才填充）。不影响功能，但 Spec 应包含此字段。

### A10. Spec vs 实现 — Agent 队列优先级处理缺失

**严重程度: MEDIUM**

Spec (line 120):
> 每个 agent 发言结束后检查 queue 是否有新消息，有则优先处理（结束当前轮，启动新轮）

实际 (`brainstorm.py:386`):
```python
if not self._queue.empty():
    break
```

实现只是 `break` 退出 agent 循环，然后回到 `run_persistent()` 的外层循环取下一条消息。没有 "启动新轮" 的显式逻辑——只是隐式地通过循环回到 `queue.get()` 实现。功能上接近，但 round 管理不清晰: `break` 后 `_run_rounds` 直接 yield `round_end` 然后退出，round number 的递增依赖 `_get_current_round()` 从 DB 查询。如果 queue 中有多条消息快速到达，round number 可能不连续。

---

## 原始 Review（Plan vs 实现）

> 以下为对照 Plan 文档的原始发现。经 Spec 交叉审查后，第 1、2 点已降级为 Plan-Spec 分歧。

### 1. Plan vs 实现 — TwoRoundVoting 未实现（Plan-Spec 分歧）

**严重程度: HIGH**

**Plan (Task 5.1)** 定义了:
- `DecisionStrategy` ABC 接口（`collect_intents` + `generate_speeches`）
- `TwoRoundVoting`：Round 1 收集意向（`max_tokens=20`），Round 2 YES 的 agent 并行流式发言
- Lead Agent 不参与 Round 1/2，负责轮次总结

**实际实现**: 完全没有这些。用的是顺序 agent 发言 + `MAX_ROUNDS=8` 多轮循环。没有 `DecisionStrategy`，没有意向收集，没有并行发言。Lead Agent 和其他 agent 走同样的发言逻辑。

**影响**: 架构可扩展性的核心承诺（`DecisionStrategy` ABC 支持未来替换投票策略）落空。

---

## 2. Plan vs 实现严重偏离 — SSE 事件类型大幅缺失

**严重程度: HIGH**

Plan 定义了 **13 种** SSE 事件，实际只实现了 **7 种**:

| Plan 事件 | 状态 | 说明 |
|---|---|---|
| `agent_intent` | ❌ 缺失 | Round 1 意向，因 TwoRoundVoting 未实现 |
| `cooldown_start` | ❌ 缺失 | 冷却开始通知 |
| `cooldown_reset` | ❌ 缺失 | 冷却重置通知 |
| `cooldown_confirm` | ❌ 缺失 | 确认阶段通知 |
| `round_aborted` | ❌ 缺失 | 用户中断通知 |
| `message_token` | ⚠️ 改名 | 实际叫 `agent_token` |
| `user_message` | ✅ 新增 | Plan 未定义，Iter-6 新增 |
| `round_end` | ✅ 新增 | Plan 未定义，Iter-6 新增 |
| `heartbeat` | ✅ 新增 | Plan 未定义，Iter-6 新增 |
| `agent_start` | ✅ | |
| `message_done` | ✅ | |
| `agent_pass` | ✅ | |
| `discussion_end` | ✅ | |
| `max_reached` | ✅ | |
| `error` | ✅ | |

冷却状态变化对前端 UX 至关重要（Plan Task 5.3 明确要求 "讨论状态指示器：冷却中..."），但前端完全没有冷却状态展示。

---

## 3. Iter-6 架构目标未达成 — 旧引擎未废弃

**严重程度: HIGH**

**Plan (Task 6.0)** 明确说:
> 原 `discuss` 端点保留但标注 deprecated，Iter-7 删除

**实际**:
- `_active_engines` (旧) 和 `_active_connections` (新) 两个 dict 共存
- 前端 `sendOne()` 有完整两条路径：`discussionConnected` → inject，否则 → 旧 `startDiscussion`
- `waitForDiscussionIdle()` 仍然存在，用于旧路径

这不是 "deprecated"，是完全并行运行。旧路径的存在意味着新架构没有被真正依赖。

---

## 4. CoolingTimer 语义问题 — LLM 延迟可能导致误触发

**严重程度: MEDIUM**

```python
# brainstorm.py:97-100
if self.state == TimerState.RUNNING:
    if idle >= self.cooldown_seconds:  # idle = now - _last_activity
        self.state = TimerState.COOLING_DOWN
```

`heartbeat()` 在每次非 PASS 发言后调用，所以冷却只在所有 agent 都 PASS 后才开始计时。这可能是正确行为，但存在一个边界问题：

- `run_persistent()` 中用户消息也调用 `self.timer.heartbeat()`（line 497）
- 如果 LLM 调用本身超过 `cooldown_seconds`（默认 5s），冷却会在 agent 响应期间错误触发
- 实际 LLM 调用延迟经常超过 5s，特别是流式生成完整回复时

---

## 5. 前端状态管理混乱 — `discussionMessages` 永不清理

**严重程度: MEDIUM**

在 persistent 模式下:
- `connectSession()` 不清空 `discussionMessages`
- `_handleSSEEvent` 的 `discussion_end` handler 不清空
- 切换 brainstorm session 时，`activateSession()` 不清空

结果: `discussionMessages` 在整个 brainstorm 生命周期内无限累积。`prevDiscussionCountRef` 机制把增量追加到 `messages`，但 `discussionMessages` 本身从不重置。

---

## 6. Agent 列表在 persistent 连接期间不刷新

**严重程度: MEDIUM**

```python
# brainstorm.py:467 — run_persistent()
agents = await self._load_agents()  # 只在连接建立时加载一次
```

如果用户在讨论进行中添加/移除 Team Agent，`run_persistent()` 不会感知。Plan 没有明确这个边界，但 UX 上用户期望 "Add Agent → 立即参与讨论"。

---

## 7. `threadColor.ts` 算法与 Plan 不一致

**严重程度: LOW**

Plan (Task 6.3) 说的是 **djb2 hash**:
> 根据根 ID 生成色相（djb2 hash % 360）

实际实现用的是 **FNV-1a**（offset basis `2166136261`，prime `16777619`）。不影响功能，但说明实现时没有严格对照 Plan。

---

## 8. `getRootId()` 缺少深度限制和正确的循环检测

**严重程度: MEDIUM**

```typescript
while (true) {
  const parent = map.get(current);
  if (!parent || visited.has(current)) return current;
  visited.add(current);
  current = parent;
}
```

问题:
1. 循环检测语义不正确：检测到循环时返回当前节点，而非报错或返回 `null`
2. 无深度限制：如果 DB 数据有长链，遍历可能很慢
3. 性能问题：每次渲染 `DisplayItems` 时，对每条有 `parent_message_id` 的消息都调用 `getRootId()`，每次都重建 `Map`。100 条消息 = 100 次 Map 构建 + 100 次链遍历

---

## 9. 硬编码后端 URL — 两套 HTTP 客户端并存

**严重程度: MEDIUM**

```typescript
// brainstormStore.ts:6
const BACKEND = "http://127.0.0.1:8080";
```

`connectSession`、`disconnectSession`、`injectMessage` 直接用 `fetch()` + 硬编码 URL。但 `client.ts` 中的其他 API 调用通过 Tauri `invoke` 走 Rust proxy。

两套 HTTP 客户端并存意味着:
- 错误处理不统一
- 认证/拦截器逻辑不共享
- 端口配置散落多处

---

## 10. ChatArea.tsx 835 行 — 组件职责过载

**严重程度: MEDIUM**

ChatArea 同时承担:
- Chat 模式（SSE 流式）
- Brainstorm 模式（persistent connection）
- 消息队列管理
- 分隔线渲染
- Reply 引用条
- 思考气泡
- TopBar 状态展示

没有拆分。Brainstorm 相关逻辑应独立为 `BrainstormChatArea` 或至少 `useBrainstormChat` hook。

---

## 11. `startDiscussion()` 清空 `discussionMessages` — 与 persistent 模式行为不一致

**严重程度: LOW**

```typescript
// brainstormStore.ts:410
set({ discussionActive: true, discussionMessages: [] });
```

旧路径每次调用都清空。Persistent 模式不清空。两条路径的消息保留策略不一致，如果将来完全切到 persistent 模式，旧的分隔线/增量逻辑可能需要调整。

---

## 12. `intent` 字段定义但从未使用

**严重程度: LOW**

`Message` model 有 `intent: str | None`（Plan Task 5.0），BrainstormEngine 的 `_save_message()` 从不设置它。`_handleSSEEvent` 的 `user_message` case 硬编码 `intent: null`。这个字段是为 TwoRoundVoting 的 Round 1 设计的，但 TwoRoundVoting 未实现。

---

## 总结

| 类别 | 数量 | 说明 |
|---|---|---|
| Spec 状态过期 | 1 | Iter-6 标记 ⬜ 但代码已实现 |
| Spec 文档问题 | 2 | 重复内容、字段名不同步 |
| Spec vs 实现 | 4 | 队列行为、run() 未重构、discussionConnected 未替代、队列优先级 |
| Plan-Spec 分歧 | 2 | TwoRoundVoting、SSE 事件数量（Plan 过度设计，Spec 已简化）|
| 架构问题 | 4 | 状态不清空、agent 不刷新、timer 语义、双引擎并存 |
| 代码质量 | 3 | 组件过载、硬编码 URL、算法与 Plan 不一致 |
| 数据完整性 | 2 | 未使用字段、循环检测语义 |

### 核心结论

1. **Plan 和 Spec 之间存在分歧**: Plan 定义了 TwoRoundVoting + 13 种 SSE 事件，Spec 简化为多轮循环 + 7 种事件。实现遵循 Spec，Plan 需要更新以消除分歧。
2. **实现与 Spec 基本一致，但有 4 处偏离**: 队列行为（Spec 说合并，实现逐条）、`run()` 未重构、`discussionConnected` 未替代 `discussionActive`、agent 队列优先级处理模糊。
3. **持久连接叠加在旧架构上**: 旧路径未废弃，两套引擎并存。
4. **Spec 文档本身需要维护**: 重复内容、状态过期、字段名不同步。

### 建议修复优先级

1. **P0 — 同步 Spec 和 Plan**: 更新 Plan 移除 TwoRoundVoting（或更新 Spec 加入），消除两份文档的分歧
2. **P0 — 更新 Spec 状态**: Iter-6 标记为 ✅，清理重复章节
3. **P0 — 移除旧路径**: 删除 `_active_engines`、`startDiscussion`、`stopDiscussion`、`waitForDiscussionIdle`，强制走 persistent 模式
4. **P0 — 修复 CoolingTimer**: LLM 调用期间不应触发冷却（需要区分 "agent 正在生成" 和 "无人发言"）
5. **P1 — 统一队列行为**: Brainstorm Spec 和 Chat Spec 对队列的定义矛盾，需选择一种并统一
6. **P1 — 清理 `discussionMessages`**: 切换 session / 断开连接时重置
7. **P1 — `discussionConnected` 替代 `discussionActive`**: 按 Spec 原意，persistent 模式下只用 `discussionConnected`
8. **P2 — 拆分 ChatArea**: 提取 brainstorm 相关逻辑到独立 hook 或组件
9. **P2 — 统一 HTTP 客户端**: brainstormStore 中的 `fetch()` 改为走 `client.ts` 的统一通道
10. **P3 — `getRootId` 性能**: 传入预构建的 Map，加深度限制
11. **P3 — 清理未使用字段**: `intent` 字段在投票策略实现前标记 reserved
