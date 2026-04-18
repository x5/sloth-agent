"""Tests for PlanParser."""

from pathlib import Path

import pytest

from sloth_agent.core.plan_parser import PlanParser, PlanTask

# Real triple-backtick fence strings for tests
FENCE_OPEN = "```"
FENCE_CLOSE = "```"


class TestPlanParser:
    def test_parse_header_sections(self, tmp_path: Path):
        plan = tmp_path / "plan.md"
        plan.write_text("""# Task 1: Create user model
Define the User class with name and email.

# Task 2: Create API endpoint
Add a /users route.
""")
        tasks = PlanParser.parse(plan)
        assert len(tasks) == 2
        assert tasks[0].title == "Task 1: Create user model"
        assert tasks[1].title == "Task 2: Create API endpoint"

    def test_parse_code_blocks(self, tmp_path: Path):
        plan = tmp_path / "plan.md"
        content = (
            "# Task: Add calculator\n\n"
            f"{FENCE_OPEN}python src/calc.py\n"
            "def add(a, b):\n"
            "    return a + b\n"
            f"{FENCE_CLOSE}\n"
        )
        plan.write_text(content)
        tasks = PlanParser.parse(plan)
        assert len(tasks) == 1
        assert tasks[0].file_path == "src/calc.py"
        assert "def add" in (tasks[0].code or "")

    def test_parse_no_code(self, tmp_path: Path):
        plan = tmp_path / "plan.md"
        plan.write_text("""# Task: Write docs
Create a README with usage examples.
Some more description here.
""")
        tasks = PlanParser.parse(plan)
        assert len(tasks) == 1
        assert tasks[0].code is None
        assert "README" in tasks[0].description

    def test_parse_multiple_code_blocks(self, tmp_path: Path):
        plan = tmp_path / "plan.md"
        content = (
            "# Task: Full feature\n\n"
            f"{FENCE_OPEN}python src/models/user.py\n"
            "class User: pass\n"
            f"{FENCE_CLOSE}\n\n"
            "Some description text.\n\n"
            f"{FENCE_OPEN}python tests/test_user.py\n"
            "def test_user(): pass\n"
            f"{FENCE_CLOSE}\n"
        )
        plan.write_text(content)
        tasks = PlanParser.parse(plan)
        assert len(tasks) == 1
        assert "class User" in (tasks[0].code or "")
        # Last file hint wins
        assert tasks[0].file_path == "tests/test_user.py"

    def test_parse_text_direct(self):
        text = "## Fix login bug\nThe login fails when email is empty.\n"
        tasks = PlanParser.parse_text(text)
        assert len(tasks) == 1
        assert tasks[0].title == "Fix login bug"

    def test_parse_empty_plan(self, tmp_path: Path):
        plan = tmp_path / "plan.md"
        plan.write_text("")
        tasks = PlanParser.parse(plan)
        assert len(tasks) == 0

    def test_parse_h2_and_h3_headers(self, tmp_path: Path):
        plan = tmp_path / "plan.md"
        plan.write_text("""## Step 1
Description A.

### Step 1.1
Sub-description B.
""")
        tasks = PlanParser.parse(plan)
        assert len(tasks) == 2
        assert tasks[0].title == "Step 1"
        assert tasks[1].title == "Step 1.1"

    def test_plan_task_ids_are_sequential(self, tmp_path: Path):
        plan = tmp_path / "plan.md"
        plan.write_text("""# A
# B
# C
""")
        tasks = PlanParser.parse(plan)
        assert [t.id for t in tasks] == [1, 2, 3]

    def test_plan_task_defaults(self, tmp_path: Path):
        plan = tmp_path / "plan.md"
        plan.write_text("""# Simple task
Just a task with no code.
""")
        tasks = PlanParser.parse(plan)
        assert tasks[0].done is False
        assert tasks[0].description == "Just a task with no code."
