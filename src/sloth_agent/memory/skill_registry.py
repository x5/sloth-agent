"""SkillRegistry — central management of all skills."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from sloth_agent.memory.skills import Skill, SkillManager
from sloth_agent.memory.skill_router import SkillRouter
from sloth_agent.memory.skill_validator import SkillValidator


@dataclass
class SkillEntry:
    """A skill with enabled/disabled state."""

    skill: Skill
    enabled: bool = True


class SkillRegistry:
    """Central registry for all skills.

    Manages builtin + user + local skills with enable/disable toggles.
    Wraps SkillManager (file loading) and provides routing/search interfaces.
    """

    def __init__(
        self,
        builtin_dir: Path | None = None,
        user_dir: Path | None = None,
        local_dir: Path | None = None,
    ):
        self._skills: dict[str, SkillEntry] = {}
        self._validator = SkillValidator()
        self._router: SkillRouter | None = None

        # Build search directories
        dirs: list[Path] = []
        if builtin_dir:
            dirs.append(builtin_dir)
        if user_dir:
            dirs.append(user_dir)
        if local_dir:
            dirs.append(local_dir)

        # Load skills from all directories
        manager = SkillManager(skills_dirs=dirs)
        skills = manager.load_all_skills()

        for skill in skills:
            # Register with validator for duplicate detection
            self._validator.register_known(skill.id, skill.description)
            self._skills[skill.id] = SkillEntry(skill=skill)

        # Build router
        self._router = SkillRouter(self.get_all())

    def get(self, skill_id: str) -> Skill | None:
        """Get a skill by ID, or None if not found/disabled."""
        entry = self._skills.get(skill_id)
        if entry and entry.enabled:
            return entry.skill
        return None

    def get_all(self) -> list[Skill]:
        """Get all enabled skills."""
        return [e.skill for e in self._skills.values() if e.enabled]

    def search(self, query: str) -> list[Skill]:
        """Search skills by query."""
        if self._router:
            matches = self._router.match_all(query)
            return [m.skill for m in matches]
        return []

    def match_skill(self, user_input: str) -> Skill | None:
        """Match user input to best skill, return the skill or None."""
        if self._router:
            match = self._router.match(user_input)
            if match and match.confidence >= 0.5:
                return match.skill
        return None

    def enable(self, skill_id: str) -> bool:
        """Enable a skill."""
        if skill_id in self._skills:
            self._skills[skill_id].enabled = True
            self._rebuild_router()
            return True
        return False

    def disable(self, skill_id: str) -> bool:
        """Disable a skill."""
        if skill_id in self._skills:
            self._skills[skill_id].enabled = False
            self._rebuild_router()
            return True
        return False

    def is_enabled(self, skill_id: str) -> bool:
        """Check if a skill is enabled."""
        entry = self._skills.get(skill_id)
        return entry.enabled if entry else False

    def list_all(self) -> list[tuple[str, str, bool]]:
        """List all skills with their enabled status."""
        return [
            (e.skill.id, e.skill.description, e.enabled)
            for e in self._skills.values()
        ]

    def _rebuild_router(self) -> None:
        """Rebuild the router index after enable/disable changes."""
        self._router = SkillRouter(self.get_all())
