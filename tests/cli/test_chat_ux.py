"""Tests for ChatUX — welcome screen, help, Chinese-first, confirm cards, progress."""

from pathlib import Path

import pytest
from rich.console import Console

from sloth_agent.cli.chat_ux import ChatUX


def _capture(console: Console, fn, *args, **kwargs) -> str:
    """Capture Rich console output from a function call."""
    with console.capture() as capture:
        fn(*args, **kwargs)
    return capture.get()


class TestWelcomeScreen:
    """Welcome screen display tests."""

    def test_welcome_screen_shown(self, tmp_path: Path):
        """Startup should show welcome with banner and suggested questions."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(console, ux.show_welcome, workspace=tmp_path)
        assert "预设问题" in output

    def test_welcome_context_aware(self, tmp_path: Path):
        """With plan file, should generate 'execute plan' suggestion."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        # Create plan file
        (tmp_path / "plan.md").write_text("# Plan\n")
        # Create code file
        (tmp_path / "main.py").write_text("print('hi')\n")

        questions = ux.generate_suggested_questions(tmp_path)
        assert any("plan" in q.lower() or "执行" in q for q in questions)
        assert any("代码" in q or "审查" in q for q in questions)

    def test_welcome_default_questions(self, tmp_path: Path):
        """With no special files, should use default question."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        questions = ux.generate_suggested_questions(tmp_path)
        assert "帮我写一个需求文档" in questions

    def test_welcome_shows_todo(self, tmp_path: Path):
        """With TODO.md, should suggest viewing task list."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        (tmp_path / "TODO.md").write_text("# TODO\n")
        questions = ux.generate_suggested_questions(tmp_path)
        assert any("任务" in q or "TODO" in q for q in questions)

    def test_welcome_limits_to_4(self, tmp_path: Path):
        """Should return at most 4 questions."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        # Create all detectable files
        (tmp_path / "plan.md").write_text("# Plan\n")
        (tmp_path / "main.py").write_text("x=1\n")
        (tmp_path / "test_main.py").write_text("def test(): pass\n")
        (tmp_path / "TODO.md").write_text("# TODO\n")

        questions = ux.generate_suggested_questions(tmp_path)
        assert len(questions) <= 4


class TestNaturalHelp:
    """Natural language help display tests."""

    def test_natural_help_format(self):
        """Help should show capability descriptions, not just command list."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(console, ux.show_natural_help)
        # Should contain capability descriptions
        assert "聊天对话" in output
        assert "执行命令" in output
        assert "编辑文件" in output

    def test_natural_help_advanced_folded(self):
        """Advanced commands should be below the divider line."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(console, ux.show_natural_help)
        assert "高级命令" in output

    def test_natural_help_status_line(self):
        """Should show session ID and skill count if provided."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(
            console, ux.show_natural_help,
            session_id="abc123",
            skill_count=5,
        )
        assert "abc123" in output
        assert "5" in output


class TestChineseFirst:
    """Chinese-first output tests."""

    def test_chinese_system_prompt(self):
        """The system prompt in REPL should contain Chinese characters."""
        from sloth_agent.chat.repl import EnhancedChatSession

        session = EnhancedChatSession()
        messages = session._build_messages("hello")
        system_prompt = messages[0].content
        # Should contain Chinese
        assert any(c in system_prompt for c in "你是开发")

    def test_chinese_error_messages(self):
        """Error display should use Chinese labels."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(console, ux.show_error, message="连接失败")
        assert "错误" in output


class TestStructuredOutput:
    """Rich table output tests."""

    def test_structured_output_table(self):
        """Should render a Rich Table, not plain text."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(
            console, ux.show_structured_result,
            title="工具列表",
            rows=[("read_file", "只读", "低")],
            headers=["工具", "用途", "风险"],
        )
        assert "工具" in output
        assert "read_file" in output

    def test_diff_preview(self):
        """Diff preview should use Panel with file path."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(
            console, ux.show_diff_preview,
            filepath="test.py",
            diff_lines=["+new line", "-old line"],
        )
        assert "test.py" in output


class TestConfirmCards:
    """Confirmation card tests."""

    def test_confirm_card_shown(self, monkeypatch):
        """High-risk operations should show confirmation with file list."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        # Monkeypatch input to return 'y'
        monkeypatch.setattr("builtins.input", lambda prompt="": "y")

        result = ux.show_confirm(
            file_changes=[{"file": "test.py", "lines": 10, "type": "modify"}],
            commands=["pytest"],
        )
        assert result is True

    def test_confirm_card_default_yes(self, monkeypatch):
        """Empty input should be treated as confirmation (default Y)."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        monkeypatch.setattr("builtins.input", lambda prompt="": "")

        result = ux.show_confirm(
            file_changes=[],
            commands=["run test"],
        )
        assert result is True

    def test_confirm_card_no_cancel(self, monkeypatch):
        """'n' input should cancel."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        monkeypatch.setattr("builtins.input", lambda prompt="": "n")

        result = ux.show_confirm(
            file_changes=[],
            commands=["dangerous cmd"],
        )
        assert result is False

    def test_delete_confirm_requires_explicit(self, monkeypatch):
        """Deleting files requires typing DELETE."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        monkeypatch.setattr("builtins.input", lambda prompt="": "DELETE")

        result = ux.show_delete_confirm(filepath="test.py")
        assert result is True

    def test_delete_confirm_wrong_input(self, monkeypatch):
        """Wrong input should not confirm deletion."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        monkeypatch.setattr("builtins.input", lambda prompt="": "y")

        result = ux.show_delete_confirm(filepath="test.py")
        assert result is False


class TestProgress:
    """Progress indicator tests."""

    def test_progress_spinner(self):
        """Should create a Progress object with spinner."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        progress = ux.create_progress("测试中…")
        assert progress is not None
        # Should have at least 2 columns (spinner + text)
        assert len(progress.columns) >= 2

    def test_status_panel(self):
        """Status panel should show phase, progress, and steps."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(
            console, ux.show_status_panel,
            phase="构建",
            progress_pct=50,
            completed=["解析"],
            current="编码",
            pending=["审查"],
            elapsed="30s",
        )
        assert "构建" in output
        assert "50%" in output
        assert "自主模式" in output

    def test_error_with_retry(self):
        """Error display should include retry count if provided."""
        console = Console(force_terminal=True, width=80)
        ux = ChatUX(console)

        output = _capture(console, ux.show_error, message="超时", retry_count=3)
        assert "错误" in output
        # "重试" may be split by ANSI codes, check for parts
        assert "重试" in output or "retry" in output.lower()
        assert "3" in output
