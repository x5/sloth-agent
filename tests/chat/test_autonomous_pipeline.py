"""Tests for autonomous pipeline integration in REPL."""

import pytest
from unittest.mock import patch, MagicMock

from sloth_agent.chat.autonomous import AutonomousController, AutonomousState


class TestAutonomousPipeline:
    def test_autonomous_controller_starts_task(self):
        controller = AutonomousController()
        executed = []

        def fake_exec(task, stop_flag):
            executed.append(task.task_id)

        controller.start(
            task_id="test-pipeline",
            description="Test",
            steps=["step 1"],
            executor=fake_exec,
        )
        import time
        time.sleep(0.2)
        assert "test-pipeline" in executed
        controller.stop()

    def test_stop_flag_respected(self):
        controller = AutonomousController()
        saw_stop = []

        def fake_exec(task, stop_flag):
            stop_flag.wait(timeout=2)
            saw_stop.append(stop_flag.is_set())

        controller.start(
            task_id="test-stop",
            description="Test stop flag",
            steps=["step 1"],
            executor=fake_exec,
        )
        import time
        time.sleep(0.1)
        controller.stop()
        assert saw_stop[0] is True

    def test_status_shows_running(self):
        import threading
        controller = AutonomousController()
        barrier = threading.Event()

        def fake_exec(task, stop_flag):
            task.current_step = "working"
            barrier.wait()

        controller.start(
            task_id="test-status",
            description="Test",
            steps=["step 1"],
            executor=fake_exec,
        )
        status = controller.get_status()
        assert status["state"] == "running"
        assert status["current_step"] == "working"
        barrier.set()
        controller.stop()

    def test_error_captured(self):
        controller = AutonomousController()

        def fake_exec(task, stop_flag):
            raise ValueError("test error")

        controller.start(
            task_id="test-error",
            description="Test",
            steps=["step 1"],
            executor=fake_exec,
        )
        import time
        time.sleep(0.2)
        status = controller.get_status()
        assert "test error" in status["error"]
