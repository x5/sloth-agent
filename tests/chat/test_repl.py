"""Tests for enhanced REPL with tool execution and autonomous mode."""

import time

import pytest

from sloth_agent.chat.repl import EnhancedChatSession
from sloth_agent.chat.autonomous import AutonomousController, AutonomousState


class TestEnhancedChatSession:
    def test_init_creates_instance(self):
        session = EnhancedChatSession()
        assert session is not None
        assert session.autonomous is not None
        assert session.tool_registry is not None

    def test_slash_commands_dict_has_new_commands(self):
        from sloth_agent.chat.repl import _SLASH_COMMANDS

        assert "/skill <name>" in _SLASH_COMMANDS
        assert "/start autonomous" in _SLASH_COMMANDS
        assert "/stop" in _SLASH_COMMANDS
        assert "/status" in _SLASH_COMMANDS


class TestAutonomousController:
    def test_starts_idle(self):
        controller = AutonomousController()
        assert not controller.is_running()

    def test_start_sets_running(self):
        import threading
        controller = AutonomousController()
        barrier = threading.Event()

        def blocking_exec(task, stop_flag):
            barrier.wait()

        controller.start(
            task_id="test-1",
            description="Test task",
            steps=["step 1"],
            executor=blocking_exec,
        )
        assert controller.is_running()
        barrier.set()
        time.sleep(0.1)

    def test_stop_transitions_to_idle(self):
        import threading
        controller = AutonomousController()
        barrier = threading.Event()

        def blocking_exec(task, stop_flag):
            for _ in range(50):
                if stop_flag.is_set():
                    task.result = "stopped"
                    return
                time.sleep(0.05)
            barrier.set()

        controller.start(
            task_id="test-2",
            description="Test task",
            steps=["step 1"],
            executor=blocking_exec,
        )
        controller.stop()
        assert not controller.is_running()

    def test_cannot_start_when_running(self):
        import threading
        controller = AutonomousController()
        barrier = threading.Event()

        def blocking_exec(task, stop_flag):
            barrier.wait()

        controller.start(
            task_id="test-3",
            description="Test task",
            steps=["step 1"],
            executor=blocking_exec,
        )
        with pytest.raises(RuntimeError, match="already running"):
            controller.start(
                task_id="test-4",
                description="Another task",
                steps=["step 1"],
                executor=blocking_exec,
            )
        barrier.set()
        time.sleep(0.1)

    def test_get_status_returns_dict(self):
        controller = AutonomousController()
        status = controller.get_status()
        assert "state" in status

    def test_status_shows_running(self):
        import threading
        controller = AutonomousController()
        barrier = threading.Event()

        def blocking_exec(task, stop_flag):
            task.current_step = "working"
            barrier.wait()

        controller.start(
            task_id="test-5",
            description="Test task",
            steps=["step 1"],
            executor=blocking_exec,
        )
        status = controller.get_status()
        assert status["state"] == "running"
        barrier.set()
        time.sleep(0.1)

    def test_stop_when_not_running_is_safe(self):
        controller = AutonomousController()
        result = controller.stop()
        assert result is None


class TestSlashCommandHandling:
    def test_unknown_command_shows_error(self, capsys):
        session = EnhancedChatSession()
        session._handle_slash("/bogus")
        captured = capsys.readouterr()
        assert "未知命令" in captured.out

    def test_skill_without_name_shows_usage(self, capsys):
        session = EnhancedChatSession()
        session._handle_slash("/skill")
        captured = capsys.readouterr()
        assert "Usage" in captured.out

    def test_start_without_autonomous_shows_usage(self, capsys):
        session = EnhancedChatSession()
        session._handle_slash("/start something")
        captured = capsys.readouterr()
        assert "Usage" in captured.out

    def test_quit_returns_true(self):
        session = EnhancedChatSession()
        assert session._handle_slash("/quit") is True

    def test_stop_when_not_running(self, capsys):
        session = EnhancedChatSession()
        session._handle_slash("/stop")
        captured = capsys.readouterr()
        assert "自主模式未运行" in captured.out
