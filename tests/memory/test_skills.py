"""Tests for SkillManager (SKILL.md loading)."""

import os
from pathlib import Path

import pytest

from sloth_agent.memory.skills import Skill, SkillManager

FIXTURES = Path(os.path.join(os.path.dirname(__file__), "fixtures"))


def test_load_all_skills():
    mgr = SkillManager([FIXTURES / "superpowers", FIXTURES / "gstack"])
    skills = mgr.load_all_skills()
    assert len(skills) == 2
    ids = {s.id for s in skills}
    assert ids == {"tdd", "review"}


def test_get_skill_content():
    mgr = SkillManager([FIXTURES / "superpowers", FIXTURES / "gstack"])
    content = mgr.get_skill_content("tdd")
    assert content is not None
    assert "RED-GREEN-REFACTOR" in content


def test_skill_from_markdown():
    raw = (
        "---\n"
        "name: foo\n"
        "description: A test skill\n"
        "trigger: auto\n"
        "source: user\n"
        "version: 1.0.0\n"
        "allowed-tools: [Read]\n"
        "---\n"
        "\n"
        "# Foo Skill\n\nDo something.\n"
    )
    skill = Skill.from_markdown(raw)
    assert skill.id == "foo"
    assert skill.description == "A test skill"
    assert skill.source == "user"
    assert "Do something." in skill.content
