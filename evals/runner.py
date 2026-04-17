"""Eval Runner - Execute eval tasks and collect results."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class TaskResult:
    name: str
    passed: bool
    metrics: dict = field(default_factory=dict)
    error: str | None = None


@dataclass
class EvalReport:
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: list[TaskResult] = field(default_factory=list)


class EvalRunner:
    """Run eval tasks and collect results."""

    def __init__(self, tasks_file: Path):
        self.tasks_file = tasks_file
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> list[dict]:
        data = yaml.safe_load(self.tasks_file.read_text())
        return data.get("eval_tasks", [])

    def run_all(self, config=None) -> EvalReport:
        """Run all eval tasks."""
        report = EvalReport()
        for task_def in self.tasks:
            result = self.run_task(task_def["name"], config)
            report.results.append(result)
            report.total += 1
            if result.passed:
                report.passed += 1
            else:
                report.failed += 1
        return report

    def run_task(self, task_name: str, config=None) -> TaskResult:
        """Run a single eval task by name."""
        task_def = None
        for t in self.tasks:
            if t["name"] == task_name:
                task_def = t
                break
        if task_def is None:
            return TaskResult(name=task_name, passed=False, error=f"Task '{task_name}' not found")

        # v1.0: validate that the plan file exists and is parseable
        plan_path = Path(task_def.get("plan", ""))
        if not plan_path.exists():
            return TaskResult(name=task_name, passed=False, error=f"Plan file missing: {plan_path}")

        content = plan_path.read_text()
        if not content.strip():
            return TaskResult(name=task_name, passed=False, error="Plan file is empty")

        return TaskResult(name=task_name, passed=True, metrics={"plan_length": len(content)})
