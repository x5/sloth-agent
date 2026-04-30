# 飞书接口对接设计规格

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 待审批

---

## 1. 需求描述

### 1.1 问题

现有飞书集成只有审批通道（`human/review.py` 中的 webhook 推送），不支持：
- 用户通过飞书发送消息与 Agent 对话
- Agent 通过飞书回复消息
- 飞书卡片交互触发 workflow 操作
- 飞书 session 与 CLI session 的统一管理

### 1.2 目标

| 版本 | 能力 | 说明 |
|------|------|------|
| **v1.0** | 飞书 Webhook Server | 接收飞书消息，转发到 ChatSession 处理，回复飞书 |
| **v1.1** | 飞书卡片交互 | 审批卡片、状态卡片、工作流控制卡片 |
| **v1.2** | 飞书 session 管理 | 飞书 session 与 CLI session 统一管理，支持多用户 |

---

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                       飞书用户                              │
└───────────────┬─────────────────────────┬───────────────────┘
                │                         │
                │ 发送消息                 │ 点击卡片按钮
                ▼                         ▼
┌───────────────────────────┐  ┌─────────────────────────────┐
│ 飞书 Webhook (HTTP POST)  │  │ 飞书 Card Callback (HTTP)   │
│ /feishu/webhook           │  │ /feishu/card-callback       │
└───────────┬───────────────┘  └────────────┬────────────────┘
            │                               │
            ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  FeishuServer (FastAPI)                      │
├─────────────────────────────────────────────────────────────┤
│  1. 验证请求签名                                              │
│  2. 解析消息内容                                              │
│  3. 创建/恢复 Session                                        │
│  4. 转发到 ChatSession 处理                                   │
│  5. 通过飞书 API 回复用户                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  ChatSession (共享)                          │
│  - 复用 CLI chat 的对话逻辑                                   │
│  - 区别：输入/输出是飞书消息格式，不是终端 I/O                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Memory (sessions/feishu-{user_id}/)             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 与现有审批通道的关系

```
现有（review.py）:
  Agent → Feishu Webhook → 用户收到审批卡片
  用户点击 → Webhook 回调 → 状态文件更新 → Agent 轮询检查

新增（feishu_server.py）:
  用户 → 飞书消息 → Webhook Server → ChatSession 处理 → 回复飞书
  用户 → 点击卡片 → Card Callback → 触发 workflow 操作

两者互补：
  - 审批通道: Agent 主动推送到飞书
  - 对话通道: 用户主动从飞书发起
```

---

## 3. 模块定义

### 3.1 FeishuServer

**文件**: `src/cli/feishu_server.py`（新增）

```
职责: FastAPI 应用，处理飞书 Webhook 和 Card Callback
```

**路由**:

| 路由 | 方法 | 说明 |
|------|------|------|
| `/feishu/webhook` | POST | 接收飞书消息 |
| `/feishu/card-callback` | POST | 接收飞书卡片回调 |
| `/feishu/health` | GET | 健康检查 |

**核心流程（消息处理）**:

```
1. 接收 POST 请求
   → 验证签名（challenge-response 或 token 验证）

2. 解析消息
   → 提取 user_id, message_content, message_type

3. 查找/创建 Session
   → SessionManager.load_session(f"feishu-{user_id}")
   → 如果不存在，创建新 session

4. 处理消息
   → ChatSession.process_message(message_content)
   → LLM 响应

5. 回复用户
   → 通过飞书消息 API 发送回复
   → 更新 session metadata
```

### 3.2 FeishuClient

**文件**: `src/providers/feishu_client.py`（新增）

```
职责: 飞书 API 客户端，发送消息和卡片
```

**核心方法**:

| 方法 | 说明 |
|------|------|
| `send_message(user_id, content)` | 发送文本消息 |
| `send_card(user_id, card)` | 发送交互卡片 |
| `update_card(token, card)` | 更新已发送的卡片 |
| `get_user_info(open_id)` | 获取用户信息 |

### 3.3 配置扩展

**文件**: `src/core/config.py`（新增字段）

```python
class FeishuConfig(BaseModel):
    app_id: str = ""
    app_secret: str = ""
    webhook: str = ""
    verification_token: str = ""
    encrypt_key: str = ""
    enabled: bool = False
```

---

## 4. 飞书消息格式

### 4.1 Webhook 消息（用户发送到机器人）

```json
{
  "open_id": "ou_xxx",
  "message_type": "text",
  "content": {
    "text": "帮我 review 这段代码"
  },
  "message_id": "om_xxx",
  "create_time": "1234567890"
}
```

### 4.2 回复消息（Agent 发送给用户）

```json
{
  "receive_id_type": "open_id",
  "receive_id": "ou_xxx",
  "msg_type": "text",
  "content": "{\"text\": \"好的，我来看看...\"}"
}
```

### 4.3 审批卡片

```json
{
  "msg_type": "interactive",
  "card": {
    "header": {
      "title": {"tag": "plain_text", "content": "日计划审批"},
      "template": "blue"
    },
    "elements": [
      {"tag": "div", "text": {"tag": "lark_md", "content": "...任务列表..."}},
      {"tag": "action", "actions": [
        {"tag": "button", "text": {"tag": "plain_text", "content": "通过"}, "type": "primary", "action_id": "approve"},
        {"tag": "button", "text": {"tag": "plain_text", "content": "拒绝"}, "type": "danger", "action_id": "reject"}
      ]}
    ]
  }
}
```

---

## 5. 安全

### 5.1 请求验证

- 使用飞书 `verification_token` 验证请求来源
- 如果使用加密模式，使用 `encrypt_key` 解密消息体

### 5.2 访问控制

- 只允许配置的飞书用户 ID 与 Agent 对话
- 未在白名单的用户返回默认提示

---

## 6. Session 管理

飞书 session 与 CLI session 共享同一套 SessionManager：

```
memory/
├── sessions/
│   ├── chat-20260416-100000-a1b2/    # CLI session
│   │   ├── chat.jsonl
│   │   ├── context.json
│   │   └── metadata.json
│   └── feishu-ou_xxx/                # 飞书 session（按用户 ID）
│       ├── chat.jsonl
│       ├── context.json
│       └── metadata.json
└── ...
```

飞书 session 的 metadata 中记录 `mode: "feishu"` 以便区分。

---

## 7. 启动方式

```bash
# 独立启动飞书 server
uv run python -m sloth_agent.cli.feishu_server

# 或作为 sloth 子命令
sloth feishu
```

### 7.1 配置要求

```yaml
# configs/agent.yaml
feishu:
  app_id: "${FEISHU_APP_ID}"
  app_secret: "${FEISHU_APP_SECRET}"
  webhook: "${FEISHU_WEBHOOK}"
  verification_token: "${FEISHU_VERIFICATION_TOKEN}"
  encrypt_key: "${FEISHU_ENCRYPT_KEY}"
  enabled: true
```

---

## 8. 文件结构

```
src/
  cli/
    feishu_server.py         # 新增，FastAPI 应用
  providers/
    feishu_client.py         # 新增，飞书 API 客户端
  core/
    config.py                # 修改，添加 FeishuConfig
configs/
  agent.yaml                 # 修改，添加 feishu 配置段
pyproject.toml               # 修改，添加 fastapi, uvicorn 依赖
tests/
  cli/
    test_feishu_server.py    # 新增
  providers/
    test_feishu_client.py    # 新增
```

---

## 9. 依赖变更

| 依赖 | 版本 | 说明 |
|------|------|------|
| fastapi | >= 0.100.0 | 新增，Webhook server |
| uvicorn | >= 0.23.0 | 新增，ASGI server |
| httpx | 已有 | 飞书 API 调用（已有依赖） |

---

## 10. 测试策略

| 测试 | 说明 |
|------|------|
| `test_webhook_receive_message` | 接收飞书消息，正确解析 |
| `test_webhook_verify` | 请求签名验证通过 |
| `test_send_message` | 通过 API 发送消息 |
| `test_send_card` | 发送交互卡片 |
| `test_card_callback` | 处理卡片回调 |
| `test_feishu_session` | 飞书 session 创建和消息保存 |

---

## 11. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 飞书 API 限流 | 消息发送失败 | 重试 + 指数退避 |
| Webhook 未配置公网地址 | 消息无法接收 | 提供 ngrok 开发模式 |
| 消息体过大 | 飞书拒绝 | 截断回复，分多条发送 |
| 多用户并发消息 | Session 冲突 | 每个用户独立 session ID |

---

*规格版本: v1.0.0*
*创建日期: 2026-04-16*
