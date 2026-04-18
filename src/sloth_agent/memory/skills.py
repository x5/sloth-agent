"""SkillManager - Load SKILL.md files from the filesystem."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Skill:
    """A skill loaded from a SKILL.md file (Claude Code format)."""

    id: str
    name: str
    source: str  # builtin | user | evolved
    trigger: str  # auto | manual | auto+manual | error-driven
    description: str
    content: str
    allowed_tools: list[str] = field(default_factory=list)

    @classmethod
    def from_markdown(cls, text: str) -> "Skill":
        """Parse a SKILL.md text into a Skill instance."""
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
        if not m:
            raise ValueError("SKILL.md must start with YAML frontmatter: ---")
        fm_yaml = m.group(1)
        body = m.group(2).strip()

        fm = yaml.safe_load(fm_yaml)
        return cls(
            id=fm.get("name", ""),
            name=fm.get("name", "").replace("-", " ").title(),
            source=fm.get("source", "user"),
            trigger=fm.get("trigger", "manual"),
            description=fm.get("description", ""),
            content=body,
            allowed_tools=fm.get("allowed-tools", []),
        )


class SkillManager:
    """Scan directories for SKILL.md files and provide skill content."""

    def __init__(self, skills_dirs: list[Path] | None = None):
        self.skills_dirs = skills_dirs or []
        self._cache: dict[str, Skill] = {}

    def load_all_skills(self) -> list[Skill]:
        """Scan all search directories for SKILL.md files."""
        if not self._cache:
            for skills_dir in self.skills_dirs:
                if not skills_dir.is_dir():
                    continue
                for skill_file in skills_dir.rglob("SKILL.md"):
                    try:
                        text = skill_file.read_text(encoding="utf-8")
                        skill = Skill.from_markdown(text)
                        self._cache[skill.id] = skill
                    except (ValueError, Exception):
                        continue
        return list(self._cache.values())

    def get_skill_content(self, skill_id: str) -> str | None:
        """Get the content of a specific skill for LLM prompt injection."""
        if not self._cache:
            self.load_all_skills()
        skill = self._cache.get(skill_id)
        return skill.content if skill else None

    def list_skills(self) -> list[str]:
        """List all skill IDs."""
        if not self._cache:
            self.load_all_skills()
        return list(self._cache.keys())
