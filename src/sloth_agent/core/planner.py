"""Planner module - generates daily plans from specs and context."""

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from sloth_agent.core.config import Config
from sloth_agent.core.state import PlanContext, TaskContext


class Planner:
    """Generates daily execution plans based on specs and memory."""

    def __init__(self, config: Config):
        self.config = config

    def generate_daily_plan(self) -> PlanContext | None:
        """Generate a plan for tomorrow based on today's context."""
        spec = self._read_spec()
        if not spec:
            return None

        yesterday_report = self._load_yesterday_report()
        relevant_skills = self._retrieve_relevant_skills(spec)
        context = self._build_context(spec, yesterday_report, relevant_skills)

        tasks = self._generate_tasks(context)

        plan = PlanContext(
            plan_id=str(uuid.uuid4()),
            date=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
            tasks=tasks,
        )

        self._save_plan(plan)
        return plan

    def _read_spec(self) -> str | None:
        """Read the latest spec from docs/specs/ directory."""
        # Look in docs/specs relative to the project root
        project_root = Path(__file__).parent.parent.parent.parent
        specs_dir = project_root / "docs" / "specs"

        if not specs_dir.exists():
            return None

        spec_files = list(specs_dir.glob("*.md")) + list(specs_dir.glob("*.txt"))
        if not spec_files:
            return None

        latest = max(spec_files, key=lambda p: p.stat().st_mtime)
        return latest.read_text()

    def _load_yesterday_report(self) -> dict | None:
        """Load yesterday's execution report."""
        from sloth_agent.memory.store import MemoryStore

        store = MemoryStore(self.config)
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        return store.load_report(yesterday)

    def _retrieve_relevant_skills(self, spec: str) -> list[dict]:
        """Retrieve skills relevant to current spec."""
        from sloth_agent.memory.retrieval import MemoryRetrieval

        retrieval = MemoryRetrieval(self.config)
        return retrieval.search_skills(spec, top_k=5)

    def _build_context(
        self, spec: str, yesterday_report: dict | None, skills: list[dict]
    ) -> dict:
        """Build context for LLM to generate plan."""
        return {
            "spec": spec,
            "yesterday_report": yesterday_report,
            "relevant_skills": skills,
            "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
        }

    def _generate_tasks(self, context: dict) -> list[TaskContext]:
        """Generate tasks using LLM."""
        # TODO: Integrate with LLM provider
        # For now, return placeholder structure
        return [
            TaskContext(
                task_id="task-1",
                description="Read and understand current project state",
                tools_needed=["read_file", "search"],
            ),
        ]

    def _save_plan(self, plan: PlanContext):
        """Save plan to docs/plans/ directory."""
        project_root = Path(__file__).parent.parent.parent.parent
        plans_dir = project_root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)

        plan_file = plans_dir / f"plan-{plan.date}.json"
        plan_file.write_text(plan.model_dump_json(indent=2))
