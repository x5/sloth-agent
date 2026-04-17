"""Tests for eval runner."""

import tempfile
from pathlib import Path

import yaml

from evals.runner import EvalRunner


def test_eval_runner_single_task():
    """Eval runner can execute a single task."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        plan_file = tmp / "plan.md"
        plan_file.write_text("# Test Plan\n\nDo something.")

        tasks_file = tmp / "tasks.yaml"
        tasks_data = {
            "eval_tasks": [
                {
                    "name": "test-task",
                    "plan": str(plan_file),
                    "expected": {"tests_pass": True},
                }
            ]
        }
        tasks_file.write_text(yaml.safe_dump(tasks_data))

        runner = EvalRunner(tasks_file)
        result = runner.run_task("test-task")
        assert result.passed is True
        assert result.metrics.get("plan_length", 0) > 0
