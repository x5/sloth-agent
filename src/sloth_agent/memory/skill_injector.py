"""SkillInjector — inject matched skill content into system prompts."""

from __future__ import annotations

from dataclasses import dataclass

from sloth_agent.memory.skill_router import SkillMatch
from sloth_agent.memory.skills import Skill


@dataclass
class InjectionResult:
    """Result of skill injection."""

    injected_skills: list[tuple[Skill, float]]  # (skill, confidence)
    system_prompt_section: str
    token_count: int


class SkillInjector:
    """Inject skill content into system prompts.

    Controls token budget: each skill is capped at MAX_TOKENS_PER_SKILL.
    Multiple skills are sorted by confidence and top-N are selected.
    """

    # Approximate token budget per skill (4096 chars ≈ 4K tokens for typical text)
    MAX_TOKENS_PER_SKILL = 4096

    def __init__(self, max_skills: int = 3, max_total_tokens: int = 12000):
        self.max_skills = max_skills
        self.max_total_tokens = max_total_tokens

    def inject(
        self,
        matches: list[SkillMatch],
        existing_prompt: str = "",
    ) -> InjectionResult:
        """Select and format skills for system prompt injection.

        Args:
            matches: Skill matches from SkillRouter, sorted by confidence.
            existing_prompt: Current system prompt (for token budget tracking).

        Returns:
            InjectionResult with selected skills and formatted section.
        """
        if not matches:
            return InjectionResult(
                injected_skills=[],
                system_prompt_section="",
                token_count=0,
            )

        # Estimate existing prompt token count (rough: 4 chars ≈ 1 token)
        used_tokens = len(existing_prompt) // 4
        remaining = self.max_total_tokens - used_tokens

        selected: list[tuple[Skill, float]] = []
        sections: list[str] = []

        for match in matches[: self.max_skills]:
            skill = match.skill
            # Truncate skill content to token budget
            content = self._truncate_content(skill.content, self.MAX_TOKENS_PER_SKILL)
            token_estimate = len(content) // 4

            if token_estimate > remaining:
                break  # Budget exhausted

            selected.append((skill, match.confidence))
            sections.append(self._format_skill_section(skill, content, match.confidence))
            remaining -= token_estimate

        prompt_section = self._combine_sections(sections)
        return InjectionResult(
            injected_skills=selected,
            system_prompt_section=prompt_section,
            token_count=len(prompt_section) // 4,
        )

    @staticmethod
    def _truncate_content(content: str, max_chars: int) -> str:
        """Truncate skill content to fit within token budget."""
        if len(content) <= max_chars:
            return content
        return content[: max_chars - 50] + "\n... [truncated]"

    @staticmethod
    def _format_skill_section(
        skill: Skill, content: str, confidence: float
    ) -> str:
        """Format a single skill for system prompt."""
        return f"""--- Active Skill: {skill.name} ---
{content}
--- End Skill ---
"""

    @staticmethod
    def _combine_sections(sections: list[str]) -> str:
        """Combine multiple skill sections into one block."""
        if not sections:
            return ""
        return "\n".join(sections)
