"""Skill Manager - Creates, updates, and manages skills."""

import uuid
from datetime import datetime
from pathlib import Path

import yaml

from sloth_agent.core.config import Config
from sloth_agent.core.state import ErrorContext


class Skill:
    """Represents a reusable skill."""

    def __init__(
        self,
        name: str,
        version: str,
        tags: list[str],
        triggers: list[str],
        content: str,
        created: str | None = None,
        updated: str | None = None,
        revision_reason: str | None = None,
    ):
        self.name = name
        self.version = version
        self.tags = tags
        self.triggers = triggers
        self.content = content
        self.created = created or datetime.now().strftime("%Y-%m-%d")
        self.updated = updated or datetime.now().strftime("%Y-%m-%d")
        self.revision_reason = revision_reason

    def to_markdown(self) -> str:
        """Convert skill to markdown format."""
        frontmatter = {
            "name": self.name,
            "version": self.version,
            "created": self.created,
            "updated": self.updated,
            "tags": self.tags,
            "triggers": self.triggers,
        }

        if self.revision_reason:
            frontmatter["revision_reason"] = self.revision_reason

        md = "---\n"
        md += yaml.dump(frontmatter, allow_unicode=True)
        md += "---\n\n"
        md += self.content
        return md

    @classmethod
    def from_markdown(cls, md: str) -> "Skill":
        """Parse skill from markdown."""
        parts = md.split("---")
        if len(parts) < 3:
            raise ValueError("Invalid skill markdown format")

        frontmatter = yaml.safe_load(parts[1])
        content = "---".join(parts[2:]).strip()

        return cls(
            name=frontmatter["name"],
            version=frontmatter["version"],
            tags=frontmatter.get("tags", []),
            triggers=frontmatter.get("triggers", []),
            content=content,
            created=frontmatter.get("created"),
            updated=frontmatter.get("updated"),
            revision_reason=frontmatter.get("revision_reason"),
        )


class SkillManager:
    """Manages skill lifecycle: creation, revision, and retrieval."""

    def __init__(self, config: Config):
        self.config = config

        # Skills directory: .sloth-agent/skills/
        project_root = Path(__file__).parent.parent.parent.parent
        self.skills_dir = project_root / ".sloth-agent" / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def generate_skill_from_error(self, error: ErrorContext) -> Skill | None:
        """Generate a new skill from an error encountered."""
        # TODO: Use LLM to generate skill content based on error
        if not error.skill_suggestion:
            return None

        skill = Skill(
            name=f"error-recovery-{error.error_type}",
            version="1.0.0",
            tags=["error-recovery", error.error_type],
            triggers=[error.error_type, error.error_message[:50]],
            content=error.skill_suggestion,
        )

        return skill

    def save_skill(self, skill: Skill):
        """Save skill to skills directory."""
        category = skill.tags[0] if skill.tags else "general"
        category_dir = self.skills_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)

        skill_file = category_dir / f"{skill.name}.md"
        skill_file.write_text(skill.to_markdown())

    def load_skill(self, name: str) -> Skill | None:
        """Load a skill by name."""
        for skill_file in self.skills_dir.rglob("*.md"):
            skill = Skill.from_markdown(skill_file.read_text())
            if skill.name == name:
                return skill
        return None

    def revise_skill(self, skill: Skill, new_content: str, reason: str):
        """Create a new version of an existing skill."""
        version_parts = skill.version.split(".")
        new_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}"

        revised = Skill(
            name=skill.name,
            version=new_version,
            tags=skill.tags,
            triggers=skill.triggers,
            content=new_content,
            created=skill.created,
            updated=datetime.now().strftime("%Y-%m-%d"),
            revision_reason=reason,
        )

        self.save_skill(revised)

    def consider_skill_extension(self, task_id: str, outcome: dict):
        """Consider extending a skill based on successful task execution."""
        # TODO: Implement skill extension logic
        pass

    def consider_skill_fix(self, task_id: str, outcome: dict):
        """Consider fixing a skill based on failed task execution."""
        # TODO: Implement skill fix logic
        pass
