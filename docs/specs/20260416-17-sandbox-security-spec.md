# 沙箱与安全规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

---

## 1. 问题

Sloth Agent 在自主模式下会执行代码、运行命令、读写文件。如果没有安全边界，可能出现：

1. 误删项目外文件（`rm -rf /`、`shutil.rmtree("/")`）
2. 敏感信息泄露（读取 `~/.ssh/`、`/etc/passwd`）
3. 资源耗尽（无限循环、内存泄漏、fork bomb）
4. 网络攻击面（向外部发送敏感数据、DDoS）
5. 权限提升（sudo 提权、修改系统配置）

---

## 2. 安全分层

```
┌─────────────────────────────────────────────────┐
│  Layer 5: 审计与监控                              │
│  - 审计日志、异常检测、自动告警                    │
├─────────────────────────────────────────────────┤
│  Layer 4: 权限控制                                │
│  - 文件权限、网络权限、工具权限                     │
├─────────────────────────────────────────────────┤
│  Layer 3: 资源限制                                │
│  - CPU、内存、磁盘、网络带宽                       │
├─────────────────────────────────────────────────┤
│  Layer 2: 沙箱隔离                                │
│  - 目录隔离、进程隔离、网络隔离                    │
├─────────────────────────────────────────────────┤
│  Layer 1: 危险操作拦截                            │
│  - 黑名单、正则拦截、路径校验                      │
└─────────────────────────────────────────────────┘
```

---

## 3. Layer 1：危险操作拦截（黑名单）

### 3.1 Bash 命令黑名单

```python
DANGEROUS_COMMANDS = [
    # 文件系统破坏
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+~",
    r"rm\s+-rf\s+\.\.",
    r"shutil\.rmtree\s*\(\s*['\"]/",
    r"os\.remove\s*\(\s*['\"]/",

    # 权限提升
    r"sudo\s+",
    r"su\s+-",
    r"chmod\s+[0-7]*777",
    r"chown\s+root",

    # 网络攻击
    r"curl.*\|.*sh",
    r"wget.*\|.*bash",
    r"nc\s+-[elp]",
    r"nmap\s+",
    r"fork.*:",  # fork bomb 模式

    # 系统破坏
    r"dd\s+if=/dev/zero",
    r"mkfs",
    r"fdisk",
    r"mount\s+",
    r"umount\s+",
]
```

### 3.2 路径白名单

```python
ALLOWED_PATHS = [
    "./",              # 项目根目录
    "../",             # 项目上级（限制访问）
    "/tmp/",           # 临时目录
]

DENIED_PATHS = [
    "/etc/",           # 系统配置
    "/root/",          # root 家目录
    "/home/",          # 其他用户家目录
    "/proc/",          # 进程信息
    "/sys/",           # 系统信息
    "~/.ssh/",         # SSH 密钥
    "~/.aws/",         # AWS 凭证
    "~/.config/",      # 用户配置
    "~/.bash_history", # 命令历史
]
```

### 3.3 路径校验器

```python
class PathValidator:
    """校验文件路径是否在允许范围内。"""

    def __init__(self, workspace: str, allowed_paths: list[str], denied_paths: list[str]):
        self.workspace = Path(workspace).resolve()
        self.allowed = [self.workspace / p for p in allowed_paths if p != "./"]
        self.denied = [Path(p).expanduser().resolve() for p in denied_paths]

    def validate(self, path: str) -> ValidationResult:
        """校验路径。返回 (allowed: bool, reason: str)。"""
        target = Path(path).resolve()

        # 检查是否在黑名单
        for denied in self.denied:
            if self._is_subpath(target, denied):
                return ValidationResult(
                    ok=False,
                    reason=f"Path '{path}' is in denied path '{denied}'"
                )

        # 检查是否在 workspace 范围内
        if self._is_subpath(target, self.workspace):
            return ValidationResult(ok=True)

        # 检查是否在额外允许路径范围内
        for allowed in self.allowed:
            if self._is_subpath(target, allowed):
                return ValidationResult(ok=True)

        return ValidationResult(
            ok=False,
            reason=f"Path '{path}' is outside allowed directories"
        )

    def _is_subpath(self, path: Path, base: Path) -> bool:
        """检查 path 是否是 base 的子路径。"""
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False
```

---

## 4. Layer 2：沙箱隔离

### 4.1 目录隔离

```yaml
# 每个 Agent 实例有自己的工作空间
sandbox:
  workspace: "./workspace/{session_id}/"
  allowed_dirs:
    - "src/"         # 源代码
    - "tests/"       # 测试代码
    - "docs/"        # 文档
    - "tmp/"         # 临时文件
  readonly_dirs:
    - "configs/"     # 配置只读
    - ".claude/"     # Claude 配置只读
```

### 4.2 进程隔离

```python
class ProcessSandbox:
    """进程级沙箱隔离。"""

    def __init__(self, resource_limits: ResourceLimits):
        self.limits = resource_limits

    def execute(self, command: str) -> ProcessResult:
        """在受限进程中执行命令。"""
        import subprocess
        import resource

        def limit_resources():
            # CPU 时间限制（秒）
            resource.setrlimit(resource.RLIMIT_CPU, (self.limits.cpu_seconds, self.limits.cpu_seconds))
            # 内存限制（字节）
            resource.setrlimit(resource.RLIMIT_AS, (self.limits.max_memory, self.limits.max_memory))
            # 进程数限制
            resource.setrlimit(resource.RLIMIT_NPROC, (self.limits.max_processes, self.limits.max_processes))
            # 文件大小限制（字节）
            resource.setrlimit(resource.RLIMIT_FSIZE, (self.limits.max_file_size, self.limits.max_file_size))

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=self.limits.timeout_seconds,
            preexec_fn=limit_resources if self.limits.enabled else None,
            cwd=self.limits.workspace,
        )
        return ProcessResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
```

### 4.3 资源限制默认值

```python
@dataclass
class ResourceLimits:
    enabled: bool = True
    cpu_seconds: int = 300          # 5 分钟 CPU
    max_memory: int = 1024 * 1024 * 1024  # 1GB
    max_processes: int = 10         # 最多 10 个子进程
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    timeout_seconds: int = 600      # 10 分钟超时
    workspace: str = "./workspace/"
    network_enabled: bool = False   # 默认禁止网络
```

---

## 5. Layer 3：工具权限控制

### 5.1 权限矩阵

| 工具 | 自主模式 | 交互模式 | 说明 |
|------|---------|---------|------|
| `read_file` | ✅ | ✅ | 限制在 workspace 内 |
| `search` | ✅ | ✅ | 限制在 workspace 内 |
| `write_file` | ✅ | ✅ | 限制在 workspace 内 |
| `bash` | ⚠️ | ❌ 需确认 | 黑名单拦截 + 资源限制 |
| `git` | ✅ | ⚠️ 需确认 | 仅允许非破坏性操作 |
| `http_request` | ⚠️ | ⚠️ 需确认 | 限制目标域名 |

### 5.2 Git 操作限制

```python
SAFE_GIT_COMMANDS = [
    "status", "log", "diff", "show", "branch", "tag",
    "stash", "checkout", "add", "commit",
    "push", "pull", "fetch",
    "worktree", "rev-parse", "ls-files",
]

DANGEROUS_GIT_COMMANDS = [
    "push --force", "reset --hard", "clean -f",
    "filter-branch", "rebase --interactive",
]

class GitSandbox:
    def validate(self, command: str) -> ValidationResult:
        if any(dangerous in command for dangerous in DANGEROUS_GIT_COMMANDS):
            return ValidationResult(
                ok=False,
                reason=f"Git command '{command}' is dangerous"
            )
        return ValidationResult(ok=True)
```

---

## 6. Layer 4：敏感信息保护

### 6.1 环境变量保护

```python
SENSITIVE_ENV_VARS = [
    "AWS_SECRET_ACCESS_KEY",
    "AWS_ACCESS_KEY_ID",
    "OPENAI_API_KEY",
    "GITHUB_TOKEN",
    "FEISHU_APP_SECRET",
    "SMTP_PASSWORD",
    "DATABASE_URL",
]

class EnvSanitizer:
    """环境变量脱敏。"""

    def expose(self) -> dict[str, str]:
        """返回安全暴露给 Agent 的环境变量。"""
        safe_vars = {}
        for key, value in os.environ.items():
            if key in SENSITIVE_ENV_VARS:
                safe_vars[key] = "***REDACTED***"
            else:
                safe_vars[key] = value
        return safe_vars

    def validate_access(self, tool_name: str) -> bool:
        """校验工具是否有权访问敏感环境变量。"""
        # 只有 LLM Provider 可以访问 API Key
        if tool_name == "llm_chat":
            return True
        # 其他工具不能访问
        return False
```

### 6.2 输出脱敏

```python
class OutputSanitizer:
    """工具输出脱敏。"""

    PATTERNS = [
        (r"['\"](sk-[a-zA-Z0-9]{20,})['\"]", "***API_KEY_REDACTED***"),
        (r"['\"](ghp_[a-zA-Z0-9]{36})['\"]", "***GITHUB_TOKEN_REDACTED***"),
        (r"\b\d{4}[-]?\d{4}[-]?\d{4}[-]?\d{4}\b", "***CREDIT_CARD_REDACTED***"),
    ]

    def sanitize(self, output: str) -> str:
        """脱敏输出中的敏感信息。"""
        for pattern, replacement in self.PATTERNS:
            output = re.sub(pattern, replacement, output)
        return output
```

---

## 7. Layer 5：审计与监控

### 7.1 安全审计日志

```python
@dataclass
class SecurityLog:
    timestamp: float
    event_type: str  # "blocked_command" | "path_violation" | "resource_exhausted" | "sensitive_access"
    severity: str    # "warning" | "error" | "critical"
    tool_name: str
    detail: str
    action_taken: str  # "blocked" | "allowed_with_warning" | "logged"

class SecurityAuditor:
    """安全审计日志管理器。"""

    def __init__(self, log_path: str = "logs/security.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: SecurityLog) -> None:
        """写入安全事件。"""
        with open(self.log_path, "a") as f:
            f.write(json.dumps(asdict(event)) + "\n")

        # 严重事件立即告警
        if event.severity == "critical":
            self._alert(event)

    def _alert(self, event: SecurityLog) -> None:
        """发送安全告警。"""
        # TODO: 飞书通知、邮件通知
        pass
```

### 7.2 异常行为检测

```python
class AnomalyDetector:
    """检测异常工具调用模式。"""

    def __init__(self, window_seconds: int = 60, threshold: int = 10):
        self.window = window_seconds
        self.threshold = threshold
        self.history: list[float] = []  # 时间戳列表

    def check(self, tool_name: str) -> bool:
        """检查是否触发异常模式。返回 True 表示异常。"""
        now = time.time()
        self.history.append(now)

        # 窗口期内调用次数超过阈值
        window_start = now - self.window
        recent = [t for t in self.history if t > window_start]
        if len(recent) > self.threshold:
            return True

        return False
```

---

## 8. Python 代码执行沙箱

当 Agent 需要执行 Python 代码时（如 `code_execution` 工具）：

```python
class PythonSandbox:
    """Python 代码执行沙箱。"""

    ALLOWED_MODULES = {
        "os", "sys", "json", "re", "math", "datetime",
        "pathlib", "collections", "itertools", "functools",
        "typing", "dataclasses", "enum", "hashlib",
    }

    BLOCKED_FUNCTIONS = {
        "eval", "exec", "compile", "__import__",
        "getattr", "setattr", "delattr",
        "open",  # 使用沙箱提供的安全文件读写
    }

    def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        """在受限环境中执行 Python 代码。"""
        import ast

        # 1. AST 安全检查
        self._check_ast(code)

        # 2. 在子进程中执行
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=self.workspace,
            env=self._safe_env(),
        )
        return ExecutionResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )

    def _check_ast(self, code: str) -> None:
        """AST 级别安全检查。"""
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name not in self.ALLOWED_MODULES:
                        raise SecurityError(f"Module '{alias.name}' not allowed")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.BLOCKED_FUNCTIONS:
                    raise SecurityError(f"Function '{node.func.id}' blocked")
```

---

## 9. 配置文件

```yaml
# configs/security.yaml
security:
  sandbox:
    enabled: true
    workspace: "./workspace/"
    resource_limits:
      cpu_seconds: 300
      max_memory_mb: 1024
      max_processes: 10
      max_file_size_mb: 100
      timeout_seconds: 600

  path:
    allowed:
      - "./src/"
      - "./tests/"
      - "./docs/"
      - "./tmp/"
    denied:
      - "/etc/"
      - "/root/"
      - "~/.ssh/"
      - "~/.aws/"

  network:
    enabled: false  # 默认禁止沙箱内网络
    allowed_domains:
      - "api.openai.com"
      - "api.deepseek.com"
      - "pypi.org"

  audit:
    log_path: "logs/security.jsonl"
    alert_on_critical: true
    alert_channels:
      - type: "feishu"
        webhook: "${FEISHU_SECURITY_WEBHOOK}"
```

---

## 10. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/security/path_validator.py` | 路径白名单校验 |
| `src/sloth_agent/security/process_sandbox.py` | 进程沙箱 |
| `src/sloth_agent/security/git_sandbox.py` | Git 操作限制 |
| `src/sloth_agent/security/env_sanitizer.py` | 环境变量脱敏 |
| `src/sloth_agent/security/output_sanitizer.py` | 输出脱敏 |
| `src/sloth_agent/security/auditor.py` | 安全审计日志 |
| `src/sloth_agent/security/anomaly_detector.py` | 异常行为检测 |
| `src/sloth_agent/security/python_sandbox.py` | Python 代码沙箱 |
| `src/sloth_agent/security/models.py` | 安全数据模型 |
| `configs/security.yaml` | 安全配置 |
| `logs/security.jsonl` | 安全审计日志（运行时生成） |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
