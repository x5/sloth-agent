# 安装与引导规范

> 版本: v1.1.0
> 日期: 2026-04-16
> 状态: 部分实现
> v0.1 更新: 全局安装脚本 (install.sh / install.ps1) 已实现，采用 Claude Code 安装模型

---

## 1. 问题

新用户首次使用 Sloth Agent 时面临的问题：

1. 不知道需要安装哪些依赖（Python、uv、API Key）
2. 配置文件不知道怎么填
3. 飞书/webhook 等外部集成不知道怎么配置
4. 没有一个"快速开始"的体验
5. 环境检查不透明，出了问题不知道哪里不对

---

## 2. 安装流程

```
sloth install
    │
    ├── ① 环境检查（Python、uv、Git）
    ├── ② 依赖安装（uv sync）
    ├── ③ 配置引导（交互式问答）
    │   ├── API Key 配置
    │   ├── 飞书集成（可选）
    │   ├── 工作空间设置
    │   └── 安全配置
    ├── ④ 模板初始化
    │   ├── 项目结构
    │   ├── 默认配置文件
    │   └── 示例技能
    ├── ⑤ 环境验证
    └── ⑥ 完成 + 快速开始指南
```

---

## 3. 环境检查器

### 3.1 检查清单

```python
@dataclass
class CheckResult:
    name: str
    passed: bool
    version: str | None = None
    error: str | None = None
    suggestion: str | None = None

class EnvironmentChecker:
    """环境依赖检查器。"""

    CHECKS = [
        ("Python", "python3 --version", r"Python (\d+\.\d+\.\d+)", (3, 10)),
        ("uv", "uv --version", r"uv (\d+\.\d+\.\d+)", (0, 1)),
        ("Git", "git --version", r"git version (\d+\.\d+\.\d+)", (2, 0)),
    ]

    def run_all(self) -> list[CheckResult]:
        """运行所有检查。"""
        results = []
        for name, command, version_pattern, min_version in self.CHECKS:
            result = self._check(name, command, version_pattern, min_version)
            results.append(result)
        return results

    def _check(self, name: str, command: str, version_pattern: str,
               min_version: tuple[int, int]) -> CheckResult:
        """检查单个依赖。"""
        try:
            output = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=10
            )
            if output.returncode != 0:
                return CheckResult(
                    name=name, passed=False,
                    suggestion=f"Install {name}: {self._install_command(name)}"
                )

            version = re.search(version_pattern, output.stdout)
            if not version:
                return CheckResult(name=name, passed=False, error="Version not detected")

            ver_str = version.group(1)
            ver = tuple(int(x) for x in ver_str.split(".")[:2])
            if ver < min_version:
                return CheckResult(
                    name=name, passed=False, version=ver_str,
                    suggestion=f"{name} >= {'.'.join(str(v) for v in min_version)} required"
                )

            return CheckResult(name=name, passed=True, version=ver_str)

        except FileNotFoundError:
            return CheckResult(
                name=name, passed=False,
                suggestion=f"Install {name}: {self._install_command(name)}"
            )

    def _install_command(self, name: str) -> str:
        """返回安装命令建议。"""
        commands = {
            "Python": "https://www.python.org/downloads/",
            "uv": "curl -LsSf https://astral.sh/uv/install.sh | sh",
            "Git": "https://git-scm.com/downloads",
        }
        return commands.get(name, f"Install {name}")

    def check_api_keys(self) -> list[CheckResult]:
        """检查 API Key 是否已配置。"""
        results = []

        # DeepSeek
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
        if deepseek_key:
            results.append(CheckResult(name="DeepSeek API Key", passed=True))
        else:
            results.append(CheckResult(
                name="DeepSeek API Key", passed=False,
                suggestion="Set DEEPSEEK_API_KEY environment variable"
            ))

        return results
```

### 3.2 环境报告

```
Checking environment...
✅ Python 3.13.12
✅ uv 0.6.0
✅ Git 2.45.0
❌ DeepSeek API Key not set

1 of 4 checks failed.

To fix: export DEEPSEEK_API_KEY="your-key-here"
        Or add to .env file
```

---

## 4. 交互式配置引导

### 4.1 CLI 命令

```python
@app.command()
def install():
    """Install and configure Sloth Agent."""
    from sloth_agent.cli.install import Installer

    installer = Installer()
    installer.run()
```

### 4.2 安装流程实现

```python
class Installer:
    """交互式安装向导。"""

    def __init__(self):
        self.console = Console()
        self.config: dict = {}

    def run(self) -> None:
        """运行完整安装流程。"""
        self.console.print("[bold blue]Sloth Agent Installer[/bold blue]")
        self.console.print()

        # 1. 环境检查
        if not self._step_environment():
            return

        # 2. 依赖安装
        self._step_dependencies()

        # 3. 配置引导
        self._step_configuration()

        # 4. 模板初始化
        self._step_templates()

        # 5. 验证
        self._step_verification()

        # 6. 完成
        self._step_completion()

    def _step_environment(self) -> bool:
        """Step 1: 环境检查。"""
        self.console.print("\n[bold step 1/6] Checking environment...[/bold]")

        checker = EnvironmentChecker()
        results = checker.run_all()

        all_passed = True
        for r in results:
            if r.passed:
                self.console.print(f"  [green]✅[/green] {r.name} {r.version or ''}")
            else:
                self.console.print(f"  [red]❌[/red] {r.name}: {r.error or 'not found'}")
                if r.suggestion:
                    self.console.print(f"     [dim]→ {r.suggestion}[/dim]")
                all_passed = False

        if not all_passed:
            self.console.print("\n[yellow]Please fix the above issues and retry.[/yellow]")
            return False

        return True

    def _step_dependencies(self) -> None:
        """Step 2: 安装依赖。"""
        self.console.print("\n[bold step 2/6] Installing dependencies...[/bold]")

        with self.console.status("[dim]uv sync...[/dim]"):
            result = subprocess.run(
                "uv sync", shell=True, capture_output=True, text=True
            )

        if result.returncode == 0:
            self.console.print("  [green]✅[/green] Dependencies installed")
        else:
            self.console.print(f"  [red]❌[/red] Failed: {result.stderr}")

    def _step_configuration(self) -> None:
        """Step 3: 交互式配置引导。"""
        self.console.print("\n[bold step 3/6] Configuration[/bold]")

        # 3a: LLM Provider 选择
        self._configure_llm()

        # 3b: 工作空间
        self._configure_workspace()

        # 3c: 飞书集成（可选）
        self._configure_feishu()

        # 3d: 安全配置
        self._configure_security()

        # 写入配置文件
        self._write_config()

    def _configure_llm(self) -> None:
        """配置 LLM Provider。"""
        self.console.print("\n  [bold]LLM Provider Configuration[/bold]")

        providers = ["deepseek", "qwen", "kimi", "glm", "minimax"]
        selected = self._ask_choice(
            "Select default LLM provider:", providers
        )

        api_key = self._ask_secret(
            f"Enter {selected} API key:",
            env_var=f"{selected.upper()}_API_KEY"
        )

        self.config["llm"] = {
            "default_provider": selected,
            "api_key_env": f"{selected.upper()}_API_KEY",
        }

    def _configure_workspace(self) -> None:
        """配置工作空间。"""
        workspace = self._ask_input(
            "Workspace directory:",
            default="./workspace",
            validator=self._validate_path
        )
        self.config["agent"] = {"workspace": workspace}

    def _configure_feishu(self) -> None:
        """配置飞书集成（可选）。"""
        use_feishu = self._ask_yes_no(
            "Enable Feishu integration? (y/N)", default=False
        )

        if use_feishu:
            app_id = self._ask_input("Feishu App ID:")
            app_secret = self._ask_secret("Feishu App Secret:")
            self.config["feishu"] = {
                "enabled": True,
                "app_id": app_id,
                "app_secret": app_secret,
            }
        else:
            self.config["feishu"] = {"enabled": False}

    def _configure_security(self) -> None:
        """配置安全级别。"""
        self.console.print("\n  [bold]Security Level[/bold]")
        level = self._ask_choice(
            "Select security level:",
            ["strict (recommended) - sandbox enabled",
             "relaxed - sandbox disabled"]
        )

        self.config["security"] = {
            "sandbox_enabled": "strict" in level.lower(),
        }

    def _step_templates(self) -> None:
        """Step 4: 初始化模板。"""
        self.console.print("\n[bold step 4/6] Initializing templates...[/bold]")

        # 创建目录结构
        dirs = ["workspace", "configs", "logs", "checkpoints", "skills/user"]
        for d in dirs:
            Path(d).mkdir(parents=True, exist_ok=True)
            self.console.print(f"  [green]✅[/green] Created {d}/")

        # 复制默认配置
        self._copy_default_configs()

        # 创建示例技能
        self._create_example_skill()

    def _step_verification(self) -> None:
        """Step 5: 最终验证。"""
        self.console.print("\n[bold step 5/6] Verifying installation...[/bold]")

        # 验证配置可加载
        try:
            from sloth_agent.core.config import load_config
            config = load_config()
            self.console.print("  [green]✅[/green] Configuration loads OK")
        except Exception as e:
            self.console.print(f"  [red]❌[/red] Config error: {e}")

        # 验证工具可注册
        try:
            from sloth_agent.core.tools.tool_registry import ToolRegistry
            registry = ToolRegistry(config)
            self.console.print(f"  [green]✅[/green] {len(registry.list_tools())} tools registered")
        except Exception as e:
            self.console.print(f"  [red]❌[/red] Tool error: {e}")

    def _step_completion(self) -> None:
        """Step 6: 完成。"""
        self.console.print("\n[bold green]🎉 Installation complete![/bold green]")
        self.console.print()
        self.console.print("[bold]Quick Start:[/bold]")
        self.console.print("  sloth chat          # Enter interactive chat")
        self.console.print("  sloth run           # Run autonomous mode")
        self.console.print("  sloth status        # Check agent status")
        self.console.print("  sloth skills        # List available skills")
        self.console.print()
        self.console.print("[dim]Config saved to: configs/agent.yaml[/dim]")
        self.console.print("[dim]Logs will be in: logs/[/dim]")
```

---

## 5. 辅助工具函数

```python
def _ask_input(self, prompt: str, default: str | None = None,
               validator=None) -> str:
    """带默认值和校验的输入。"""
    if default:
        prompt = f"{prompt} [{default}]"

    while True:
        value = input(f"  {prompt} ").strip()
        if not value and default:
            return default
        if not value:
            continue
        if validator and not validator(value):
            self.console.print("  [red]Invalid value, please retry[/red]")
            continue
        return value


def _ask_choice(self, prompt: str, choices: list[str]) -> str:
    """选择菜单。"""
    self.console.print(f"  {prompt}")
    for i, choice in enumerate(choices, 1):
        self.console.print(f"    {i}. {choice}")

    while True:
        value = input("  Select (number): ").strip()
        try:
            idx = int(value) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except ValueError:
            pass


def _ask_yes_no(self, prompt: str, default: bool = False) -> bool:
    """Yes/No 选择。"""
    suffix = " [Y/n]" if default else " [y/N]"
    value = input(f"  {prompt}{suffix} ").strip().lower()
    if not value:
        return default
    return value in ("y", "yes")


def _ask_secret(self, prompt: str, env_var: str | None = None) -> str:
    """安全输入（不回显）。"""
    import getpass
    value = getpass.getpass(f"  {prompt} ")

    # 同时写入 .env 文件
    if env_var:
        env_path = Path(".env")
        lines = {}
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    lines[k.strip()] = v.strip()
        lines[env_var] = value
        env_path.write_text("\n".join(f"{k}={v}" for k, v in lines.items()))

    return value


def _validate_path(self, path: str) -> bool:
    """校验路径合法。"""
    try:
        p = Path(path)
        return len(str(p)) < 255
    except Exception:
        return False
```

---

## 6. 配置文件模板

### 6.1 .env.example

```bash
# Global API Keys — copy to .env and fill in your keys
# These are used by all projects unless overridden by project .env
DEEPSEEK_API_KEY=
QWEN_API_KEY=

# Optional additional providers
# KIMI_API_KEY=
# GLM_API_KEY=
# MINIMAX_API_KEY=
# XIAOMI_API_KEY=

# Feishu (optional)
FEISHU_APP_ID=
FEISHU_APP_SECRET=
FEISHU_WEBHOOK_URL=

# SMTP (optional, for email notifications)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
```

> **注意**：API Key 解析顺序为 `项目 .env > 全局 .env > 系统环境变量`。详见 §10.2.1。

### 6.2 agent.yaml（生成后）

```yaml
# Generated by sloth install on 2026-04-16
agent:
  name: "sloth-agent"
  workspace: "./workspace"
  timezone: "Asia/Shanghai"

execution:
  auto_execute_hours: "09:00-18:00"
  require_approval_hours: "18:00-09:00"

chat:
  max_context_turns: 20
  auto_approve_risk_level: 2
  stream_responses: true
  prompt_prefix: "sloth> "

security:
  sandbox_enabled: true
```

---

## 6.5 统一配置文件 config.json（v0.2 新增）

### 6.5.1 文件位置与作用

Sloth Agent 使用 JSON 格式的 `config.json` 作为统一配置文件，替代原有的 `agent.yaml` + `.env` 双文件模式。`config.json` 只管理结构和行为配置，API Key 仍通过环境变量或 `.env` 文件读取（配置文件中用 `"env:VAR_NAME"` 引用）。

### 6.5.2 配置层级与优先级

```
项目 local > 项目 project > 全局 user
```

| 层级 | 路径 | 说明 | Git |
|------|------|------|-----|
| local | `[项目]/.sloth/config.local.json` | 个人覆盖 | gitignore |
| project | `[项目]/.sloth/config.json` | 团队共享 | git commit |
| user | `~/.sloth-agent/config.json` | 全局默认 | 不纳入 git |

加载时按 local → project → user 深度合并，local 优先级最高。

### 6.5.3 config.json 格式

```json
{
  "llm": {
    "providers": {
      "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "models": {
          "coding": "deepseek-v3.2",
          "reasoning": "deepseek-r1-0528"
        }
      },
      "qwen": {
        "api_key_env": "QWEN_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": {
          "review": "qwen3.6-plus"
        }
      },
      "kimi": {
        "api_key_env": "KIMI_API_KEY",
        "base_url": "https://api.moonshot.cn/v1",
        "models": {
          "vision": "kimi-k2.5"
        }
      },
      "glm": {
        "api_key_env": "GLM_API_KEY",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": {
          "coding": "glm-5.1"
        }
      }
    },
    "default_provider": "deepseek"
  },
  "agent": {
    "name": "sloth-agent",
    "workspace": "./workspace",
    "timezone": "Asia/Shanghai"
  },
  "execution": {
    "auto_execute_hours": "09:00-18:00",
    "require_approval_hours": "18:00-09:00"
  },
  "chat": {
    "max_context_turns": 20,
    "auto_approve_risk_level": 2,
    "stream_responses": true,
    "prompt_prefix": "sloth> "
  },
  "security": {
    "sandbox_enabled": true,
    "path_whitelist": ["./workspace/**", "./src/**", "./tests/**"],
    "command_denylist": ["rm -rf /", "dd", "mkfs"]
  },
  "skills": {
    "global_dir": "~/.sloth-agent/skills",
    "local_dir": ".sloth/local_skills"
  },
  "observability": {
    "log_level": "INFO",
    "log_file": "~/.sloth-agent/logs/sloth.log"
  }
}
```

### 6.5.4 ConfigManager 实现

```python
from dataclasses import dataclass, field
from pathlib import Path
import json
import os

@dataclass
class ProviderConfig:
    api_key_env: str
    base_url: str
    models: dict[str, str] = field(default_factory=dict)

@dataclass
class LLMConfig:
    providers: dict[str, ProviderConfig]
    default_provider: str = "deepseek"

@dataclass
class AgentConfig:
    name: str = "sloth-agent"
    workspace: str = "./workspace"
    timezone: str = "Asia/Shanghai"

@dataclass
class SecurityConfig:
    sandbox_enabled: bool = True
    path_whitelist: list[str] = field(default_factory=lambda: ["./workspace/**", "./src/**"])
    command_denylist: list[str] = field(default_factory=lambda: ["rm -rf /", "dd", "mkfs"])

@dataclass
class SlothConfig:
    llm: LLMConfig
    agent: AgentConfig = field(default_factory=AgentConfig)
    execution: dict = field(default_factory=dict)
    chat: dict = field(default_factory=dict)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    skills: dict = field(default_factory=dict)
    observability: dict = field(default_factory=dict)


class ConfigManager:
    """
    加载和合并多层级 config.json。
    支持 user/project/local 三级配置，深度合并，local 优先。
    """

    def __init__(self, project_dir: str | None = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()

    @property
    def _user_config(self) -> Path:
        return Path.home() / ".sloth-agent" / "config.json"

    @property
    def _project_config(self) -> Path:
        return self.project_dir / ".sloth" / "config.json"

    @property
    def _local_config(self) -> Path:
        return self.project_dir / ".sloth" / "config.local.json"

    def load(self) -> SlothConfig:
        merged: dict = {}
        for cfg_path in [self._user_config, self._project_config, self._local_config]:
            if cfg_path.exists():
                data = json.loads(cfg_path.read_text())
                merged = self._deep_merge(merged, data)
        return self._from_dict(merged)

    def _deep_merge(self, base: dict, override: dict) -> dict:
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _from_dict(self, data: dict) -> SlothConfig:
        llm_data = data.get("llm", {})
        providers = {}
        for name, prov in llm_data.get("providers", {}).items():
            providers[name] = ProviderConfig(**prov)
        llm = LLMConfig(
            providers=providers,
            default_provider=llm_data.get("default_provider", "deepseek")
        )
        agent = AgentConfig(**data.get("agent", {}))
        security = SecurityConfig(**data.get("security", {}))
        return SlothConfig(
            llm=llm,
            agent=agent,
            execution=data.get("execution", {}),
            chat=data.get("chat", {}),
            security=security,
            skills=data.get("skills", {}),
            observability=data.get("observability", {})
        )

    def get_api_key(self, provider: str) -> str | None:
        """
        从配置中解析 api_key_env，返回实际 API Key 值。
        支持 "env:VAR_NAME" 和 "$VAR_NAME" 两种引用格式。
        """
        config = self.load()
        prov = config.llm.providers.get(provider)
        if not prov:
            return None
        env_var = prov.api_key_env
        return os.environ.get(env_var)
```

### 6.5.5 CLI 命令

```bash
sloth config                          # 查看当前生效的合并配置
sloth config --scope user             # 查看全局配置
sloth config --scope project          # 查看项目配置
sloth config --scope local            # 查看个人覆盖配置
sloth config set llm.default_provider qwen   # 修改当前层级配置
sloth config validate                 # 验证配置文件合法性
sloth config env                      # 列出所有需要设置的 API Key 环境变量
```

### 6.5.6 与 .env 的关系

| 配置类型 | 存储位置 | 格式 | 说明 |
|---------|---------|------|------|
| API Key | `.env` 或系统环境变量 | `KEY=VALUE` | 敏感信息，不进 config.json |
| 模型路由 | `config.json` | JSON | provider、模型名、base_url |
| 行为参数 | `config.json` | JSON | workspace、chat、security、skills |

config.json 中用 `api_key_env` 字段指向环境变量名，运行时通过 `ConfigManager.get_api_key()` 解析。

### 6.5.7 交互式初始化向导（v0.2 新增）

```bash
sloth config init --interactive    # 交互式引导（推荐）
sloth config init -i               # 同上，简写
sloth config init                  # 非交互，创建模板文件
```

**交互式流程：**

```
sloth config init --interactive
    │
    ├── ① 选择作用域：user（全局）/ project（当前目录）
    ├── ② 选择默认 LLM Provider
    │       deepseek（推荐）/ qwen / kimi / glm / minimax / xiaomi
    ├── ③ 输入 API Key
    │       隐藏输入，支持粘贴
    │       可选：跳过（后续手动编辑 .env）
    ├── ④ 设置工作空间路径（默认 ./workspace）
    ├── ⑤ 确认配置摘要
    │       显示即将创建/修改的文件和内容摘要
    ├── ⑥ 写入配置
    │       user 模式 → ~/.sloth-agent/config.json + ~/.sloth-agent/.env
    │       project 模式 → .sloth/config.json + .env
    └── ⑦ 验证
            自动加载配置并测试 API Key 可用性（可选的 ping 测试）
```

**实现要求：**
- 使用 `prompt_toolkit` 实现跨平台兼容的交互式输入
- API Key 输入使用隐藏模式（类似密码输入）
- 每个步骤支持 Tab 补全和默认值
- 支持 `Ctrl+C` 随时退出，已写入的部分配置保留
- 输出摘要使用 Rich 表格，清晰展示配置结果

**配置写入规则：**
- user 模式：写入 `~/.sloth-agent/config.json`（含 provider 和 `api_key_env` 定义）+ `~/.sloth-agent/.env`（含实际 Key）
- project 模式：写入 `[cwd]/.sloth/config.json` + `[cwd]/.env`
- 如果文件已存在，合并已有配置，不覆盖无关字段

---

## 7. 首次运行引导

安装完成后，显示快速开始指南：

```
🎉 Installation complete!

Your first steps:

1. Run 'sloth chat' to try interactive mode
   Type /help to see available commands

2. Place your project files in ./workspace/

3. Run 'sloth run' for autonomous mode
   Agent will: analyze → plan → code → review → deploy

4. Check 'sloth status' anytime to see agent state

Docs: https://...
Support: ...
```

---

## 9. CLI 入口与 `sloth run` 命令（v1.0）

### 9.1 命令定义

v1.0 CLI 提供 `run` 子命令，用于启动自主流水线：

```bash
sloth run <plan>              # 输入 Plan 文件，跑完整 Builder → Gate1 → Reviewer → Gate2 → Deployer → Gate3 流水线
sloth run <plan> --agent      # 指定从哪个 Agent 开始（默认 builder）
sloth run <plan> --dry-run    # 预演模式，不执行实际工具调用
```

### 9.2 执行流程

```
sloth run path/to/plan.md
    │
    ├── ① 加载配置文件（configs/agent.yaml）
    ├── ② 初始化 LLM Router（按 agent + stage 路由）
    ├── ③ 创建 ProductOrchestrator
    ├── ④ 创建 Runner + ToolRegistry
    ├── ⑤ 加载 Plan 文件
    ├── ⑥ 创建 RunState（run_id=uuid）
    ├── ⑦ 设置 Builder phase
    ├── ⑧ runner.run(state) → 完整流水线执行
    ├── ⑨ 阶段产物写入 memory/scenarios/
    ├── ⑩ 输出最终结果
```

### 9.3 CLI 入口代码

```python
# src/sloth_agent/cli/app.py

import typer
from pathlib import Path
from rich.console import Console

app = typer.Typer()

@app.command()
def run(plan: str = typer.Argument(..., help="Plan 文件路径")):
    """执行自主流水线: Builder → Reviewer → Deployer"""
    from sloth_agent.core.config import load_config
    from sloth_agent.core.orchestrator import ProductOrchestrator
    from sloth_agent.core.runner import Runner

    config = load_config()
    orchestrator = ProductOrchestrator(config)
    runner = Runner(config, orchestrator.tool_registry)

    plan_text = Path(plan).read_text()
    state = orchestrator.create_run_state()
    state.current_agent = "builder"
    state.current_phase = "plan_parsing"

    final_state = runner.run(state)

    if final_state.phase == "completed":
        console.print("[green]流水线执行成功![/green]")
    else:
        console.print(f"[red]流水线失败: {final_state.errors}[/red]")
```

### 9.4 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/cli/app.py` | CLI 入口（typer app，sloth run/status/eval） |
| `src/sloth_agent/cli/install.py` | 交互式安装向导 |
| `src/sloth_agent/cli/env_check.py` | 环境检查器 |

---

## 8. 文件清单

| 文件 | 说明 |
|------|------|
| `src/sloth_agent/cli/install.py` | 交互式安装向导 |
| `src/sloth_agent/cli/env_check.py` | 环境检查器 |
| `src/sloth_agent/core/config.py` | ConfigManager + 配置数据类 |
| `configs/config.json.example` | 配置模板（JSON） |
| `configs/agent.yaml.example` | 配置模板（YAML，v0.1 兼容） |
| `.env.example` | 环境变量模板 |
| `skills/user/example_skill/SKILL.md` | 示例技能 |

---

---

## 10. 全局安装脚本（v0.1 已实现）

### 10.1 设计理念

采用 Claude Code 安装模型：**一键脚本 → 自检 → 安装 → CLI shim → 用户在任何项目目录运行 `sloth`**。

### 10.2 安装流程

```
curl ... | bash  (macOS/Linux)  或  iwr ... | iex  (Windows)
    │
    ├── ① 自检：检查 git、uv、python3
    │       └── uv 缺失则自动下载安装
    ├── ② 克隆/更新到 ~/.sloth-agent（固定位置）
    ├── ③ 创建 .venv，uv pip install -e .
    │       └── 自动安装 pyproject.toml 中全部依赖
    ├── ④ 创建 CLI shim
    │       ├── macOS/Linux: ~/.local/bin/sloth → ~/.sloth-agent/.venv/bin/sloth
    │       └── Windows:     %USERPROFILE%\.local\bin\sloth.ps1 + .bat
    ├── ⑤ 将 ~/.local/bin 写入 shell profile（~/.zshrc / ~/.bashrc / $PROFILE）
    ├── ⑥ 验证：sloth --help 可执行
    ├── ⑦ Smoke test：evals.smoke_test 验证流水线完整性
    ├── ⑧ 创建 .env.example，若环境变量有 Key 则自动填充 .env
    └── ⑨ 输出下一步指南
```

### 10.2.1 API Key 解析顺序

```
项目 .env > 全局 .env > 系统环境变量
```

| 优先级 | 来源 | 路径 | 说明 |
|--------|------|------|------|
| 1（最高） | 项目 .env | `[项目目录]/.env` | 仅当前项目生效 |
| 2 | 全局 .env | `~/.sloth-agent/.env` | 所有项目共用，项目 .env 可覆盖 |
| 3 | 系统环境变量 | 当前 shell 的 `env` | 仅当前 shell session 生效 |

**示例场景：**
- 个人项目 → 配全局 `~/.sloth-agent/.env` 即可
- 客户项目需独立 Key → 客户项目创建 `.env`，覆盖全局
- 临时测试 → `export DEEPSEEK_API_KEY=test-key`，session 结束自动失效

### 10.3 安装脚本产物

| 产物 | 平台 | 路径 |
|------|------|------|
| install.sh | macOS / Linux / WSL2 | `scripts/install.sh` |
| install.ps1 | Windows PowerShell | `scripts/install.ps1` |
| CLI shim | macOS/Linux | `~/.local/bin/sloth` |
| CLI shim + .bat | Windows | `%USERPROFILE%\.local\bin\sloth.ps1` + `.bat` |
| .env.example | 所有平台 | `~/.sloth-agent/.env.example` |
| .env（自动填充） | 所有平台 | `~/.sloth-agent/.env`（仅当环境变量有 Key 时） |

### 10.4 自检清单

| 检查项 | 缺失行为 |
|--------|---------|
| git | 失败，提示安装地址 |
| uv | 自动从 astral.sh 下载安装脚本 |
| python3 | 警告，uv 会自动管理 Python 版本 |

### 10.5 CLI Shim 设计

Shim 是一个极简脚本，仅将调用委托给隐藏 venv 中的 sloth：

```bash
# macOS/Linux: ~/.local/bin/sloth
#!/bin/bash
exec "${HOME}/.sloth-agent/.venv/bin/sloth" "$@"
```

```powershell
# Windows: %USERPROFILE%\.local\bin\sloth.ps1
& "$HOME\.sloth-agent\.venv\Scripts\sloth.exe" $args
```

优势：
- 项目依赖升级时，用户无需重新安装 shim
- venv 位置固定，shim 无需修改
- 卸载时只需删除 `~/.sloth-agent` 和 shim

### 10.6 用户安装后使用方式

```bash
# 在任何项目目录下直接运行
sloth --help
sloth init
sloth run --plan plan.md
sloth status
```

### 10.7 与交互式配置向导的关系

Spec 第 2-6 节描述的 `sloth install` 交互式向导（环境检查 → 依赖安装 → 配置引导 → 模板初始化 → 验证 → 完成）是 **v0.2+ 的目标**，当前 v0.1 通过安装脚本实现最小可用安装流程。

v0.2 起，通过 `sloth config init --interactive` 提供交互式配置引导（spec §6.5.7），专注于配置环节。完整的环境检查 + 依赖安装由安装脚本处理。

---

## 11. 全局安装与多项目架构（从跨模块规范迁入）

### 11.1 设计理念

Sloth Agent 作为**全局工具**安装，一次安装，所有项目通用（类似 OpenClaw/Hermes Agent）。

### 11.2 目录结构

```
~/.sloth-agent/                  # 全局安装目录（~/.sloth-agent/）
├── src/                        # 框架源码（全局一份）
├── .env.example                # API Key 模板
├── .env                        # 全局 API Key（可选）
├── config.json                 # 全局统一配置
├── configs/                    # 全局配置（旧版 YAML）
│   ├── agent.yaml              # Agent 配置（v0.1 兼容）
│   └── llm_providers.yaml      # LLM 提供商配置
├── skills/                     # 全局 Skills 库（所有项目共享）
├── memory/                     # 全局记忆数据
├── checkpoints/                # 全局断点快照
├── logs/                       # 全局日志
└── run.py                      # 入口脚本

[项目目录]/
├── .sloth/                     # 项目配置（轻量）
│   ├── project.yaml            # 项目名、路径、SPEC/PLAN 目录
│   └── local_skills/          # 项目专属 Skills（可选）
├── docs/                       # 文档（项目内）
│   ├── specs/
│   ├── plans/
│   └── reports/
├── TODO.md                     # 项目任务
└── [项目源代码...]
```

### 11.3 项目初始化（sloth init）

```bash
sloth init --project ~/my-project
```

初始化后创建完整项目结构：

```
~/my-project/
├── .env                        # 项目 API Key（覆盖全局）
├── .sloth/                     # Sloth Agent 项目配置
│   ├── config.json             # 项目统一配置（团队共享）
│   ├── config.local.json       # 项目个人覆盖（不纳入 git）
│   └── project.yaml            # 项目元信息
├── docs/                       # 文档（框架生成）
│   ├── specs/                  # 设计规格
│   ├── plans/                  # 实现计划
│   └── reports/                # 工作报告
├── src/                        # 源代码
│   └── (your code)
├── tests/                      # 测试代码
│   └── (your tests)
├── scripts/                    # 辅助脚本（如有）
├── README.md                   # 项目说明
├── LICENSE                     # 许可证（如有）
├── .gitignore                  # Git 忽略规则
├── pyproject.toml              # Python: uv 项目配置
│   # 或 Cargo.toml (Rust)
│   # 或 package.json (Node.js)
│   # 或 go.mod (Go)
└── TODO.md                     # 项目任务清单
```

### 11.4 安装方式

```bash
# 1. 克隆到全局目录
git clone git@github.com:x5/sloth-agent.git ~/.sloth-agent

# 2. 使用 uv 安装（与项目一致）
cd ~/.sloth-agent
uv venv .venv --quiet
uv pip install -e .

# 3. 添加 CLI shim 到 PATH
mkdir -p ~/.local/bin
cat > ~/.local/bin/sloth <<'EOF'
#!/bin/bash
exec "${HOME}/.sloth-agent/.venv/bin/sloth" "$@"
EOF
chmod +x ~/.local/bin/sloth
```

### 11.5 project.yaml 格式

```yaml
project:
  name: my-project
  path: /home/user/my-project
  docs_dir: docs                    # 文档目录（相对于项目根）
  spec_dir: docs/specs
  plan_dir: docs/plans
  report_dir: docs/reports

skills:
  global: ~/.sloth-agent/skills     # 全局 Skills
  local: .sloth/local_skills        # 项目专属 Skills

workflow:
  night_phase_time: "22:00"
  day_phase_time: "09:00"
  heartbeat_interval: 180          # 3 分钟

llm:
  default_provider: deepseek
  node_mapping:                    # 可选，覆盖全局配置
    brainstorming: glm
    planning: claude
```

### 11.6 使用方式

```bash
# 指定项目运行
sloth run --project ~/my-project --phase night
sloth run --project ~/my-project --phase day

# 查看状态
sloth status --project ~/my-project

# 查看帮助
sloth --help
```

### 11.7 与 OpenClaw/Hermes Agent 对比

| 特性 | OpenClaw | Hermes Agent | Sloth Agent |
|------|----------|--------------|-------------|
| 安装位置 | `~/.openclaw/` | `~/.hermes/` | `~/.sloth-agent/` |
| 安装方式 | `npm install -g` | Shell 脚本 | Shell 脚本 + CLI shim |
| 项目配置 | `~/.openclaw/openclaw.json` | 无 | `[项目]/.sloth/config.json` + `~/.sloth-agent/config.json` |
| Skills 位置 | `~/.openclaw/skills/` | `~/.hermes/skills/` | `~/.sloth-agent/skills/` + `[项目]/.sloth/local_skills/` |
| 多项目支持 | 是 | 否 | 是 |

---

*规范版本: v1.1.0*
*创建日期: 2026-04-16*
