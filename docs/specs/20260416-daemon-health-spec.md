# 常驻进程与健康检查规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

"黑灯工厂"要求 Agent 能够在无人值守的情况下持续运行。当前架构下：

1. `AgentEvolve.run()` 是一次性执行，完成后退出
2. 没有进程守护，崩溃后无法自动恢复
3. 没有健康检查，无法知道 Agent 是否存活
4. 没有运行时监控，无法检测异常行为

---

## 2. 架构

```
┌─────────────────────────────────────────────────┐
│  systemd / supervisor / 内置 Watchdog            │
│  （进程守护）                                     │
├─────────────────────────────────────────────────┤
│  Health Endpoint (HTTP / 文件)                   │
│  /health → {status, uptime, last_heartbeat}      │
├─────────────────────────────────────────────────┤
│  Agent Daemon                                    │
│  ┌───────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ Day Phase │→ │ Night    │→ │ Report Phase │  │
│  │ 09:00     │  │ 22:00    │  │ 22:00        │  │
│  └───────────┘  └──────────┘  └──────────────┘  │
├─────────────────────────────────────────────────┤
│  Watchdog（心跳监控 + 自动恢复）                   │
│  - 心跳间隔: 180s                                │
│  - 最大丢失: 3 次                                 │
│  - 恢复动作: checkpoint restore                   │
└─────────────────────────────────────────────────┘
```

---

## 3. Agent Daemon

### 3.1 守护进程模式

```python
class AgentDaemon:
    """Sloth Agent 常驻进程管理器。

    支持三种运行模式：
    1. foreground - 前台运行（调试用）
    2. daemon - 后台常驻（生产用）
    3. cron - 定时触发（按需调度）
    """

    def __init__(self, config: Config):
        self.config = config
        self.pid_file = Path("./run/sloth-agent.pid")
        self.log_file = Path("./logs/agent.log")
        self.state_file = Path("./run/state.json")

    def start(self, mode: str = "foreground") -> None:
        """启动 Agent 守护进程。"""
        if mode == "daemon":
            self._daemonize()

        # 写入 PID
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.write_text(str(os.getpid()))

        # 注册信号处理
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # 启动主循环
        self._run_cycle()

    def _daemonize(self) -> None:
        """Fork 到后台。"""
        # 第一次 fork
        pid = os.fork()
        if pid > 0:
            os._exit(0)

        # 脱离终端
        os.setsid()

        # 第二次 fork
        pid = os.fork()
        if pid > 0:
            os._exit(0)

        # 重定向标准输出
        sys.stdout.flush()
        sys.stderr.flush()
        with open(self.log_file, "a") as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())

    def _run_cycle(self) -> None:
        """日夜循环主进程。"""
        while not self._should_stop:
            try:
                now = datetime.now()
                hour = now.hour

                if 9 <= hour < 22:
                    self._run_day_phase()
                else:
                    self._run_night_phase()

                self._run_report_phase()

                # 等待下一个周期
                self._wait_for_next_cycle()

            except Exception as e:
                logger.error(f"Agent cycle error: {e}")
                self._save_checkpoint()  # 出错前保存检查点
                time.sleep(60)  # 等待 1 分钟后重试

    def stop(self) -> None:
        """停止守护进程。"""
        self._should_stop = True
        if self.pid_file.exists():
            self.pid_file.unlink()
```

### 3.2 CLI 命令

```python
# 添加到 src/sloth_agent/cli/app.py

@app.command()
def daemon(
    mode: str = typer.Option("foreground", "--mode", "-m", help="foreground|daemon"),
):
    """Start Sloth Agent as a daemon process."""
    from sloth_agent.daemon import AgentDaemon
    config = load_config()
    daemon = AgentDaemon(config)
    daemon.start(mode=mode)


@app.command()
def stop():
    """Stop the running Sloth Agent daemon."""
    from sloth_agent.daemon import AgentDaemon
    config = load_config()
    daemon = AgentDaemon(config)
    daemon.stop()


@app.command()
def health():
    """Check the health of the running daemon."""
    from sloth_agent.daemon import HealthChecker
    checker = HealthChecker()
    status = checker.check()
    if status.healthy:
        console.print(f"[green]Healthy[/green] - uptime: {status.uptime}")
    else:
        console.print(f"[red]Unhealthy[/red] - {status.reason}")
```

---

## 4. Health Endpoint

### 4.1 文件式健康检查（默认）

```python
class HealthChecker:
    """文件式健康检查。

    Agent 每 180 秒写入一次心跳文件。
    外部监控系统检查文件的时间戳判断存活。
    """

    def __init__(self, heartbeat_interval: int = 180, max_missed: int = 3):
        self.heartbeat_file = Path("./run/heartbeat.json")
        self.interval = heartbeat_interval
        self.max_missed = max_missed

    def beat(self) -> None:
        """写入心跳信号。"""
        state = {
            "timestamp": time.time(),
            "pid": os.getpid(),
            "phase": self._current_phase(),
            "current_task": self._current_task(),
            "uptime": self._uptime(),
            "memory_mb": self._memory_usage(),
        }
        self.heartbeat_file.parent.mkdir(parents=True, exist_ok=True)
        self.heartbeat_file.write_text(json.dumps(state, indent=2))

    def check(self) -> HealthStatus:
        """检查健康状态。"""
        if not self.heartbeat_file.exists():
            return HealthStatus(
                healthy=False,
                reason="No heartbeat file found - daemon not running"
            )

        data = json.loads(self.heartbeat_file.read_text())
        age = time.time() - data["timestamp"]
        max_age = self.interval * self.max_missed

        if age > max_age:
            return HealthStatus(
                healthy=False,
                reason=f"Heartbeat stale: {age:.0f}s ago (max {max_age}s)",
                data=data
            )

        return HealthStatus(healthy=True, data=data)
```

### 4.2 HTTP 健康检查端点（可选）

```python
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    """HTTP 健康检查端点。"""

    def do_GET(self):
        checker = HealthChecker()
        status = checker.check()

        if self.path == "/health":
            if status.healthy:
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "healthy",
                    "uptime": status.data.get("uptime", 0),
                    "phase": status.data.get("phase", "unknown"),
                }).encode())
            else:
                self.send_response(503)
                self.wfile.write(json.dumps({
                    "status": "unhealthy",
                    "reason": status.reason,
                }).encode())
        elif self.path == "/status":
            # 详细状态
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(self._full_status()).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 不输出请求日志


def start_health_server(port: int = 8080) -> HTTPServer:
    """启动健康检查 HTTP 服务器。"""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    return server
```

---

## 5. Watchdog（看门狗）

### 5.1 心跳监控

```python
class Watchdog:
    """看门狗：监控 Agent 心跳，自动恢复。"""

    def __init__(self, config: WatchdogConfig):
        self.interval = config.heartbeat_interval  # 180s
        self.max_missed = config.max_missing_heartbeats  # 3
        self.restart_delay = config.restart_delay  # 60s
        self.missed_count = 0
        self.last_heartbeat = time.time()

    def monitor(self) -> None:
        """监控循环。"""
        while True:
            time.sleep(self.interval)

            checker = HealthChecker()
            status = checker.check()

            if status.healthy:
                self.missed_count = 0  # 重置
                self.last_heartbeat = status.data["timestamp"]
            else:
                self.missed_count += 1
                logger.warning(
                    f"Agent missed heartbeat {self.missed_count}/{self.max_missed}"
                )

                if self.missed_count >= self.max_missed:
                    self._trigger_recovery()

    def _trigger_recovery(self) -> None:
        """触发恢复流程。"""
        logger.info("Triggering agent recovery...")

        # 1. 检查进程是否还存活
        if self._process_alive():
            # 进程在但心跳丢失，可能是死锁
            logger.warning("Process alive but not sending heartbeats")
            self._force_restart()
        else:
            # 进程已崩溃
            self._restart()

    def _force_restart(self) -> None:
        """强制重启。"""
        # 1. 读取 checkpoint
        checkpoint = self._load_latest_checkpoint()

        # 2. 终止旧进程
        self._kill_process()

        # 3. 等待
        time.sleep(self.restart_delay)

        # 4. 从 checkpoint 恢复
        self._start_from_checkpoint(checkpoint)

    def _restart(self) -> None:
        """重启进程。"""
        time.sleep(self.restart_delay)
        self._start_agent()
```

### 5.2 自动恢复策略

```python
class RecoveryStrategy:
    """自动恢复策略选择器。"""

    def decide(self, failure: FailureInfo) -> RecoveryAction:
        """根据失败类型选择恢复动作。"""

        # LLM API 不可用
        if failure.is_api_error():
            return RecoveryAction(
                type="switch_model",
                detail=f"Switch to fallback model (original: {failure.model})"
            )

        # 文件系统错误
        if failure.is_fs_error():
            return RecoveryAction(
                type="restore_checkpoint",
                detail=f"Restore from checkpoint (error: {failure.error})"
            )

        # 内存溢出
        if failure.is_oom():
            return RecoveryAction(
                type="restart_with_cleanup",
                detail="Restart agent and clear temp files"
            )

        # 未知错误
        return RecoveryAction(
            type="full_restart",
            detail=f"Full restart (error: {failure.error})"
        )
```

---

## 6. 系统级守护（systemd / supervisor）

### 6.1 systemd service 文件

```ini
# /etc/systemd/system/sloth-agent.service
[Unit]
Description=Sloth Agent Daemon
After=network.target

[Service]
Type=simple
User=sloth
Group=sloth
WorkingDirectory=/opt/sloth-agent
ExecStart=/opt/sloth-agent/.venv/bin/python -m sloth_agent daemon --mode daemon
ExecStop=/opt/sloth-agent/.venv/bin/python -m sloth_agent stop
Restart=on-failure
RestartSec=60
WatchdogSec=600
StandardOutput=append:/var/log/sloth-agent/agent.log
StandardError=append:/var/log/sloth-agent/error.log

# 资源限制
MemoryMax=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

### 6.2 supervisor 配置

```ini
# /etc/supervisor/conf.d/sloth-agent.conf
[program:sloth-agent]
command=/opt/sloth-agent/.venv/bin/python -m sloth_agent daemon --mode daemon
directory=/opt/sloth-agent
user=sloth
autostart=true
autorestart=unexpected
exitcodes=0
startsecs=10
startretries=3
stopwaitsecs=30
stdout_logfile=/var/log/sloth-agent/stdout.log
stderr_logfile=/var/log/sloth-agent/stderr.log
stdout_logfile_maxbytes=50MB
stderr_logfile_maxbytes=50MB
```

---

## 7. 运行时监控

### 7.1 指标收集

```python
@dataclass
class AgentMetrics:
    uptime_seconds: float
    phases_completed: int
    tasks_completed: int
    tasks_failed: int
    total_tool_calls: int
    total_llm_calls: int
    total_tokens_used: int
    avg_task_duration_seconds: float
    memory_mb: float
    disk_usage_mb: float
    last_error: str | None
    last_error_time: float | None

class MetricsCollector:
    """Agent 运行时指标收集器。"""

    def __init__(self, log_path: str = "logs/metrics.jsonl"):
        self.log_path = Path(log_path)
        self.metrics = AgentMetrics(
            uptime_seconds=0,
            phases_completed=0,
            tasks_completed=0,
            tasks_failed=0,
            total_tool_calls=0,
            total_llm_calls=0,
            total_tokens_used=0,
            avg_task_duration_seconds=0,
            memory_mb=0,
            disk_usage_mb=0,
            last_error=None,
            last_error_time=None,
        )

    def record_task_complete(self, duration: float) -> None:
        self.metrics.tasks_completed += 1
        self._update_avg_duration(duration)

    def record_task_fail(self) -> None:
        self.metrics.tasks_failed += 1

    def record_tool_call(self) -> None:
        self.metrics.total_tool_calls += 1

    def record_llm_call(self, tokens: int) -> None:
        self.metrics.total_llm_calls += 1
        self.metrics.total_tokens_used += tokens

    def snapshot(self) -> None:
        """写入当前指标快照。"""
        self.metrics.uptime_seconds = time.time() - self._start_time
        self.metrics.memory_mb = self._current_memory_mb()
        self.metrics.disk_usage_mb = self._current_disk_mb()

        with open(self.log_path, "a") as f:
            f.write(json.dumps(asdict(self.metrics)) + "\n")
```

---

## 8. 配置文件

```yaml
# configs/daemon.yaml
daemon:
  mode: "foreground"  # foreground | daemon
  pid_file: "./run/sloth-agent.pid"
  log_file: "./logs/agent.log"
  state_file: "./run/state.json"

health:
  heartbeat_interval: 180  # 3 分钟
  max_missed_heartbeats: 3
  http_port: 8080  # 0 表示不启动 HTTP 服务

watchdog:
  restart_delay: 60  # 重启前等待 1 分钟
  max_restart_count: 5  # 24 小时内最多重启 5 次

recovery:
  strategy: "checkpoint_restore"  # checkpoint_restore | full_restart
  checkpoint_dir: "./checkpoints/"
  model_fallback_order: ["deepseek", "qwen", "kimi", "glm"]
```

---

## 9. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/daemon/__init__.py` | AgentDaemon 守护进程 |
| `src/sloth_agent/daemon/health.py` | HealthChecker 健康检查 |
| `src/sloth_agent/daemon/watchdog.py` | Watchdog 看门狗（已有，需增强） |
| `src/sloth_agent/daemon/recovery.py` | RecoveryStrategy 自动恢复 |
| `src/sloth_agent/daemon/metrics.py` | MetricsCollector 指标收集 |
| `src/sloth_agent/daemon/http.py` | HTTP 健康检查端点 |
| `configs/daemon.yaml` | 守护进程配置 |
| `scripts/sloth-agent.service` | systemd service 模板 |
| `logs/metrics.jsonl` | 运行指标（运行时生成） |
| `logs/security.jsonl` | 安全审计（运行时生成） |
| `run/heartbeat.json` | 心跳文件（运行时生成） |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
