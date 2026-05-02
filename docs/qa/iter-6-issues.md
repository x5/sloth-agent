# Iter-6 已知问题

Iter-6：持久 SSE 连接模型（`POST /connect` + `POST /inject` + `DELETE /connect`）开发过程中发现的问题。

---

## Open

### #7 集成测试 `test_persistent_connect_inject_streams` 持续挂起

**Severity:** P1  
**Discovered:** 2026-05-03  
**Status:** 🟢 Fixed — 2026-05-03

#### 根因

`httpx.ASGITransport` 不支持真正的流式响应。其 `handle_async_request()` 实现（`_transports/asgi.py:170`）直接 `await self.app(scope, receive, send)`，等待 ASGI app 完成后再将所有 body parts 打包返回（line 185-187）。对于持久 SSE 连接，`run_persistent()` 永远不会返回，因此 `client.stream()` 永远阻塞，`response.aiter_lines()` 永远无法被访问。

#### 修复

创建了 `StreamingASGITransport`（`backend/tests/integration/test_brainstorm.py`），在后台 `asyncio.create_task` 中运行 ASGI app，收到 `http.response.start` 后立即返回 Response，body parts 通过 `asyncio.Queue` 实时流式传输给 `aiter_lines()`。测试中仅 `test_persistent_connect_inject_streams_user_and_agent_events` 使用此 transport，其他测试继续使用 `ASGITransport`（非流式测试不受影响）。

#### 背景

Iter-6 引入了持久 SSE 连接模型：`POST /connect` 建立长连接，`POST /inject` 推送用户消息，`DELETE /connect` 关闭连接。

为此新增了集成测试 `test_persistent_connect_inject_streams_user_and_agent_events`（`backend/tests/integration/test_brainstorm.py`），用于验证完整 happy path：建立连接 → inject 消息 → 接收 SSE 事件 → 断开连接 → 流关闭。

#### 核心流程

```
test (main task)                      reader_task
─────────────────                    ─────────────
await reader_task created            async with client.stream(POST /connect):
await sleep(0) ─────────────────────►  aiter_lines() drives ASGI app
await client.post(/inject) ────────► run_persistent() unblocks, runs rounds
await discussion_ended.wait() ──────► sees discussion_end, sets discussion_ended
await client.delete(/connect) ─────► engine.abort() called, sentinel injected
await stream_closed.wait(5s)   ─────► run_persistent() should exit, stream closes
```

#### 失败症状

测试在 `asyncio.wait_for(stream_closed.wait(), timeout=5.0)` 处超时，说明：

- `discussion_end` 事件**已经**成功接收（`discussion_ended` 被设置）
- `DELETE /connect` 的 `abort()` 被成功调用，sentinel 已被 `put_nowait` 入队
- 但 `run_persistent()` 的 async generator **从未关闭**，HTTP 流没有发出 EOF

#### 根本原因分析

`run_persistent()` 在 `discussion_end` 后回到顶部循环：

```python
while not self._abort:
    content, reply_to = await asyncio.wait_for(queue.get(), timeout=30.0)
    if self._abort:
        break
```

`abort()` 注入 sentinel `("", None)` 后，`queue.get()` 理论上应立即返回。但问题在于 **httpx `ASGITransport` 的异步驱动机制**：

- `aiter_lines()` 读取 response body 的方式是向 ASGI transport 请求 chunk
- ASGI transport 的 `handle_async_request()` 里执行 `await app(scope, receive, send)`
- 整个 `run_persistent()` 作为这个 `await` 的一部分运行
- 当 `run_persistent()` 在 `queue.get()` 上挂起时，`aiter_lines()` 本身也没有新数据可读，进入等待
- sentinel 入队后，**需要 event loop 给 `run_persistent()` 足够的迭代机会**才能消费 sentinel 并退出

在测试的单线程 event loop 中，`stream_closed.wait(5s)` 等待时，event loop 应该能调度：

1. `queue.get()` 的 future 被 resolved（sentinel 在队列里）
2. `run_persistent()` resume → `break` → generator 返回
3. ASGI 发出 `http.response.body {more_body: False}`
4. `aiter_lines()` 收到 EOF → StopAsyncIteration
5. `stream_reader()` 退出 → `stream_closed.set()`

理论上这个链条应该能走通，但实际在测试中始终卡在某一步。

#### 之前错误方向的尝试（均未解决根因）

这些方案均假设 `ASGITransport` 支持流式响应，试图修复应用层逻辑。实际根因在传输层。

| 方案 | 描述 | 结果 |
|------|------|------|
| **方案 A**：直接 `break` 后 disconnect | 在 `discussion_end` 后立即在 `stream_reader` 里 break | 失败 |
| **方案 B**：不 break，自然退出 | `stream_reader` 看到 `discussion_end` 后不 break | 失败 |
| **方案 C**：`create_task` 并发 | 用 `asyncio.create_task(stream_reader())` | 失败 |

#### 修复代码

- `StreamingASGITransport` 类：`backend/tests/integration/test_brainstorm.py`（约 100 行）
- 运行 `app(scope, receive, send)` 在 `asyncio.create_task` 后台任务中
- 收到 `http.response.start` 后立即返回 Response
- body parts 通过 `asyncio.Queue` 实时流式传输
- `_QueueStream(AsyncByteStream)` 提供标准 httpx 流接口给 `aiter_lines()`
- 仅用于 SSE 持久连接测试，不修改 `engine.abort()` / `run_persistent()` 等业务逻辑
