"""sloth config CLI command — view/edit/validate unified configuration."""

import json
from pathlib import Path
from typing import Any

import typer

config_app = typer.Typer(help="Manage Sloth Agent configuration")


@config_app.command()
def show(
    scope: str | None = typer.Option(
        None, "--scope", "-s",
        help="Show only one scope level: user, project, or local"
    ),
    raw: bool = typer.Option(
        False, "--raw", "-r",
        help="Show raw merged JSON instead of formatted tree"
    ),
):
    """Show current configuration (merged from all scopes)."""
    from sloth_agent.core.config_manager import ConfigManager

    cm = ConfigManager()

    if scope:
        data = cm.load_scope(scope)
        if not data:
            typer.echo(f"No config found at {scope} scope.")
            raise typer.Exit(1)
    else:
        data = cm.load_raw()

    if not data:
        typer.echo("No configuration found. Run 'sloth config init' to create one.")
        raise typer.Exit(1)

    typer.echo(json.dumps(data, indent=2, ensure_ascii=False))


@config_app.command()
def set(
    path: str = typer.Argument(..., help="Config path to set, e.g. llm.default_provider"),
    value: str = typer.Argument(..., help="Value to set"),
    scope: str = typer.Option(
        "local", "--scope", "-s",
        help="Which scope to write to: user, project, or local"
    ),
):
    """Set a config value at the specified scope."""
    from sloth_agent.core.config_manager import ConfigManager

    cm = ConfigManager()

    # Parse the value: try JSON types, fallback to string
    parsed = _parse_value(value)

    # Build nested dict from path
    keys = path.split(".")
    data = _build_nested(keys, parsed)

    saved = cm.save(data, scope=scope)
    typer.echo(f"Saved {path} = {value!r} to {saved}")


@config_app.command()
def validate():
    """Validate the current merged configuration."""
    from sloth_agent.core.config_manager import ConfigManager

    cm = ConfigManager()
    errors = cm.validate()

    if errors:
        typer.echo("Configuration errors:", err=True)
        for e in errors:
            typer.echo(f"  ✗ {e}", err=True)
        raise typer.Exit(1)
    else:
        typer.echo("Configuration is valid.")


@config_app.command(name="env")
def env_check():
    """List all required API key environment variables and their status."""
    from sloth_agent.core.config_manager import ConfigManager

    cm = ConfigManager()
    status = cm.check_env_vars()

    if not status:
        typer.echo("No API keys configured in config.json.")
        return

    all_set = True
    for var, is_set in status.items():
        icon = "✓" if is_set else "✗"
        if not is_set:
            all_set = False
        typer.echo(f"  {icon} {var}")

    typer.echo()
    if all_set:
        typer.echo("All API keys are configured.")
    else:
        typer.echo("Missing API keys. Set them in .env or as environment variables.")
        typer.echo("  Copy ~/.sloth-agent/.env.example to ~/.sloth-agent/.env and edit.")


@config_app.command()
def init(
    scope: str = typer.Option(
        "user", "--scope", "-s",
        help="Which scope to initialize: user, project, or local"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i",
        help="Interactive wizard to configure provider, API key, and workspace"
    ),
):
    """Create a config.json template at the specified scope, or run interactive wizard."""
    from sloth_agent.core.config_manager import ConfigManager

    if interactive:
        _run_interactive_init(scope)
        return

    cm = ConfigManager()

    # Load the example template
    example = Path(__file__).parent.parent.parent.parent / "configs" / "config.json.example"
    if not example.exists():
        typer.echo("config.json.example not found. Cannot initialize.", err=True)
        raise typer.Exit(1)

    data = json.loads(example.read_text(encoding="utf-8"))

    if scope == "user":
        # For user scope, save to ~/.sloth-agent/config.json
        import shutil
        target = cm._user_config
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(example, target)
        typer.echo(f"Created {target}")
    else:
        saved = cm.save(data, scope=scope)
        typer.echo(f"Created {saved}")


def _parse_value(value: str):
    """Try to parse value as JSON type, fallback to string."""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return value


def _build_nested(keys: list[str], value: Any) -> dict:
    """Build a nested dict from a dot-separated path."""
    result = {}
    current = result
    for key in keys[:-1]:
        current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return result


def _run_interactive_init(scope: str) -> None:
    """Interactive configuration wizard using prompt_toolkit."""
    from prompt_toolkit import prompt
    from prompt_toolkit.shortcuts import radiolist_dialog
    from prompt_toolkit.validation import Validator

    from sloth_agent.core.config_manager import ConfigManager

    typer.echo()
    typer.echo("=== Sloth Agent Configuration Wizard ===")
    typer.echo()

    # Step 1: Choose scope
    if scope == "user":
        typer.echo("Scope: user (global ~/.sloth-agent/)")
    else:
        typer.echo(f"Scope: {scope} (current project)")

    # Step 2: Choose provider
    providers = [
        ("deepseek", "DeepSeek  (coding + reasoning)"),
        ("qwen", "Qwen / Tongyi Qianwen  (review + coding)"),
        ("kimi", "Kimi / Moonshot  (vision)"),
        ("glm", "GLM / Zhipu  (coding)"),
        ("minimax", "MiniMax  (evolution)"),
        ("xiaomi", "Xiaomi / MiMo  (coding)"),
    ]
    result = radiolist_dialog(
        title="Select LLM Provider",
        text="Choose your default AI model provider:",
        values=providers,
    ).run()
    if result is None:
        typer.echo("Cancelled.")
        raise typer.Exit(0)
    provider = result

    # Step 3: API Key
    typer.echo()
    env_var = f"{provider.upper()}_API_KEY"
    api_key = prompt(
        f"Enter {env_var} (hidden, or press Enter to skip): ",
        is_password=True,
    )

    # Step 4: Workspace path
    typer.echo()
    workspace = prompt(
        "Workspace directory: ",
        default="./workspace",
    ).strip()

    # Build config
    config_data = {
        "llm": {
            "default_provider": provider,
            "providers": {
                provider: {
                    "api_key_env": env_var,
                    "base_url": _get_base_url(provider),
                    "models": _get_default_models(provider),
                }
            },
        },
        "agent": {
            "name": "sloth-agent",
            "workspace": workspace,
            "timezone": "Asia/Shanghai",
        },
    }

    # Step 5: Confirmation
    typer.echo()
    typer.echo("Configuration summary:")
    typer.echo(f"  Scope:          {scope}")
    typer.echo(f"  Provider:       {provider}")
    typer.echo(f"  API Key:        {'[set]' if api_key else '[skipped]'}")
    typer.echo(f"  Workspace:      {workspace}")
    typer.echo(f"  Config file:    {scope} level")
    typer.echo()

    # Step 6: Write
    cm = ConfigManager()
    saved = cm.save(config_data, scope=scope)
    typer.echo(f"Config saved to: {saved}")

    # Write API Key to .env if provided
    if api_key:
        env_path = saved.parent / ".env"
        lines = [f"# API Keys (auto-generated by sloth config init --interactive)"]
        lines.append(f"{env_var}={api_key}")
        if env_path.exists():
            existing = env_path.read_text(encoding="utf-8")
            if env_var not in existing:
                env_path.write_text(
                    existing.rstrip() + "\n" + "\n".join(lines) + "\n",
                    encoding="utf-8",
                )
                typer.echo(f"API Key added to: {env_path}")
            else:
                typer.echo(f"{env_var} already in .env, not overwritten")
        else:
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            typer.echo(f"Created: {env_path}")

    # Step 7: Validate
    typer.echo()
    errors = cm.validate()
    if errors:
        typer.echo("Warnings:")
        for e in errors:
            typer.echo(f"  [dim]⚠[/dim] {e}")
    else:
        typer.echo("[green]Configuration is valid.[/green]")

    typer.echo()
    typer.echo("Next steps:")
    typer.echo("  sloth config show    — view full configuration")
    typer.echo("  sloth config env     — check API key status")
    typer.echo("  sloth chat           — start interactive chat")


def _get_base_url(provider: str) -> str:
    """Return the default base_url for a given provider."""
    urls = {
        "deepseek": "https://api.deepseek.com/v1",
        "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "kimi": "https://api.moonshot.cn/v1",
        "glm": "https://open.bigmodel.cn/api/paas/v4",
        "minimax": "https://api.minimax.chat/v1",
        "xiaomi": "https://api.mioffice.cn/openapi/llm",
    }
    return urls.get(provider, "")


def _get_default_models(provider: str) -> dict[str, str]:
    """Return default model mappings for a given provider."""
    models = {
        "deepseek": {"coding": "deepseek-v3.2", "reasoning": "deepseek-r1-0528"},
        "qwen": {"review": "qwen3.6-plus"},
        "kimi": {"vision": "kimi-k2.5"},
        "glm": {"coding": "glm-5.1"},
        "minimax": {"evolution": "minimax-m2.7"},
        "xiaomi": {"coding": "mimo-v2-pro"},
    }
    return models.get(provider, {})
