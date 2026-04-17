"""Tests for AutonomousController."""

import threading
import time

import pytest

from sloth_agent.chat.autonomous import AutonomousController, AutonomousState


class TestAutonomousController:
    def test_starts_idle(self):
        ctrl = AutonomousController()
        assert not ctrl.is_running()
        assert ctrl.get_status()["state"] == "idle"

    def test_start_creates_task(self):
        ctrl = AutonomousController()

        def dummy_exec(task, stop_flag):
            time.sleep(0.1)

        task = ctrl.start("t1", "test task", ["step1"], dummy_exec)
        assert task.task_id == "t1"
        assert ctrl.is_running()
        # Wait for thread to finish
        time.sleep(0.3)

    def test_stop_while_running(self):
        ctrl = AutonomousController()
        barrier = threading.Event()

        def long_exec(task, stop_flag):
            for i in range(100):
                if stop_flag.is_set():
                    task.result = "stopped"
                    return
                time.sleep(0.05)
            task.result = "completed"

        ctrl.start("t1", "long task", ["step1", "step2"], long_exec)
        assert ctrl.is_running()

        result = ctrl.stop()
        assert result is not None
        assert result.result == "stopped"
        assert not ctrl.is_running()

    def test_cannot_start_two_tasks(self):
        ctrl = AutonomousController()

        def slow_exec(task, stop_flag):
            time.sleep(1)

        ctrl.start("t1", "first", ["step1"], slow_exec)
        with pytest.raises(RuntimeError, match="already running"):
            ctrl.start("t2", "second", ["step1"], slow_exec)

        ctrl.stop()

    def test_get_status_when_idle(self):
        ctrl = AutonomousController()
        status = ctrl.get_status()
        assert status["state"] == "idle"
        assert status["task"] is None

    def test_get_status_when_running(self):
        ctrl = AutonomousController()
        barrier = threading.Event()

        def blocking_exec(task, stop_flag):
            task.current_step = "working"
            barrier.wait()

        ctrl.start("t1", "blocking", ["working"], blocking_exec)
        status = ctrl.get_status()
        assert status["state"] == "running"
        assert status["task_id"] == "t1"
        assert status["current_step"] == "working"
        barrier.set()
        time.sleep(0.1)

    def test_error_sets_state(self):
        ctrl = AutonomousController()

        def failing_exec(task, stop_flag):
            raise ValueError("something broke")

        ctrl.start("t1", "fail task", ["step1"], failing_exec)
        time.sleep(0.2)
        status = ctrl.get_status()
        assert "something broke" in status["error"]
        assert not ctrl.is_running()

    def test_completed_state(self):
        ctrl = AutonomousController()

        def quick_exec(task, stop_flag):
            task.result = "done"

        ctrl.start("t1", "quick", ["step1"], quick_exec)
        time.sleep(0.2)
        status = ctrl.get_status()
        assert status["result"] == "done"
