"""Tests for skill injection into ContextWindowManager."""

from pathlib import Path

from sloth_agent.core.context_window import ContextWindowManager
from sloth_agent.memory.skills import SkillManager


def test_inject_skills(tmp_path: Path):
    # Create a minimal fixture skill dir
    (tmp_path / "s1").mkdir()
    (tmp_path / "s1" / "SKILL.md").write_text(
        "---\nname: s1\ndescription: test\ntrigger: manual\nsource: user\nversion: 1.0\n---\n\n# S1\nDo things.\n"
    )
    mgr = SkillManager([tmp_path])
    cwm = ContextWindowManager(model="gpt-4", max_tokens=8000)
    result = cwm.inject_skills(["s1"], mgr)
    assert "## Skill: s1" in result
    assert "Do things." in result
