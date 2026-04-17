"""Checkpoint - Persistent state management and git-based checkpoints."""

import json
import subprocess
import uuid
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class RollbackResult(BaseModel):
    success: bool
    tag: str = ""
    message: str = ""


class CheckpointManager:
    """Manages JSON checkpoint files and git-based checkpoints."""

    def __init__(self, repo_path: str | Path | None = None, config=None):
        self.config = config

        if repo_path:
            self.repo_path = str(repo_path)
        else:
            project_root = Path(__file__).parent.parent.parent.parent
            self.repo_path = str(project_root)

        # JSON checkpoint directory
        self.checkpoint_dir = Path(self.repo_path) / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, task_context) -> str:
        """Save current task state to checkpoint."""
        checkpoint_id = getattr(task_context, "checkpoint_id", None) or str(uuid.uuid4())
        checkpoint = {
            "checkpoint_id": checkpoint_id,
            "task": task_context.model_dump() if hasattr(task_context, "model_dump") else str(task_context),
            "saved_at": datetime.now().isoformat(),
        }
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        checkpoint_file.write_text(json.dumps(checkpoint, indent=2, default=str))
        return checkpoint_id

    def load_checkpoint(self, checkpoint_id: str):
        """Load task state from checkpoint."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if not checkpoint_file.exists():
            return None
        data = json.loads(checkpoint_file.read_text())
        return data

    def get_latest_checkpoint(self):
        """Get the most recent checkpoint."""
        checkpoints = sorted(
            self.checkpoint_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not checkpoints:
            return None
        latest = checkpoints[0]
        return latest.stem, json.loads(latest.read_text())

    def list_checkpoints(self) -> list[dict]:
        """List all available checkpoints."""
        result = []
        for cp_file in self.checkpoint_dir.glob("*.json"):
            data = json.loads(cp_file.read_text())
            result.append({
                "checkpoint_id": data["checkpoint_id"],
                "saved_at": data["saved_at"],
            })
        return sorted(result, key=lambda x: x["saved_at"], reverse=True)

    def clear_checkpoint(self, checkpoint_id: str):
        """Remove a checkpoint file."""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()

    # -----------------------------------------------------------------------
    # Git-based three-level checkpoint (spec §5, arch §8.3)
    # -----------------------------------------------------------------------

    def create_git_checkpoint(self, level: str, label: str) -> str:
        """Create a git tag checkpoint.

        Args:
            level: 'session' | 'stage' | 'task'
            label: identifier, e.g. session_id or stage name
        """
        tag = f"sloth/{level}/{label}"
        subprocess.run(
            ["git", "tag", "-f", tag],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )
        return tag

    def rollback_to(self, tag: str) -> RollbackResult:
        """Rollback workspace to a git checkpoint.

        Creates a safety backup tag before resetting.
        """
        safety_tag = f"sloth/backup/{tag.replace('/', '_')}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        try:
            # Create safety backup of current state
            subprocess.run(
                ["git", "tag", "-f", safety_tag],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            # Hard reset to the checkpoint
            subprocess.run(
                ["git", "reset", "--hard", tag],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            # Clean untracked files
            subprocess.run(
                ["git", "clean", "-fd"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            return RollbackResult(success=True, tag=tag, message=f"Rolled back to {tag}")
        except subprocess.CalledProcessError as e:
            return RollbackResult(success=False, tag=tag, message=f"Rollback failed: {e.stderr.decode()}")

    def auto_commit(self, task: str, result: dict) -> str | None:
        """Auto-commit after a task completes successfully.

        Returns the short commit hash, or None if nothing to commit.
        """
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            # Check if there's anything to commit
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            if not status.stdout.strip():
                return None

            msg = f"[sloth] auto-commit: task={task} result={result.get('status', 'unknown')}"
            subprocess.run(
                ["git", "commit", "-m", msg],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            # Get the commit hash
            log = subprocess.run(
                ["git", "log", "--oneline", "-1"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            return log.stdout.strip().split()[0] if log.stdout.strip() else None
        except subprocess.CalledProcessError:
            return None
