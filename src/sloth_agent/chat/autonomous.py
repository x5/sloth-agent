"""AutonomousController — manage autonomous mode from within chat."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AutonomousState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    COMPLETED = "completed"


@dataclass
class TaskStatus:
    """Status of the current autonomous task."""

    task_id: str = ""
    description: str = ""
    state: AutonomousState = AutonomousState.IDLE
    started_at: float = 0
    completed_at: float = 0
    current_step: str = ""
    steps: list[str] = field(default_factory=list)
    result: str = ""
    error: str = ""


class AutonomousController:
    """Control autonomous mode execution from the chat REPL.

    Provides start/stop/status for background autonomous tasks.
    The actual execution is delegated to the caller via callbacks.
    """

    def __init__(self):
        self._current_task: TaskStatus | None = None
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def current_task(self) -> TaskStatus | None:
        return self._current_task

    def is_running(self) -> bool:
        return (
            self._current_task is not None
            and self._current_task.state == AutonomousState.RUNNING
        )

    def start(
        self,
        task_id: str,
        description: str,
        steps: list[str],
        executor: Any,
    ) -> TaskStatus:
        """Start an autonomous task in a background thread.

        Args:
            task_id: Unique task identifier.
            description: Human-readable description.
            steps: List of step descriptions.
            executor: Callable(task_status, stop_flag) that performs the work.
        """
        if self.is_running():
            raise RuntimeError("A task is already running. Stop it first.")

        self._stop_flag.clear()
        self._current_task = TaskStatus(
            task_id=task_id,
            description=description,
            state=AutonomousState.RUNNING,
            started_at=time.time(),
            steps=steps,
        )

        self._thread = threading.Thread(
            target=self._run_task,
            args=(executor,),
            daemon=True,
        )
        self._thread.start()
        return self._current_task

    def stop(self) -> TaskStatus | None:
        """Signal the running task to stop."""
        if not self.is_running():
            return self._current_task

        self._current_task.state = AutonomousState.STOPPING
        self._stop_flag.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)

        if self._current_task:
            self._current_task.state = AutonomousState.IDLE
            self._current_task.completed_at = time.time()
        return self._current_task

    def get_status(self) -> dict:
        """Get current task status."""
        if self._current_task is None:
            return {"state": AutonomousState.IDLE, "task": None}

        task = self._current_task
        elapsed = time.time() - task.started_at if task.started_at else 0
        return {
            "state": task.state.value,
            "task_id": task.task_id,
            "description": task.description,
            "current_step": task.current_step,
            "steps": task.steps,
            "elapsed_seconds": round(elapsed, 1),
            "result": task.result,
            "error": task.error,
        }

    def _run_task(self, executor: Any) -> None:
        """Run the executor function in a background thread."""
        try:
            executor(self._current_task, self._stop_flag)
        except Exception as e:
            if self._current_task:
                self._current_task.error = str(e)
                self._current_task.state = AutonomousState.IDLE
        finally:
            if self._current_task and self._current_task.state == AutonomousState.RUNNING:
                self._current_task.state = AutonomousState.COMPLETED
                self._current_task.completed_at = time.time()
