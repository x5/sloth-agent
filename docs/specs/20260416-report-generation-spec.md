# 报告生成规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

Phase-Role Architecture spec 定义了 Phase 8（SRE 报告阶段），Daemon spec 有 `_run_report_phase()` 调用，但报告的内容、格式、模板、交付渠道全部未定义。

需要解决的问题：
1. 报告应该包含哪些数据？
2. 报告发给谁？通过什么渠道？
3. 什么时机生成报告？
4. 报告模板长什么样？

---

## 2. 报告类型

### 2.1 报告清单

| 报告类型 | 触发时机 | 内容范围 | 交付渠道 |
|---------|---------|---------|---------|
| **日报** | 每日 22:00（夜间模式结束） | 当日所有 Phase 的执行摘要 | 飞书卡片、文件 |
| **Phase 报告** | 每个 Phase 完成/失败时 | 该 Phase 的详细执行结果 | 文件、飞书（可选） |
| **场景报告** | 整个场景执行完成时 | 场景级汇总 | 文件 |
| **安全报告** | 每周一次 / 有安全事件时 | 安全审计摘要 | 飞书告警、文件 |
| **费用报告** | 每日 / 预算超支时 | Token 消耗和费用明细 | 飞书、文件 |
| **异常报告** | 工作流异常时 | 错误摘要和恢复动作 | 飞书告警 |
| **质量报告** | 代码场景完成后 | 测试覆盖率、代码质量 | 文件、飞书（可选） |

### 2.2 报告优先级

```
P0: 日报、异常报告（必须发送）
P1: Phase 报告、安全报告、费用报告（默认发送，可配置关闭）
P2: 场景报告、质量报告（默认关闭，可配置开启）
```

---

## 3. 报告模板

### 3.1 日报模板

```markdown
# Sloth Agent Daily Report

> 日期: 2026-04-16
> 生成时间: 22:00 CST
> 运行模式: autonomous (day/night cycle)

## 执行摘要

| 指标 | 值 |
|------|-----|
| 场景执行数 | 3 |
| Phase 完成数 | 18 |
| Phase 失败数 | 2 |
| 代码提交数 | 12 |
| 测试通过数 | 45 |
| 测试失败数 | 1 |
| 安全事件数 | 0 |
| 总 Token 消耗 | 125,000 |
| 预估费用 | ¥2.50 |

## 场景执行详情

### Scene: feature-auth (✅ 完成)
- Phase 1 (analysis): ✅ 通过
- Phase 2 (design): ✅ 通过
- Phase 3 (implementation): ✅ 通过 (12 commits)
- Phase 4 (code-review): ✅ 通过
- Phase 5 (testing): ✅ 通过 (45 tests)
- Phase 6 (qa): ⚠️ 1 个非阻塞问题
- Phase 7 (deploy): ⏭️ 跳过（无人值守模式）
- Phase 8 (sre): ✅ 完成

### Scene: fix-login-bug (❌ 失败)
- Phase 1 (analysis): ✅ 通过
- Phase 2 (design): ✅ 通过
- Phase 3 (implementation): ❌ 门控失败 3 次
  - 原因: 测试代码有 bug
  - 处理: 降级执行，跳过测试门控

## 安全摘要

- 被拦截的危险命令: 0
- 路径违规尝试: 0
- 敏感信息访问: 0
- 安全等级: 健康

## 费用明细

| Provider | Input Tokens | Output Tokens | 费用 |
|----------|-------------|--------------|------|
| deepseek-chat | 45,000 | 30,000 | ¥1.20 |
| claude-sonnet | 35,000 | 15,000 | ¥1.30 |
| **合计** | **80,000** | **45,000** | **¥2.50** |

## 建议

1. `fix-login-bug` 场景的测试代码需要手动检查
2. 预算使用率 65%，今日仍有额度

---
*本报告由 Sloth Agent 自动生成*
```

### 3.2 Phase 报告模板

```markdown
# Phase Report: {phase_name}

> 场景: {scenario_id}
> 阶段: {phase_id}
> 执行时间: {start_time} → {end_time} ({duration})
> Agent: {agent_id}
> Trace ID: {trace_id}

## 结果: {PASS/FAIL/SKIPPED}

## 执行详情

- 使用的技能: {skill_1}, {skill_2}, ...
- 工具调用次数: {tool_call_count}
- LLM 调用次数: {llm_call_count}
- Token 消耗: {token_count}
- 文件变更: {+added, -removed, ~modified}

## 门控验证

| 门控 | 结果 | 详情 |
|------|------|------|
| 测试通过 | ✅ | 45 tests passed |
| 代码审查 | ✅ | No blocking issues |
| 安全扫描 | ✅ | No violations |

## 产出物

- 代码变更: {git_diff_summary}
- 测试报告: {test_report_path}
- 审查报告: {review_report_path}

## 备注

{human_readable_summary}
```

---

## 4. 报告生成引擎

```python
class ReportGenerator:
    """报告生成引擎。

    从各数据源收集信息，套用模板，生成报告，
    通过指定渠道发送。
    """

    def __init__(self, config: Config,
                 log_manager: LogManager,
                 notification_manager: NotificationManager,
                 cost_tracker: CostTracker):
        self.config = config
        self.logs = log_manager
        self.notifications = notification_manager
        self.costs = cost_tracker
        self.report_dir = Path("reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily_report(self, date: str) -> Report:
        """生成日报。"""
        # 1. 收集数据
        summary = self._collect_daily_summary(date)
        scenes = self._collect_scene_results(date)
        security = self._collect_security_summary(date)
        costs = self._collect_cost_summary(date)

        # 2. 生成报告
        report = Report(
            type="daily",
            date=date,
            generated_at=datetime.now(),
            summary=summary,
            scenes=scenes,
            security=security,
            costs=costs,
        )

        # 3. 渲染模板
        content = self._render_template("daily.md", report)

        # 4. 保存
        file_path = self.report_dir / f"daily-{date}.md"
        file_path.write_text(content, encoding="utf-8")
        report.file_path = file_path

        # 5. 发送
        self._deliver(report, channels=["feishu_card", "file"])

        return report

    def generate_phase_report(self, phase_result: PhaseResult) -> Report:
        """生成 Phase 报告。"""
        report = Report(
            type="phase",
            scenario_id=phase_result.scenario_id,
            phase_id=phase_result.phase_id,
            result=phase_result.status,
            start_time=phase_result.start_time,
            end_time=phase_result.end_time,
            agent_id=phase_result.agent_id,
            trace_id=phase_result.trace_id,
            skills_used=phase_result.skills_used,
            tool_calls=phase_result.tool_call_count,
            llm_calls=phase_result.llm_call_count,
            tokens=phase_result.token_count,
            file_changes=phase_result.file_changes,
            gate_results=phase_result.gate_results,
            artifacts=phase_result.artifacts,
        )

        content = self._render_template("phase.md", report)
        file_path = self.report_dir / f"phase-{phase_result.scenario_id}-{phase_result.phase_id}.md"
        file_path.write_text(content, encoding="utf-8")
        report.file_path = file_path

        # 根据配置决定是否发送
        if self.config.reports.send_phase_reports:
            self._deliver(report, channels=["file"])

        return report

    def generate_exception_report(self, failure: WorkflowFailure) -> Report:
        """生成异常报告（P0，立即发送）。"""
        report = Report(
            type="exception",
            scenario_id=failure.scenario_id,
            error=failure.summary,
            error_category=failure.category,
            recovery_action=failure.recovery_action,
            timestamp=time.time(),
            trace_id=failure.trace_id,
        )

        content = self._render_template("exception.md", report)
        file_path = self.report_dir / f"exception-{uuid4().hex[:8]}.md"
        file_path.write_text(content, encoding="utf-8")

        # 异常报告必须发送
        self._deliver(report, channels=["feishu_alert", "file"])

        return report
```

---

## 5. 报告交付渠道

```python
class ReportDeliverer:
    """报告交付器。"""

    def deliver(self, report: Report, channels: list[str]) -> list[DeliveryResult]:
        """通过指定渠道发送报告。"""
        results = []

        for channel in channels:
            try:
                if channel == "feishu_card":
                    result = self._send_feishu_card(report)
                elif channel == "feishu_alert":
                    result = self._send_feishu_alert(report)
                elif channel == "file":
                    result = DeliveryResult(
                        channel="file",
                        success=True,
                        note=f"Saved to {report.file_path}",
                    )
                elif channel == "email":
                    result = self._send_email(report)
                elif channel == "webhook":
                    result = self._send_webhook(report)
                else:
                    result = DeliveryResult(
                        channel=channel,
                        success=False,
                        error=f"Unknown channel: {channel}",
                    )
                results.append(result)
            except Exception as e:
                results.append(DeliveryResult(
                    channel=channel,
                    success=False,
                    error=str(e),
                ))

        return results

    def _send_feishu_card(self, report: Report) -> DeliveryResult:
        """发送飞书卡片消息。"""
        if report.type == "daily":
            card = self._build_daily_feishu_card(report)
        elif report.type == "exception":
            card = self._build_exception_feishu_card(report)
        elif report.type == "phase":
            card = self._build_phase_feishu_card(report)
        else:
            card = self._build_generic_feishu_card(report)

        return self.feishu_client.send_card(
            chat_id=self.config.reports.feishu_chat_id,
            card=card,
        )
```

---

## 6. 数据收集器

```python
class DataCollector:
    """从各数据源收集报告数据。"""

    def __init__(self, log_manager: LogManager,
                 metrics_collector: MetricsCollector,
                 cost_tracker: CostTracker):
        self.logs = log_manager
        self.metrics = metrics_collector
        self.costs = cost_tracker

    def collect_daily_summary(self, date: str) -> DailySummary:
        """收集日报所需数据。"""
        # 从日志收集
        entries = self.logs.query(
            since=f"{date}T00:00:00",
            until=f"{date}T23:59:59",
        )

        scenes_completed = len([
            e for e in entries if e.event_type == "scenario.complete"
        ])
        phases_completed = len([
            e for e in entries if e.event_type == "phase.exit"
        ])
        phases_failed = len([
            e for e in entries if e.event_type == "phase.gate.fail"
        ])
        security_events = len([
            e for e in entries if e.layer == "security"
        ])

        return DailySummary(
            date=date,
            scenes_completed=scenes_completed,
            phases_completed=phases_completed,
            phases_failed=phases_failed,
            commits=self._count_commits(date),
            tests_passed=self._count_tests(date, passed=True),
            tests_failed=self._count_tests(date, passed=False),
            security_events=security_events,
            total_tokens=self.costs.get_daily_tokens(date),
            total_cost=self.costs.get_daily_cost(date),
        )
```

---

## 7. 配置

```yaml
# configs/reports.yaml
reports:
  daily:
    enabled: true
    send_time: "22:00"              # 每日发送时间
    channels:
      - "feishu_card"
      - "file"
    feishu_chat_id: ""              # 飞书群聊 ID

  phase:
    enabled: true
    send_on_failure: true            # 失败时必发
    send_on_success: false           # 成功时不发送（减少噪音）
    channels:
      - "file"

  exception:
    enabled: true
    channels:
      - "feishu_alert"
      - "file"
    alert_threshold: "immediate"     # 立即告警

  security:
    enabled: true
    send_schedule: "weekly"          # weekly / on_event
    channels:
      - "feishu_alert"
      - "file"

  cost:
    enabled: true
    send_schedule: "daily"
    budget_warning_threshold: 0.8    # 预算使用率 80% 时警告
    channels:
      - "feishu_card"
      - "file"

  quality:
    enabled: false                   # 默认关闭
    channels:
      - "file"

  templates_dir: "configs/report_templates/"
  output_dir: "reports/"
```

---

## 8. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/reports/__init__.py` | 报告模块入口 |
| `src/sloth_agent/reports/generator.py` | ReportGenerator 报告生成器 |
| `src/sloth_agent/reports/delivery.py` | ReportDeliverer 交付渠道 |
| `src/sloth_agent/reports/collector.py` | DataCollector 数据收集器 |
| `src/sloth_agent/reports/templates/daily.md` | 日报模板 |
| `src/sloth_agent/reports/templates/phase.md` | Phase 报告模板 |
| `src/sloth_agent/reports/templates/exception.md` | 异常报告模板 |
| `src/sloth_agent/reports/models.py` | 报告数据模型 |
| `configs/reports.yaml` | 报告配置 |
| `configs/report_templates/` | 报告模板目录 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
