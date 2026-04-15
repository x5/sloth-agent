"""Sloth Agent - Main Agent Loop."""

import logging
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from sloth_agent.core.config import load_config
from sloth_agent.core.state import PlanContext, ReportContext, TaskState

console = Console()


class AgentEvolve:
    """
    Self-driving, self-evolving AI Agent Framework.

    Daily Cycle:
    1. Night: Read SPEC -> Generate PLAN -> Await Approval
    2. Day: Execute PLAN -> Generate Report -> Self-Reflection
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config = load_config(config_path)
        self._setup_logging()
        self.console = Console()

    def _setup_logging(self):
        """Configure logging with rich handler."""
        log_file = Path(self.config.memory.vector_db_path).parent / "logs" / "agent.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[
                RichHandler(console=console, rich_tracebacks=True),
                logging.FileHandler(log_file),
            ],
        )
        self.logger = logging.getLogger("sloth-agent")

    def run(self):
        """Main execution loop."""
        self.logger.info("Sloth Agent Framework starting...")

        hour = datetime.now().hour

        # Determine phase: Night (22:00-05:00) or Day (06:00-21:00)
        if hour >= 22 or hour < 6:
            self._run_night_phase()
        else:
            self._run_day_phase()

    def _run_night_phase(self):
        """Execute night phase: SPEC -> PLAN -> Approval."""
        self.logger.info("Night Phase: Generating plan...")

        from sloth_agent.core.planner import Planner

        planner = Planner(self.config)
        plan = planner.generate_daily_plan()

        if plan:
            self._display_plan(plan)
            self._await_approval(plan)
        else:
            self.logger.warning("No plan generated, waiting for manual spec update")

    def _run_day_phase(self):
        """Execute day phase: Execute PLAN -> Report -> Reflect."""
        self.logger.info("Day Phase: Executing approved plan...")

        from sloth_agent.core.executor import Executor
        from sloth_agent.core.reflector import Reflector
        from sloth_agent.core.reporter import Reporter

        executor = Executor(self.config)
        tasks = executor.load_approved_tasks()

        if not tasks:
            self.logger.info("No approved tasks to execute, sleeping until night phase")
            return

        results = executor.execute_tasks(tasks)

        reporter = Reporter(self.config)
        report = reporter.generate_report(results)

        reflector = Reflector(self.config)
        reflector.reflect(report)

        self._display_report(report)

    def _display_plan(self, plan: PlanContext):
        """Display plan in a formatted table."""
        table = Table(title=f"Daily Plan - {plan.date}")
        table.add_column("Task", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("Tools Needed", style="magenta")

        for task in plan.tasks:
            tools = ", ".join(task.tools_needed) if task.tools_needed else "None"
            table.add_row(task.task_id, task.description, tools)

        self.console.print(table)

    def _await_approval(self, plan: PlanContext):
        """Send plan for human approval via configured channels."""
        from sloth_agent.human.review import ApprovalClient

        client = ApprovalClient(self.config)
        client.send_plan_for_approval(plan)

        self.logger.info("Awaiting human approval...")

    def _display_report(self, report: ReportContext):
        """Display execution report."""
        table = Table(title=f"Execution Report - {report.date}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        total_tasks = len(report.tasks_summary)
        succeeded = sum(1 for t in report.tasks_summary.values() if t.get("state") == "succeed")
        failed = sum(1 for t in report.tasks_summary.values() if t.get("state") == "failed")

        table.add_row("Total Tasks", str(total_tasks))
        table.add_row("Succeeded", str(succeeded))
        table.add_row("Failed", str(failed))
        table.add_row("Errors", str(len(report.errors_encountered)))
        table.add_row("Skills Created", str(len(report.skills_created)))
        table.add_row("Skills Revised", str(len(report.skills_revised)))

        self.console.print(table)
