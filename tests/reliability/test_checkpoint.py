"""Tests for Git checkpoint in CheckpointManager."""

import subprocess
import tempfile

import pytest

from sloth_agent.reliability.checkpoint import CheckpointManager


@pytest.fixture()
def checkpoint_manager():
    """Create a CheckpointManager backed by a temp git repo."""
    tmpdir = tempfile.mkdtemp()
    subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir, check=True, capture_output=True)
    # Initial commit
    (tempfile.Path(tmpdir) / "init.txt").write_text("init") if False else None
    import pathlib
    pathlib.Path(tmpdir, "init.txt").write_text("init")
    subprocess.run(["git", "add", "."], cwd=tmpdir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmpdir, check=True, capture_output=True)
    return CheckpointManager(repo_path=tmpdir)


def test_create_and_rollback(checkpoint_manager: CheckpointManager):
    """Create git tag checkpoint, then rollback."""
    cm = checkpoint_manager

    # Make a change
    import pathlib
    pathlib.Path(cm.repo_path, "change.txt").write_text("change")
    subprocess.run(["git", "add", "."], cwd=cm.repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add change"], cwd=cm.repo_path, check=True, capture_output=True)

    # Create checkpoint
    tag = cm.create_git_checkpoint("stage", "test-stage")
    assert "sloth/stage/test-stage" in tag

    # Make another change
    pathlib.Path(cm.repo_path, "change2.txt").write_text("change2")
    subprocess.run(["git", "add", "."], cwd=cm.repo_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add change2"], cwd=cm.repo_path, check=True, capture_output=True)

    # Rollback to checkpoint
    result = cm.rollback_to(tag)
    assert result.success is True
    # The change2 file should no longer be tracked
    assert not pathlib.Path(cm.repo_path, "change2.txt").exists()


def test_auto_commit(checkpoint_manager: CheckpointManager):
    """auto_commit() creates a git commit."""
    cm = checkpoint_manager
    import pathlib
    pathlib.Path(cm.repo_path, "task_output.txt").write_text("task result")
    commit_hash = cm.auto_commit(task="test-task", result={"status": "done"})
    assert commit_hash is not None

    log = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=cm.repo_path,
        capture_output=True,
        text=True,
    )
    assert "test-task" in log.stdout
