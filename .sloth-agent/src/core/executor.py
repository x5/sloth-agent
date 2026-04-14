"""Executor module - executes tasks with reliability guarantees."""

import uuid
from datetime import datetime
from pathlib import Path

from sloth_agent.core.config import Config
from sloth_agent.core.state import ExecutionStep, TaskContext, TaskState


class Executor:
    """Executes tasks with TDD enforcement, checkpointing, and verification."""

    def __init__(self, config: Config):
        self.config = config

    def load_approved_tasks(self) -> list[TaskContext]:
        """Load approved tasks from docs/plans/ directory."""
        project_root = Path(__file__).parent.parent.parent.parent
        plans_dir = project_root / "docs" / "plans"
        today = datetime.now().strftime("%Y-%m-%d")

        plan_file = plans_dir / f"plan-{today}.json"
        if not plan_file.exists():
            return []

        plan_data = json.loads(plan_file.read_text())
        tasks = [TaskContext(**t) for t in plan_data.get("tasks", [])]
        return [t for t in tasks if plan_data.get("approved", False)]

    def execute_tasks(self, tasks: list[TaskContext]) -> list[TaskContext]:
        """Execute all tasks with monitoring and recovery."""
        from sloth_agent.core.tools.tool_registry import ToolRegistry
        from sloth_agent.reliability.checkpoint import CheckpointManager
        from sloth_agent.reliability.verifier import TaskVerifier

        registry = ToolRegistry(self.config)
        checkpoint_mgr = CheckpointManager(self.config)
        verifier = TaskVerifier(self.config)

        results = []

        for task in tasks:
            task.state = TaskState.RUNNING
            task.updated_at = datetime.now()

            checkpoint_id = checkpoint_mgr.save_checkpoint(task)
            task.checkpoint_id = checkpoint_id

            try:
                result = self._execute_task_with_tdd(task, registry, verifier)
                results.append(result)

            except Exception as e:
                task.state = TaskState.FAILED
                task.error_context = str(e)
                results.append(task)

            checkpoint_mgr.save_checkpoint(task)

        return results

    def _execute_task_with_tdd(
        self, task: TaskContext, registry, verifier
    ) -> TaskContext:
        """Execute a single task with TDD workflow."""
        from sloth_agent.tdd.enforcer import TDDEnforcer

        enforcer = TDDEnforcer(self.config)

        # TDD Phase 1: Write test first
        enforcer.enforce_write_test_first(task, registry)

        # TDD Phase 2: Implement
        result = self._implement_task(task, registry)

        # TDD Phase 3: Verify
        verified = verifier.verify_task(task)

        if verified:
            task.state = TaskState.SUCCEED
        else:
            task.state = TaskState.FAILED

        return task

    def _implement_task(self, task: TaskContext, registry) -> any:
        """Execute the actual task implementation."""
        # TODO: Implement tool orchestration
        pass
