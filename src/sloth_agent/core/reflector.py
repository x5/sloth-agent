"""Reflector module - self-reflection and skill evolution."""

from datetime import datetime

from sloth_agent.core.config import Config
from sloth_agent.core.state import ReportContext


class Reflector:
    """Handles self-reflection, skill creation and revision."""

    def __init__(self, config: Config):
        self.config = config

    def reflect(self, report: ReportContext):
        """Perform self-reflection on the day's execution."""
        # Analyze errors and create/revise skills
        if report.errors_encountered:
            self._process_errors(report.errors_encountered)

        # Revise existing skills based on new experiences
        if report.tasks_summary:
            self._review_and_revise_skills(report.tasks_summary)

    def _process_errors(self, errors: list):
        """Process errors and generate skill improvements."""
        from sloth_agent.memory.skills import SkillManager

        skill_mgr = SkillManager(self.config)

        for error in errors:
            skill = skill_mgr.generate_skill_from_error(error)
            if skill:
                skill_mgr.save_skill(skill)

    def _review_and_revise_skills(self, tasks_summary: dict):
        """Review and revise existing skills based on task outcomes."""
        from sloth_agent.memory.skills import SkillManager

        skill_mgr = SkillManager(self.config)

        for task_id, outcome in tasks_summary.items():
            if outcome.get("state") == "succeed":
                skill_mgr.consider_skill_extension(task_id, outcome)
            elif outcome.get("state") == "failed":
                skill_mgr.consider_skill_fix(task_id, outcome)
