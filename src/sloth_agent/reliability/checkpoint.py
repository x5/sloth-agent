"""Checkpoint - Persistent state management for task recovery."""

import json
import uuid
from datetime import datetime
from pathlib import Path

from sloth_agent.core.config import Config
from sloth_agent.core.state import TaskContext


class CheckpointManager:
    """Manages checkpoint save/restore for task execution."""

    def __init__(self, config: Config):
        self.config = config

        # Checkpoint directory: checkpoints/
        project_root = Path(__file__).parent.parent.parent.parent
        self.checkpoint_dir = project_root / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, task: TaskContext) -> str:
        """Save current task state to checkpoint."""
        checkpoint_id = task.checkpoint_id or str(uuid.uuid4())

        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "task": task.model_dump(),
            "saved_at": datetime.now().isoformat(),
        }

        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        checkpoint_file.write_text(json.dumps(checkpoint, indent=2, default=str))

        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str) -> TaskContext | None:
        """Load task state from checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"

        if not checkpoint_file.exists():
            return None

        data = json.loads(checkpoint_file.read_text())
        return TaskContext(**data["task"])

    def get_latest_checkpoint(self) -> tuple[str, TaskContext] | None:
        """Get the most recent checkpoint."""
        checkpoints = sorted(
            self.checkpoint_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not checkpoints:
            return None

        latest = checkpoints[0]
        data = json.loads(latest.read_text())
        return data["checkpoint_id"], TaskContext(**data["task"])

    def list_checkpoints(self) -> list[dict]:
        """List all available checkpoints."""
        result = []

        for cp_file in self.checkpoint_dir.glob("*.json"):
            data = json.loads(cp_file.read_text())
            result.append(
                {
                    "checkpoint_id": data["checkpoint_id"],
                    "saved_at": data["saved_at"],
                    "task_id": data["task"]["task_id"],
                }
            )

        return sorted(result, key=lambda x: x["saved_at"], reverse=True)

    def clear_checkpoint(self, checkpoint_id: str):
        """Remove a checkpoint file."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()
