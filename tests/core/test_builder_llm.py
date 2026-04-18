"""Tests for Builder.build_sync LLM integration (PE-3)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sloth_agent.core.builder import (
    Builder,
    BuilderOutput,
    CoverageReport,
    PlanTask,
)


class TestBuilderBuildSync:
    """PE-3: build_sync executes plan tasks and produces BuilderOutput."""

    def test_empty_plan_returns_empty_output(self):
        builder = Builder()
        result = builder.build_sync(
            plan_tasks=[],
            llm_provider=None,
            workspace=".",
        )
        assert result.changed_files == []
        assert result.branch is not None

    def test_task_with_embedded_code_writes_file(self, tmp_path: Path):
        builder = Builder()
        tasks = [
            PlanTask(
                id=1,
                title="Add helper",
                description="A helper function.",
                file_path="src/helper.py",
                code="def helper():\n    return 42\n",
            ),
        ]

        result = builder.build_sync(
            plan_tasks=tasks,
            llm_provider=None,
            workspace=str(tmp_path),
        )

        assert result.changed_files == ["src/helper.py"]
        assert (tmp_path / "src" / "helper.py").exists()
        assert tasks[0].done is True

    def test_task_calls_llm_when_no_code(self, tmp_path: Path):
        builder = Builder()
        tasks = [
            PlanTask(
                id=1,
                title="Create validator",
                description="A validator class.",
                file_path="src/validator.py",
                code=None,  # No embedded code
            ),
        ]

        # Mock LLM provider with sync generate method
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "class Validator:\n    def validate(self): pass\n"

        result = builder.build_sync(
            plan_tasks=tasks,
            llm_provider=mock_llm,
            workspace=str(tmp_path),
        )

        assert result.changed_files == ["src/validator.py"]
        mock_llm.generate.assert_called_once()
        file_content = (tmp_path / "src" / "validator.py").read_text()
        assert "class Validator" in file_content

    def test_multiple_tasks_produce_multiple_files(self, tmp_path: Path):
        builder = Builder()
        tasks = [
            PlanTask(id=1, title="Model", file_path="src/model.py", code="class Model: pass\n"),
            PlanTask(id=2, title="View", file_path="src/view.py", code="class View: pass\n"),
        ]

        result = builder.build_sync(
            plan_tasks=tasks,
            llm_provider=None,
            workspace=str(tmp_path),
        )

        assert len(result.changed_files) == 2
        assert (tmp_path / "src" / "model.py").exists()
        assert (tmp_path / "src" / "view.py").exists()

    def test_build_log_contains_task_info(self, tmp_path: Path):
        builder = Builder()
        tasks = [
            PlanTask(id=1, title="Add utils", file_path="utils.py", code="pass\n"),
        ]

        result = builder.build_sync(
            plan_tasks=tasks,
            llm_provider=None,
            workspace=str(tmp_path),
        )

        assert "Add utils" in (result.build_log or "")
        assert "utils.py" in (result.build_log or "")


class TestBuilderLLMIntegration:
    """PE-3: LLM call wrapper and file inference."""

    def test_call_llm_sync_provider(self):
        builder = Builder()
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "def foo(): pass\n"

        task = PlanTask(id=1, title="Add foo", description="foo function")
        code = builder._call_llm_for_task(task, mock_llm)
        assert "def foo" in code
        call_args = mock_llm.generate.call_args
        assert call_args is not None
        messages = call_args[1].get("messages") if "messages" in call_args[1] else call_args[0][0]
        # Verify the prompt contains the task info
        prompt_text = messages[0]["content"] if isinstance(messages, list) else str(messages)
        assert "Add foo" in prompt_text

    def test_call_llm_async_provider(self):
        builder = Builder()

        class AsyncMockProvider:
            async def chat(self, messages):
                return type("R", (), {"content": "async response"})()

        task = PlanTask(id=1, title="Async task")
        code = builder._call_llm_for_task(task, AsyncMockProvider())
        assert code == "async response"

    def test_call_llm_fallback_returns_empty(self):
        builder = Builder()
        task = PlanTask(id=1, title="No LLM")
        code = builder._call_llm_for_task(task, None)
        assert code == ""

    def test_infer_file_path_from_task_title(self):
        builder = Builder()

        task_test = PlanTask(id=1, title="test utils helper")
        assert "test_" in builder._infer_file_path(task_test, "")

        task_model = PlanTask(id=1, title="create user model")
        assert "models" in builder._infer_file_path(task_model, "")

        task_api = PlanTask(id=1, title="add user api endpoint")
        assert "api" in builder._infer_file_path(task_api, "")

    def test_infer_file_path_uses_task_path_if_set(self):
        builder = Builder()
        task = PlanTask(id=1, title="whatever", file_path="custom/file.py")
        result = builder._infer_file_path(task, "")
        assert result == "custom/file.py"

    def test_parse_pytest_output(self):
        builder = Builder()

        # Standard pytest output
        total, passed, failed = builder._parse_pytest_output("2 failed, 5 passed in 1.2s")
        assert total == 7
        assert passed == 5
        assert failed == 2

        # No failures
        total, passed, failed = builder._parse_pytest_output("3 passed in 0.5s")
        assert total == 3
        assert passed == 3
        assert failed == 0

        # Only failures
        total, passed, failed = builder._parse_pytest_output("1 failed in 0.1s")
        assert total == 1
        assert passed == 0
        assert failed == 1

    def test_get_branch_returns_main_on_error(self):
        builder = Builder()
        # Should not raise even if git is not available
        branch = builder._get_branch()
        assert isinstance(branch, str)
        assert len(branch) > 0
