"""sloth init CLI command — initialize a project directory."""

import json
from pathlib import Path

import typer
from rich.console import Console

console = Console(force_terminal=True, color_system="auto")


def init(
    project_dir: str | None = typer.Argument(
        None, help="Project directory (default: current directory)"
    ),
    provider: str = typer.Option(
        "deepseek", "--provider", "-p",
        help="Default LLM provider (deepseek, qwen, kimi, glm, minimax, xiaomi)"
    ),
    api_key: str | None = typer.Option(
        None, "--api-key", "-k",
        help="API key value (writes to project .env)"
    ),
):
    """Initialize a project directory for Sloth Agent.

    Creates .sloth/ config structure and an optional project .env file.
    After initialization, run 'sloth config show' to verify.
    """
    target = Path(project_dir) if project_dir else Path.cwd()
    target = target.resolve()

    if not target.exists():
        console.print(f"[red]Directory not found: {target}[/red]")
        raise typer.Exit(1)

    sloth_dir = target / ".sloth"
    console.print(f"[bold]Initializing Sloth Agent in {target}[/bold]")

    # Create .sloth directory
    sloth_dir.mkdir(exist_ok=True)
    console.print(f"  [green][+][/green] Created {sloth_dir.relative_to(target)}/")

    # Create project config.json
    project_config = sloth_dir / "config.json"
    if project_config.exists():
        console.print(f"  [dim][+][/dim] {project_config.relative_to(target)} already exists")
    else:
        config_data = {
            "llm": {"default_provider": provider},
            "agent": {"workspace": "./workspace"},
        }
        project_config.write_text(
            json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        console.print(f"  [green][+][/green] Created {project_config.relative_to(target)}")

    # Create project .env if API key provided
    env_file = target / ".env"
    if api_key:
        env_key = f"{provider.upper()}_API_KEY"
        lines = [f"# Project API Key (overrides global)", f"{env_key}={api_key}"]
        if env_file.exists():
            existing = env_file.read_text(encoding="utf-8")
            if env_key not in existing:
                existing = existing.rstrip() + f"\n{lines[0]}\n{lines[1]}\n"
                env_file.write_text(existing, encoding="utf-8")
                console.print(f"  [green][+][/green] Added {env_key} to .env")
            else:
                console.print(f"  [dim][+][/dim] {env_key} already in .env")
        else:
            env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
            console.print(f"  [green][+][/green] Created .env with {env_key}")
    elif not env_file.exists():
        env_example = target / ".env.example"
        if not env_example.exists():
            env_example.write_text(
                f"# Project API Key (overrides global)\n# {provider.upper()}_API_KEY=\n",
                encoding="utf-8",
            )
            console.print(f"  [green][+][/green] Created .env.example template")
        else:
            console.print(f"  [dim][+][/dim] .env.example already exists")

    # Create local_skills directory
    local_skills = sloth_dir / "local_skills"
    local_skills.mkdir(exist_ok=True)

    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. Set your API key: sloth config set llm.default_provider {provider} --scope project")
    console.print("  2. Or edit the project .env file directly")
    console.print("  3. Check config: sloth config show")
    console.print("  4. Verify env: sloth config env")
