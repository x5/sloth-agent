# 安装与引导规范

> 版本: v1.0.0
> 日期: 2026-04-16
> 状态: 新增

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
# LLM API Keys (至少配置一个)
DEEPSEEK_API_KEY=
QWEN_API_KEY=
KIMI_API_KEY=
GLM_API_KEY=
MINIMAX_API_KEY=

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
| `configs/agent.yaml.example` | 配置模板 |
| `.env.example` | 环境变量模板 |
| `skills/user/example_skill/SKILL.md` | 示例技能 |

---

---

## 10. 全局安装与多项目架构（从跨模块规范迁入）

### 10.1 设计理念

Sloth Agent 作为**全局工具**安装，一次安装，所有项目通用（类似 OpenClaw/Hermes Agent）。

### 10.2 目录结构

```
~/.sloth-agent/                  # 全局安装目录（~/.sloth-agent/）
├── src/                        # 框架源码（全局一份）
├── configs/                    # 全局配置
│   ├── agent.yaml              # Agent 配置
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

### 10.3 项目初始化（sloth init）

```bash
sloth init --project ~/my-project
```

初始化后创建完整项目结构：

```
~/my-project/
├── .sloth/                     # Sloth Agent 项目配置
│   └── project.yaml
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

### 10.4 安装方式

```bash
# 1. 克隆到全局目录
git clone git@github.com:x5/sloth-agent.git ~/.sloth-agent

# 2. 使用 uv 安装（与项目一致）
cd ~/.sloth-agent
uv venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e .

# 3. 添加到 PATH（可选，或使用绝对路径）
echo 'export PATH="$HOME/.sloth-agent:$PATH"' >> ~/.bashrc
```

### 10.5 project.yaml 格式

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

### 10.6 使用方式

```bash
# 指定项目运行
sloth run --project ~/my-project --phase night
sloth run --project ~/my-project --phase day

# 查看状态
sloth status --project ~/my-project

# 查看帮助
sloth --help
```

### 10.7 与 OpenClaw/Hermes Agent 对比

| 特性 | OpenClaw | Hermes Agent | Sloth Agent |
|------|----------|--------------|-------------|
| 安装位置 | `~/.openclaw/` | `~/.hermes/` | `~/.sloth-agent/` |
| 安装方式 | `npm install -g` | Shell 脚本 | `git clone` + `uv pip install -e` |
| 项目配置 | `~/.openclaw/openclaw.json` | 无 | `[项目]/.sloth/project.yaml` |
| Skills 位置 | `~/.openclaw/skills/` | `~/.hermes/skills/` | `~/.sloth-agent/skills/` + `[项目]/.sloth/local_skills/` |
| 多项目支持 | 是 | 否 | 是 |

---

*规范版本: v1.0.0*
*创建日期: 2026-04-16*
