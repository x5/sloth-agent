"""Reporter module - generates execution reports."""

import json
from datetime import datetime
from pathlib import Path

from sloth_agent.core.config import Config
from sloth_agent.core.state import ReportContext, TaskContext


class Reporter:
    """Generates daily execution reports."""

    def __init__(self, config: Config):
        self.config = config

    def generate_report(self, task_results: list[TaskContext]) -> ReportContext:
        """Generate a report from task execution results."""
        report_id = f"report-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"

        tasks_summary = {}
        errors = []

        for task in task_results:
            tasks_summary[task.task_id] = {
                "description": task.description,
                "state": task.state.value,
                "retries": task.retries,
                "error": task.error_context.error_message if task.error_context else None,
            }

            if task.error_context:
                errors.append(task.error_context)

        report = ReportContext(
            report_id=report_id,
            date=datetime.now().strftime("%Y-%m-%d"),
            plan_id="",  # TODO: Link to plan
            tasks_summary=tasks_summary,
            errors_encountered=errors,
        )

        self._save_report(report)
        return report

    def _save_report(self, report: ReportContext):
        """Save report to docs/reports/ directory."""
        project_root = Path(__file__).parent.parent.parent.parent
        reports_dir = project_root / "docs" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        report_file = reports_dir / f"{report.report_id}.json"
        report_file.write_text(report.model_dump_json(indent=2))
