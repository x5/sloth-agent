"""Tests for SkillRegistry."""

import pytest
from pathlib import Path

from sloth_agent.memory.skill_registry import SkillRegistry


def _write_skill_md(path: Path, name: str, description: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"""---
name: {name}
source: builtin
trigger: manual
version: 1.0.0
description: {description}
---

# {name}

{description} content.
""")


class TestSkillRegistry:
    def test_loads_builtin_skills(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "TDD cycle")
        _write_skill_md(tmp_path / "debug/SKILL.md", "debugging", "Debugging")
        registry = SkillRegistry(builtin_dir=tmp_path)
        skills = registry.get_all()
        assert len(skills) == 2

    def test_get_by_id(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "TDD cycle")
        registry = SkillRegistry(builtin_dir=tmp_path)
        skill = registry.get("tdd")
        assert skill is not None
        assert skill.id == "tdd"

    def test_get_unknown_returns_none(self, tmp_path: Path):
        registry = SkillRegistry(builtin_dir=tmp_path)
        assert registry.get("nonexistent") is None

    def test_enable_disable(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "TDD cycle")
        registry = SkillRegistry(builtin_dir=tmp_path)
        assert registry.is_enabled("tdd")
        registry.disable("tdd")
        assert not registry.is_enabled("tdd")
        assert registry.get("tdd") is None  # Disabled
        registry.enable("tdd")
        assert registry.is_enabled("tdd")
        assert registry.get("tdd") is not None

    def test_disable_excludes_from_get_all(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "TDD")
        _write_skill_md(tmp_path / "debug/SKILL.md", "debugging", "Debugging")
        registry = SkillRegistry(builtin_dir=tmp_path)
        assert len(registry.get_all()) == 2
        registry.disable("tdd")
        assert len(registry.get_all()) == 1

    def test_list_all_shows_status(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "TDD cycle")
        registry = SkillRegistry(builtin_dir=tmp_path)
        skills = registry.list_all()
        assert len(skills) == 1
        sid, desc, enabled = skills[0]
        assert sid == "tdd"
        assert enabled is True

    def test_search_by_router(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "Test driven development")
        _write_skill_md(tmp_path / "debug/SKILL.md", "debugging", "Find root cause")
        registry = SkillRegistry(builtin_dir=tmp_path)
        results = registry.search("test")
        assert len(results) >= 1

    def test_match_skill(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "Test driven development")
        registry = SkillRegistry(builtin_dir=tmp_path)
        skill = registry.match_skill("tdd")
        assert skill is not None
        assert skill.id == "tdd"

    def test_match_skill_no_match(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "Test driven development")
        registry = SkillRegistry(builtin_dir=tmp_path)
        skill = registry.match_skill("completely unrelated xyz")
        assert skill is None

    def test_empty_directory(self, tmp_path: Path):
        registry = SkillRegistry(builtin_dir=tmp_path)
        assert registry.get_all() == []

    def test_rebuild_router_after_enable_disable(self, tmp_path: Path):
        _write_skill_md(tmp_path / "tdd/SKILL.md", "tdd", "Test driven development")
        _write_skill_md(tmp_path / "debug/SKILL.md", "debugging", "Debug bugs")
        registry = SkillRegistry(builtin_dir=tmp_path)
        # Match "test" should find tdd
        assert registry.match_skill("test") is not None
        # Disable tdd
        registry.disable("tdd")
        # Now "test" should not find it
        assert registry.match_skill("test") is None
