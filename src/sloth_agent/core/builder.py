"""Builder Agent with adaptive planning (spec §5.1)."""

from dataclasses import dataclass, field
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
class ReplanResult:
    """Result of dynamic replanning."""
    new_tasks: list[Any]
    should_abort: bool = False


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
