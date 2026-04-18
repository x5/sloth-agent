"""CLI commands for skill management."""

from __future__ import annotations

from pathlib import Path

import typer

skill_app = typer.Typer(help="Manage skills")


@skill_app.command()
def list():
    """List all available skills."""
    from rich.console import Console

    from sloth_agent.memory.skill_registry import SkillRegistry

    console = Console()
    builtin_dir = Path(__file__).parent.parent.parent.parent / "skills" / "builtin"

    try:
        registry = SkillRegistry(builtin_dir=builtin_dir)
        skills = registry.list_all()
        if not skills:
            console.print("[dim]No skills found[/dim]")
            return
        console.print(f"[bold]{len(skills)} skills available[/bold]")
        for sid, desc, enabled in skills:
            status = "[green]enabled[/green]" if enabled else "[dim]disabled[/dim]"
            console.print(f"  {sid} — {desc} ({status})")
    except Exception as e:
        console.print(f"[red]Error loading skills: {e}[/red]")


@skill_app.command()
def show(skill_id: str):
    """Show details of a specific skill."""
    from rich.console import Console

    from sloth_agent.memory.skill_registry import SkillRegistry

    console = Console()
    builtin_dir = Path(__file__).parent.parent.parent.parent / "skills" / "builtin"

    try:
        registry = SkillRegistry(builtin_dir=builtin_dir)
        skill = registry.get(skill_id)
        if skill:
            console.print(f"[bold]{skill.name}[/bold] ({skill.source})")
            console.print(f"[dim]{skill.description}[/dim]")
            # Use plain text instead of Markdown to avoid Windows encoding issues
            # with special characters in rendered markdown
            console.print()
            console.print(skill.content)
        else:
            console.print(f"[red]Skill '{skill_id}' not found[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@skill_app.command()
def search(query: str):
    """Search skills by query."""
    from rich.console import Console

    from sloth_agent.memory.skill_registry import SkillRegistry

    console = Console()
    builtin_dir = Path(__file__).parent.parent.parent.parent / "skills" / "builtin"

    try:
        registry = SkillRegistry(builtin_dir=builtin_dir)
        results = registry.search(query)
        if results:
            console.print(f"[bold]{len(results)} matches for '{query}'[/bold]")
            for skill in results:
                console.print(f"  {skill.id} — {skill.description}")
        else:
            console.print(f"[dim]No skills match '{query}'[/dim]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")


@skill_app.command()
def validate(path: str | None = typer.Argument(None)):
    """Validate SKILL.md files in a path."""
    from rich.console import Console
    from rich.table import Table

    from sloth_agent.memory.skill_validator import SkillValidator

    console = Console()
    validator = SkillValidator()

    if path:
        p = Path(path)
        if p.is_file():
            results = [validator.validate_file(p)]
        elif p.is_dir():
            results = validator.validate_directory(p)
        else:
            console.print(f"[red]Path not found: {path}[/red]")
            return
    else:
        # Validate builtin skills by default
        builtin_dir = Path(__file__).parent.parent.parent.parent / "skills" / "builtin"
        results = validator.validate_directory(builtin_dir)

    table = Table(title="Skill Validation")
    table.add_column("File")
    table.add_column("Status")
    table.add_column("Details")

    valid_count = 0
    for result in results:
        status = "PASS" if result.valid else "FAIL"
        if result.valid:
            valid_count += 1
        details = "; ".join(result.errors or result.warnings or ["OK"])
        table.add_row(result.path, status, details)

    console.print(table)
    console.print(f"\n{valid_count}/{len(results)} passed")
