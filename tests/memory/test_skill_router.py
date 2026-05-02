"""Tests for SkillRouter."""

import pytest

from sloth_agent.memory.skill_router import SkillRouter
from sloth_agent.memory.skills import Skill


def _make_skill(skill_id: str, name: str, description: str) -> Skill:
    return Skill(
        id=skill_id, name=name, source="builtin",
        trigger="manual", description=description, content="# Content",
    )


class TestSkillRouter:
    def test_exact_match_by_id(self):
        skills = [_make_skill("test-driven-development", "Test Driven Development", "TDD cycle")]
        router = SkillRouter(skills)
        match = router.match("test-driven-development")
        assert match is not None
        assert match.confidence == 1.0
        assert match.match_type == "exact"

    def test_exact_match_by_name(self):
        skills = [_make_skill("tdd", "TDD", "Test driven development")]
        router = SkillRouter(skills)
        match = router.match("TDD")
        assert match is not None
        assert match.confidence == 1.0

    def test_case_insensitive_match(self):
        skills = [_make_skill("debugging", "Debugging", "Systematic debugging")]
        router = SkillRouter(skills)
        match = router.match("DEBUGGING")
        assert match is not None
        assert match.confidence == 1.0

    def test_trigger_word_match(self):
        skills = [_make_skill("debugging", "Debugging", "Find the root cause")]
        router = SkillRouter(skills)
        match = router.match("I need to find the root cause")
        assert match is not None
        assert match.confidence == 0.8
        assert match.match_type == "trigger"

    def test_keyword_match(self):
        skills = [_make_skill("review", "Review", "Checklist quality gates")]
        router = SkillRouter(skills)
        # "quality" is in the description and will match
        match = router.match("I want to improve quality")
        assert match is not None
        assert match.confidence >= 0.5

    def test_no_match_returns_none(self):
        skills = [_make_skill("tdd", "TDD", "Test driven development")]
        router = SkillRouter(skills)
        match = router.match("completely unrelated nonsense")
        assert match is None

    def test_match_all_returns_sorted(self):
        skills = [
            _make_skill("tdd", "TDD", "Test driven development"),
            _make_skill("debugging", "Debugging", "Root cause analysis"),
            _make_skill("planning", "Planning", "Task decomposition"),
        ]
        router = SkillRouter(skills)
        matches = router.match_all("test")
        assert len(matches) >= 1
        # Highest confidence first
        for i in range(len(matches) - 1):
            assert matches[i].confidence >= matches[i + 1].confidence

    def test_search_by_query(self):
        skills = [
            _make_skill("tdd", "TDD", "Test driven development"),
            _make_skill("unit-test", "Unit Test", "Writing unit tests"),
        ]
        router = SkillRouter(skills)
        results = router.search("test")
        assert len(results) == 2

    def test_empty_skills_list(self):
        router = SkillRouter([])
        match = router.match("anything")
        assert match is None

    def test_match_all_respects_min_confidence(self):
        skills = [
            _make_skill("tdd", "TDD", "Test driven development"),
            _make_skill("debugging", "Debugging", "Find bugs"),
        ]
        router = SkillRouter(skills)
        # Only exact matches (1.0)
        matches = router.match_all("tdd", min_confidence=1.0)
        for m in matches:
            assert m.confidence >= 1.0

    def test_no_duplicates_in_match_all(self):
        skills = [_make_skill("tdd", "TDD", "Test driven development")]
        router = SkillRouter(skills)
        matches = router.match_all("test")
        ids = [m.skill.id for m in matches]
        assert len(ids) == len(set(ids))
