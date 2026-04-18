"""Builder Agent with adaptive planning (spec §5.1)."""

from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class CoverageReport:
    """Test execution summary."""
    total: int = 0
    passed: int = 0
    failed: int = 0


@dataclass
class BuilderOutput:
    """Structured output from Builder phase."""
    branch: str
    changed_files: list[str]
    diff_summary: str
    test_results: CoverageReport = field(default_factory=CoverageReport)
    coverage: float = 0.0
    build_log: str | None = None


@dataclass
class PlanTask:
    """A task from the parsed plan."""
    id: int
    title: str
    description: str = ""
    file_path: str | None = None
    code: str | None = None
    done: bool = False


class BuildFailure(Exception):
    def __init__(self, task, reason):
        self.task = task
        self.reason = reason
        super().__init__(reason)


class Builder:
    """Builder Agent with reflection and adaptive planning."""

    async def build(self, plan, context) -> BuilderOutput:
        """Execute plan with reflection on gate failure."""
        tasks = self.parse_plan(plan)
        completed = []

        for task in tasks:
            while not task.done:
                result = await self.execute(task)
                gate = self.check_gate(result)

                if gate.passed:
                    task.done = True
                    completed.append(task)
                    continue

                # Reflection on failure
                reflection = await self.reflect(result, gate)
                context.update(reflection.learnings)

                if reflection.action == "replan":
                    return await self.build_with_replan(plan, context)
                elif reflection.action == "abort":
                    raise BuildFailure(task, reflection.root_cause)

                task.retries += 1
                if task.retries >= 3:
                    raise BuildFailure(task, "exceeded max retries")

        return self.collect_output(completed)

    async def build_with_replan(self, plan, context) -> BuilderOutput:
        """Dynamic replanning based on execution results."""
        tasks = self.parse_plan(plan)
        replan = await self.replan(plan, context)
        if replan.should_abort:
            raise BuildFailure(None, "Replan decided to abort")
        return self.collect_output([])

    def parse_plan(self, plan):
        return []

    async def execute(self, task):
        pass

    def check_gate(self, result):
        pass

    async def reflect(self, result, gate):
        pass

    async def replan(self, plan, context) -> ReplanResult:
        return ReplanResult(new_tasks=[], should_abort=False)

    def collect_output(self, completed) -> BuilderOutput:
        return BuilderOutput(branch="", changed_files=[])

    # -----------------------------------------------------------------------
    # v0.3 sync builder for Phase Execution Pipeline
    # -----------------------------------------------------------------------

    def build_sync(
        self,
        plan_tasks: list[PlanTask],
        llm_provider: Any = None,
        workspace: str = ".",
    ) -> BuilderOutput:
        """Execute plan tasks synchronously, generating code via LLM.

        For each task:
        1. Call LLM to generate code for the task
        2. Write generated code to file
        3. Run pytest after all tasks complete

        Args:
            plan_tasks: List of parsed plan tasks.
            llm_provider: LLM provider or manager instance.
            workspace: Root directory to write generated files.

        Returns:
            BuilderOutput with changed files and test results.
        """
        changed_files: list[str] = []
        build_log_parts: list[str] = []

        for task in plan_tasks:
            try:
                file_path, code = self._generate_for_task(task, llm_provider, workspace)
                if file_path:
                    changed_files.append(file_path)
                    build_log_parts.append(f"Task {task.id} ({task.title}): wrote {file_path}")
                    task.done = True
                else:
                    build_log_parts.append(f"Task {task.id} ({task.title}): no output")
            except Exception as e:
                build_log_parts.append(f"Task {task.id} ({task.title}): error — {e}")

        # Run pytest on workspace
        test_results, coverage = self._run_pytest_sync(workspace)

        branch = self._get_branch()
        build_log = "\n".join(build_log_parts)

        return BuilderOutput(
            branch=branch,
            changed_files=changed_files,
            diff_summary=build_log,
            test_results=test_results,
            coverage=coverage,
            build_log=build_log,
        )

    def _generate_for_task(
        self,
        task: PlanTask,
        llm_provider: Any,
        workspace: str,
    ) -> tuple[str | None, str | None]:
        """Generate code for a single plan task.

        If the task already has code embedded, use it.
        Otherwise call LLM to generate code.

        Returns: (relative_file_path, code_content)
        """
        code = task.code
        file_path = task.file_path

        # If no code is embedded, call LLM
        if not code and llm_provider is not None:
            code = self._call_llm_for_task(task, llm_provider)

        if not code:
            return None, None

        # Determine file path
        if not file_path:
            file_path = self._infer_file_path(task, code)

        # Write file
        full = Path(workspace) / file_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(code, encoding="utf-8")

        return file_path, code

    def _call_llm_for_task(self, task: PlanTask, llm_provider: Any) -> str:
        """Call LLM to generate code for a task.

        Supports both sync providers (with generate method) and
        async LLMProviderManager (wrapped with asyncio.run).
        """
        prompt = (
            f"You are a coding assistant. Generate Python code for the following task.\n"
            f"Only output code in a single fenced code block.\n\n"
            f"Task: {task.title}\n"
            f"Description: {task.description}\n"
        )
        if task.file_path:
            prompt += f"\nFile path: {task.file_path}\n"

        # Sync provider (has generate method)
        if hasattr(llm_provider, "generate"):
            return llm_provider.generate(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )

        # Async LLMProviderManager
        if hasattr(llm_provider, "chat"):
            try:
                from sloth_agent.providers.llm_providers import LLMMessage

                response = asyncio.run(
                    llm_provider.chat([LLMMessage("user", prompt)])
                )
                return response.content
            except Exception:
                pass

        return ""

    def _infer_file_path(self, task: PlanTask, code: str) -> str:
        """Infer a file path from task title or code content."""
        if task.file_path:
            return task.file_path

        # Try to infer from code (e.g., module docstring)
        title_lower = task.title.lower()
        if "test" in title_lower:
            name = title_lower.replace("test", "").strip().replace(" ", "_")
            return f"tests/test_{name}.py"
        if "model" in title_lower or "schema" in title_lower:
            name = title_lower.replace("model", "").replace("schema", "").strip().replace(" ", "_")
            return f"src/models/{name}.py"
        if "api" in title_lower or "endpoint" in title_lower or "route" in title_lower:
            name = title_lower.replace("api", "").replace("endpoint", "").replace("route", "").strip().replace(" ", "_")
            return f"src/api/{name}.py"

        # Default: derive from title
        name = title_lower.replace(" ", "_")
        return f"src/{name}.py"

    def _run_pytest_sync(self, workspace: str) -> tuple[CoverageReport, float]:
        """Run pytest and return test results + coverage."""
        try:
            r = subprocess.run(
                ["pytest", "--tb=short", "-q", workspace],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=60,
            )
            total, passed, failed = self._parse_pytest_output(r.stdout + r.stderr)
            return CoverageReport(total=total, passed=passed, failed=failed), 0.0
        except FileNotFoundError:
            return CoverageReport(), 0.0
        except subprocess.TimeoutExpired:
            return CoverageReport(total=0, passed=0, failed=0), 0.0

    def _parse_pytest_output(self, output: str) -> tuple[int, int, int]:
        """Parse pytest output for total/passed/failed counts."""
        failed = 0
        passed = 0
        # Look for "X failed, Y passed" pattern
        m = re.search(r"(\d+)\s+failed", output)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+)\s+passed", output)
        if m:
            passed = int(m.group(1))
        total = passed + failed
        return total, passed, failed

    def _get_branch(self) -> str:
        """Get current git branch."""
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            return r.stdout.strip() or "main"
        except Exception:
            return "main"


@dataclass
class ReplanResult:
    """Result of dynamic replanning."""
    new_tasks: list[Any]
    should_abort: bool = False
