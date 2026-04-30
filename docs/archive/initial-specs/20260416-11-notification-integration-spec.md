# 通知与集成规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

多个 spec 中零散提到外部集成：
- 安装 spec 提到飞书和 SMTP 配置
- 安全 spec 提到飞书 webhook 告警
- 报告 spec 提到多渠道交付

但缺乏统一的集成层，导致每个需要通知的模块重复实现发送逻辑。

需要解决的问题：
1. 统一的 Notification Provider 接口
2. 通知路由（什么事件发到什么渠道）
3. 消息去重和限流
4. 模板化消息体

---

## 2. 通知渠道

### 2.1 支持渠道

| 渠道 | 优先级 | 用途 | 交互能力 |
|------|--------|------|---------|
| **飞书卡片** | P0 | 日报、报告、一般通知 | ✅ 按钮交互 |
| **飞书告警** | P0 | 安全事件、异常告警 | ❌ 单向 |
| **邮件** | P1 | 正式报告、周报 | ❌ 单向 |
| **Webhook** | P1 | 自定义集成 | ❌ 单向 |
| **文件** | P0 | 所有报告、审计日志 | ❌ 存储 |

### 2.2 通知优先级

```python
class NotificationPriority(Enum):
    CRITICAL = "critical"    # 立即发送，不受免打扰限制
    HIGH = "high"            # 立即发送
    NORMAL = "normal"        # 正常发送
    LOW = "low"              # 合并发送（减少打扰）
```

---

## 3. 通知数据模型

```python
@dataclass
class Notification:
    """通知消息。"""
    notification_id: str
    priority: NotificationPriority
    title: str
    body: str
    event_type: str            # 关联的事件类型
    category: str              # 通知分类
    timestamp: float
    metadata: dict = field(default_factory=dict)
    actions: list[dict] = field(default_factory=list)  # 交互按钮
    dedup_key: str | None = None  # 去重键


@dataclass
class NotificationRule:
    """通知路由规则。"""
    rule_id: str
    event_pattern: str         # 事件类型模式（支持通配符）
    priority: NotificationPriority
    channels: list[str]        # 目标渠道
    time_window: tuple[str, str] | None = None  # 生效时间窗口
    throttle_seconds: int = 0  # 同一通知最小间隔
    enabled: bool = True


# 默认通知路由规则
DEFAULT_RULES = [
    NotificationRule(
        rule_id="critical-errors",
        event_pattern="*.critical",
        priority=NotificationPriority.CRITICAL,
        channels=["feishu_alert", "file"],
        throttle_seconds=300,
    ),
    NotificationRule(
        rule_id="security-events",
        event_pattern="security.*",
        priority=NotificationPriority.HIGH,
        channels=["feishu_alert", "file"],
        throttle_seconds=60,
    ),
    NotificationRule(
        rule_id="daily-reports",
        event_pattern="report.daily",
        priority=NotificationPriority.NORMAL,
        channels=["feishu_card", "file"],
        throttle_seconds=0,
    ),
    NotificationRule(
        rule_id="phase-failures",
        event_pattern="phase.gate.fail",
        priority=NotificationPriority.HIGH,
        channels=["feishu_alert", "file"],
        throttle_seconds=120,
    ),
    NotificationRule(
        rule_id="budget-warnings",
        event_pattern="budget.*",
        priority=NotificationPriority.NORMAL,
        channels=["feishu_card", "file"],
        throttle_seconds=600,
    ),
]
```

---

## 4. 通知管理器

```python
class NotificationManager:
    """统一通知管理器。

    所有模块通过此接口发送通知，
    自动路由到正确的渠道。
    """

    def __init__(self, config: Config):
        self.config = config
        self.channels = self._init_channels()
        self.rules = config.notification.rules or DEFAULT_RULES
        self.sent_history: deque[tuple[str, float]] = deque(maxlen=1000)
        self.low_priority_buffer: list[Notification] = []
        self.flush_interval = 300  # 5 分钟合并发送低优先级通知

    def send(self, notification: Notification) -> list[DeliveryResult]:
        """发送通知。"""
        # 1. 去重检查
        if notification.dedup_key:
            if self._is_duplicate(notification.dedup_key):
                return [DeliveryResult(
                    channel="dedup",
                    success=False,
                    note="Duplicate notification suppressed",
                )]

        # 2. 路由匹配
        matched_rules = self._match_rules(notification.event_type)
        if not matched_rules:
            return [DeliveryResult(
                channel="none",
                success=False,
                note="No matching notification rule",
            )]

        # 3. 限流检查
        for rule in matched_rules:
            if self._is_throttled(notification, rule):
                return [DeliveryResult(
                    channel="throttle",
                    success=False,
                    note=f"Throttled by rule {rule.rule_id}",
                )]

        # 4. 低优先级合并
        if notification.priority == NotificationPriority.LOW:
            self.low_priority_buffer.append(notification)
            return [DeliveryResult(
                channel="buffered",
                success=True,
                note="Queued for batch delivery",
            )]

        # 5. 发送
        results = []
        for rule in matched_rules:
            for channel_name in rule.channels:
                channel = self.channels.get(channel_name)
                if channel:
                    result = channel.send(notification)
                    results.append(result)

        # 记录历史
        if notification.dedup_key:
            self.sent_history.append(
                (notification.dedup_key, time.time())
            )

        return results

    def flush_low_priority(self) -> list[DeliveryResult]:
        """合并发送低优先级通知。"""
        if not self.low_priority_buffer:
            return []

        # 合并为一条通知
        merged = Notification(
            notification_id=uuid4().hex[:12],
            priority=NotificationPriority.NORMAL,
            title=f"{len(self.low_priority_buffer)} low-priority notifications",
            body="\n".join(
                f"- {n.title}" for n in self.low_priority_buffer
            ),
            event_type="batch",
            category="system",
            timestamp=time.time(),
        )

        results = self.send(merged)
        self.low_priority_buffer.clear()
        return results
```

---

## 5. 渠道适配器

### 5.1 飞书适配器

```python
class FeishuChannel:
    """飞书通知渠道。"""

    def __init__(self, config: FeishuConfig):
        self.app_id = config.app_id
        self.app_secret = config.app_secret
        self.webhook_url = config.webhook_url
        self.chat_id = config.chat_id

    def send(self, notification: Notification) -> DeliveryResult:
        """发送飞书消息。"""
        if notification.priority in (
            NotificationPriority.CRITICAL,
            NotificationPriority.HIGH,
        ):
            return self._send_alert(notification)
        else:
            return self._send_card(notification)

    def _send_alert(self, notification: Notification) -> DeliveryResult:
        """发送告警（通过 Webhook）。"""
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": f"🚨 {notification.title}",
                    },
                    "template": "red",
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": notification.body,
                        },
                    },
                    {
                        "tag": "note",
                        "elements": [{
                            "tag": "plain_text",
                            "content": (
                                f"Sloth Agent | "
                                f"{datetime.fromtimestamp(notification.timestamp):%H:%M:%S}"
                            ),
                        }],
                    },
                ],
            },
        }

        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10,
        )

        return DeliveryResult(
            channel="feishu_alert",
            success=response.status_code == 200,
            status_code=response.status_code,
        )

    def _send_card(self, notification: Notification) -> DeliveryResult:
        """发送交互卡片。"""
        elements = [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": notification.body,
                },
            },
        ]

        # 添加交互按钮
        if notification.actions:
            action_elements = []
            for action in notification.actions:
                action_elements.append({
                    "tag": "action",
                    "actions": [{
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": action["label"]},
                        "type": action.get("type", "primary"),
                        "url": action.get("url", ""),
                        "value": action.get("value", {}),
                    }],
                })
            elements.extend(action_elements)

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": notification.title,
                    },
                    "template": self._priority_to_template(notification.priority),
                },
                "elements": elements,
            },
        }

        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10,
        )

        return DeliveryResult(
            channel="feishu_card",
            success=response.status_code == 200,
            status_code=response.status_code,
        )
```

### 5.2 邮件适配器

```python
class EmailChannel:
    """邮件通知渠道。"""

    def __init__(self, config: EmailConfig):
        self.smtp_host = config.smtp_host
        self.smtp_port = config.smtp_port
        self.smtp_user = config.smtp_user
        self.smtp_password = config.smtp_password
        self.recipients = config.recipients

    def send(self, notification: Notification) -> DeliveryResult:
        """发送邮件。"""
        msg = MIMEText(notification.body, "plain", "utf-8")
        msg["Subject"] = notification.title
        msg["From"] = self.smtp_user
        msg["To"] = ", ".join(self.recipients)

        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(
                    self.smtp_user,
                    self.recipients,
                    msg.as_string(),
                )
            return DeliveryResult(
                channel="email",
                success=True,
            )
        except Exception as e:
            return DeliveryResult(
                channel="email",
                success=False,
                error=str(e),
            )
```

### 5.3 Webhook 适配器

```python
class WebhookChannel:
    """通用 Webhook 通知渠道。"""

    def __init__(self, config: WebhookConfig):
        self.url = config.url
        self.headers = config.headers or {}
        self.method = config.method or "POST"

    def send(self, notification: Notification) -> DeliveryResult:
        """发送 Webhook 请求。"""
        payload = {
            "notification_id": notification.notification_id,
            "title": notification.title,
            "body": notification.body,
            "priority": notification.priority.value,
            "event_type": notification.event_type,
            "timestamp": notification.timestamp,
            "metadata": notification.metadata,
        }

        response = requests.request(
            self.method,
            self.url,
            json=payload,
            headers=self.headers,
            timeout=10,
        )

        return DeliveryResult(
            channel="webhook",
            success=200 <= response.status_code < 300,
            status_code=response.status_code,
        )
```

---

## 6. 配置

```yaml
# configs/notification.yaml
notification:
  channels:
    feishu:
      enabled: true
      webhook_url: "${FEISHU_WEBHOOK_URL}"
      chat_id: ""

    email:
      enabled: false
      smtp_host: "${SMTP_HOST}"
      smtp_port: 587
      smtp_user: "${SMTP_USER}"
      smtp_password: "${SMTP_PASSWORD}"
      recipients: []

    webhook:
      enabled: false
      url: ""
      method: "POST"
      headers: {}

  rules:
    # 可在运行时动态添加/删除规则
    - rule_id: "critical-errors"
      event_pattern: "*.critical"
      priority: "critical"
      channels: ["feishu_alert", "file"]
      throttle_seconds: 300

    - rule_id: "daily-reports"
      event_pattern: "report.daily"
      priority: "normal"
      channels: ["feishu_card", "file"]

  do_not_disturb:
    enabled: true
    hours: "22:00-08:00"        # 免打扰时段
    except_priorities:           # 免打扰期间仍发送的优先级
      - "critical"

  batching:
    low_priority_merge: true     # 低优先级通知合并
    merge_interval_seconds: 300  # 5 分钟合并一次
    max_batch_size: 20           # 最多合并 20 条
```

---

## 7. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/integration/__init__.py` | 集成模块入口 |
| `src/sloth_agent/integration/notification_manager.py` | NotificationManager 通知管理器 |
| `src/sloth_agent/integration/feishu.py` | FeishuChannel 飞书适配器 |
| `src/sloth_agent/integration/email.py` | EmailChannel 邮件适配器 |
| `src/sloth_agent/integration/webhook.py` | WebhookChannel Webhook 适配器 |
| `src/sloth_agent/integration/models.py` | 通知数据模型 |
| `configs/notification.yaml` | 通知配置 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
