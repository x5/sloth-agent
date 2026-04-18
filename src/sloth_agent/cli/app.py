"""CLI entry point for Sloth Agent."""

import typer
from rich.console import Console

import sloth_agent

app = typer.Typer(help="Sloth Agent - AI development assistant")
console = Console()

# Register sub-commands
from sloth_agent.cli.config_cmd import config_app
from sloth_agent.cli.init_cmd import init
from sloth_agent.cli.uninstall_cmd import uninstall
from sloth_agent.cli.skill_cmd import skill_app
from sloth_agent.cli.cost_cmd import cost_app
app.add_typer(config_app, name="config")
app.add_typer(skill_app, name="skills")
app.add_typer(cost_app, name="cost")
app.command()(init)
app.command()(uninstall)


@app.command()
def run(plan: str | None = typer.Argument(None, help="Plan file path")):
    """Run in autonomous mode (Plan -> Builder -> Reviewer -> Deployer)."""
    import uuid

    from pathlib import Path

    from rich.console import Console
    from sloth_agent.core.config import load_config
    from sloth_agent.core.orchestrator import ProductOrchestrator
    from sloth_agent.core.runner import Runner, RunState

    console = Console()
    config = load_config()
    orchestrator = ProductOrchestrator(config)

    # Try to resolve plan path
    resolved_plan: str | None = None
    if plan:
        p = Path(plan)
        if p.exists():
            resolved_plan = str(p.resolve())
        elif (Path.cwd() / p).exists():
            resolved_plan = str((Path.cwd() / p).resolve())

    # Initialize LLM provider if configured
    llm_provider = None
    cost_tracker = None
    try:
        from sloth_agent.cost.tracker import CostTracker
        from sloth_agent.providers.llm_providers import LLMProviderManager

        cost_tracker = CostTracker()
        llm_provider = LLMProviderManager(cost_tracker=cost_tracker)
    except Exception:
        llm_provider = None

    runner = Runner(
        config,
        orchestrator.tool_registry,
        llm_provider=llm_provider,
    )

    # Create run state
    run_id = uuid.uuid4().hex[:12]
    state = RunState(
        run_id=run_id,
        current_agent="builder",
        current_phase="build",
        phase="running",
        metadata={"plan_path": resolved_plan} if resolved_plan else {},
    )

    console.print(f"[bold]Sloth Agent v{sloth_agent.__version__}[/bold]")
    console.print(f"Run ID: {run_id}")
    console.print(f"Plan: {resolved_plan or '(none)'}")
    if llm_provider:
        console.print(f"LLM: connected")
    else:
        console.print(f"[dim]LLM: not connected (code-only mode)[/dim]")

    try:
        final_state = runner.run(state)
        if final_state.phase == "completed":
            console.print("[green]Pipeline completed successfully![/green]")
            if final_state.output:
                console.print(final_state.output)
        else:
            console.print(f"[red]Pipeline ended: {final_state.phase}[/red]")
            if final_state.errors:
                for err in final_state.errors:
                    console.print(f"  - {err}")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise SystemExit(1)


@app.command()
def chat(
    model: str | None = typer.Option(None, "--model", "-m", help="Use specific model"),
    provider: str | None = typer.Option(None, "--provider", "-p", help="Use specific provider"),
):
    """Enter interactive chat mode."""
    from sloth_agent.chat.repl import EnhancedChatSession

    session = EnhancedChatSession(model=model, provider=provider)
    session.loop()


@app.command()
def status():
    """Show agent status."""
    console.print(f"[bold]Sloth Agent v{sloth_agent.__version__}[/bold]")
    console.print("Mode: autonomous (day/night cycle)")
    console.print("Config: configs/agent.yaml")


@app.command()
def skills(name: str | None = typer.Argument(None)):
    """List all available skills, or show details for a specific skill."""
    from rich.console import Console

    builtin_dir = Path(__file__).parent.parent.parent.parent / "skills" / "builtin"
    try:
        from sloth_agent.memory.skill_registry import SkillRegistry

        registry = SkillRegistry(builtin_dir=builtin_dir)
        if name:
            skill = registry.get(name)
            if skill:
                console.print(f"[bold]{skill.name}[/bold] ({skill.source})")
                console.print(f"[dim]{skill.description}[/dim]")
                console.print()
                console.print(skill.content)
            else:
                console.print(f"[red]Skill '{name}' not found[/red]")
        else:
            all_skills = registry.get_all()
            console.print(f"[bold]{len(all_skills)} skills available[/bold]")
            for s in all_skills:
                console.print(f"  {s.id} - {s.description}")
    except Exception as e:
        console.print(f"[red]Error loading skills: {e}[/red]")


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
