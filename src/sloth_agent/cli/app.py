"""CLI entry point for Sloth Agent."""

import typer
from rich.console import Console

app = typer.Typer(help="Sloth Agent - AI development assistant")
console = Console()


@app.command()
def run():
    """Run in autonomous mode (day/night cycle)."""
    from sloth_agent.core.agent import AgentEvolve

    agent = AgentEvolve()
    agent.run()


@app.command()
def chat(
    model: str | None = typer.Option(None, "--model", "-m", help="Use specific model"),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Use specific provider"),
):
    """Enter interactive chat mode."""
    from sloth_agent.cli.chat import ChatSession

    session = ChatSession(model=model, provider=provider)
    session.loop()


@app.command()
def status():
    """Show agent status."""
    console.print("[bold]Sloth Agent v0.1.0[/bold]")
    console.print("Mode: autonomous (day/night cycle)")
    console.print("Config: configs/agent.yaml")


@app.command()
def skills(name: str | None = typer.Argument(None)):
    """List all available skills, or show details for a specific skill."""
    try:
        from sloth_agent.workflow.registry import SkillRegistry

        if name:
            skill = SkillRegistry.get(name)
            console.print(f"[bold]{skill.name}[/bold] ({skill.source})")
            console.print(skill.description)
        else:
            all_skills = SkillRegistry.get_all()
            console.print(f"[bold]{len(all_skills)} skills available[/bold]")
            for s in all_skills:
                console.print(f"  /{s.id} - {s.description}")
    except ImportError:
        console.print("[dim]Skill registry not yet available[/dim]")


@app.command()
def scenarios():
    """List all available workflow scenarios."""
    try:
        from sloth_agent.workflow.registry import PhaseRegistry

        reg = PhaseRegistry()
        console.print(f"[bold]{len(reg.list_scenarios())} scenarios[/bold]")
        for sid in reg.list_scenarios():
            phases = reg.get_by_scenario(sid)
            phase_names = ", ".join(f"{p.id}({p.name})" for p in phases)
            console.print(f"  {sid}: {phase_names}")
    except ImportError:
        console.print("[dim]Scenario registry not yet available[/dim]")


if __name__ == "__main__":
    app()
