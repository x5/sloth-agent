"""CLI commands for cost tracking."""

from __future__ import annotations

import typer

cost_app = typer.Typer(help="Query LLM cost tracking")


@cost_app.command()
def summary():
    """Show today's cost summary."""
    from rich.console import Console
    from rich.table import Table

    from sloth_agent.cost.tracker import CostTracker

    console = Console()
    tracker = CostTracker()

    table = Table(title="Cost Summary")
    table.add_column("Metric")
    table.add_column("Value")

    table.add_row("Total Calls", str(len(tracker.records)))
    table.add_row("Total Cost", f"${tracker.get_total_cost():.4f}")
    table.add_row("Daily Cost", f"${tracker.get_daily_cost():.4f}")
    table.add_row("Daily Tokens", str(tracker.get_daily_tokens()))

    console.print(table)

    # Breakdown by model
    by_model = tracker.get_cost_by_model()
    if by_model:
        model_table = Table(title="Cost by Model")
        model_table.add_column("Model")
        model_table.add_column("Cost")
        for model_name, cost in by_model.items():
            model_table.add_row(model_name, f"${cost:.4f}")
        console.print(model_table)


@cost_app.command()
def breakdown():
    """Show detailed cost breakdown."""
    from rich.console import Console
    from rich.table import Table

    from sloth_agent.cost.tracker import CostTracker

    console = Console()
    tracker = CostTracker()
    bd = tracker.get_breakdown()

    table = Table(title="Cost Breakdown")
    table.add_column("Category")
    table.add_column("Value")

    table.add_row("Total Cost", f"${bd.total:.4f}")
    table.add_row("Total Calls", str(bd.total_calls))
    table.add_row("Total Tokens", str(bd.total_tokens))

    console.print(table)

    if bd.by_provider:
        provider_table = Table(title="By Provider")
        provider_table.add_column("Provider")
        provider_table.add_column("Cost")
        for prov, cost in bd.by_provider.items():
            provider_table.add_row(prov, f"${cost:.4f}")
        console.print(provider_table)

    if bd.by_scenario:
        scenario_table = Table(title="By Scenario")
        scenario_table.add_column("Scenario")
        scenario_table.add_column("Cost")
        for scenario, cost in bd.by_scenario.items():
            scenario_table.add_row(scenario, f"${cost:.4f}")
        console.print(scenario_table)
