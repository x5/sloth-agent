"""Tests for SkillInjector."""

import pytest

from sloth_agent.memory.skill_injector import SkillInjector, InjectionResult
from sloth_agent.memory.skill_router import SkillMatch
from sloth_agent.memory.skills import Skill


def _make_skill(skill_id: str, content: str) -> Skill:
    return Skill(
        id=skill_id, name=skill_id.title(), source="builtin",
        trigger="manual", description=f"{skill_id} skill",
        content=content,
    )


class TestSkillInjector:
    def test_empty_matches_returns_empty(self):
        injector = SkillInjector()
        result = injector.inject([])
        assert result.injected_skills == []
        assert result.system_prompt_section == ""
        assert result.token_count == 0

    def test_injects_single_skill(self):
        skill = _make_skill("tdd", "# TDD\nFollow RED-GREEN-REFACTOR.")
        match = SkillMatch(skill=skill, confidence=1.0, match_type="exact")
        injector = SkillInjector()
        result = injector.inject([match])
        assert len(result.injected_skills) == 1
        assert "TDD" in result.system_prompt_section

    def test_respects_max_skills_limit(self):
        skills = [_make_skill(f"skill-{i}", f"Content {i}" * 10) for i in range(5)]
        matches = [SkillMatch(s, 0.8, "trigger") for s in skills]
        injector = SkillInjector(max_skills=2)
        result = injector.inject(matches)
        assert len(result.injected_skills) <= 2

    def test_truncates_oversized_content(self):
        huge_content = "A" * 10000
        skill = _make_skill("huge", huge_content)
        match = SkillMatch(skill=skill, confidence=0.8, match_type="trigger")
        injector = SkillInjector()
        result = injector.inject([match])
        # Content should be truncated
        assert len(result.system_prompt_section) < len(huge_content)

    def test_respects_token_budget(self):
        # Existing prompt uses most of the budget
        existing = "X" * 40000  # ~10K tokens
        skills = [_make_skill(f"skill-{i}", f"Content {i}" * 100) for i in range(3)]
        matches = [SkillMatch(s, 0.8, "trigger") for s in skills]
        injector = SkillInjector(max_total_tokens=12000)
        result = injector.inject(matches, existing_prompt=existing)
        # Should not inject much due to budget
        assert result.token_count < 2000  # Rough check

    def test_combines_multiple_sections(self):
        skills = [_make_skill(f"s{i}", f"Content {i}") for i in range(3)]
        matches = [SkillMatch(s, 0.8, "trigger") for s in skills]
        injector = SkillInjector(max_skills=3)
        result = injector.inject(matches)
        assert len(result.injected_skills) == 3
        # Each section should contain the skill name
        for skill in skills:
            assert skill.name in result.system_prompt_section

    def test_format_includes_skill_name(self):
        skill = _make_skill("tdd", "# TDD")
        match = SkillMatch(skill=skill, confidence=1.0, match_type="exact")
        injector = SkillInjector()
        result = injector.inject([match])
        assert "Active Skill:" in result.system_prompt_section
        assert "End Skill" in result.system_prompt_section
