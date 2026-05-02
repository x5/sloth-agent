"""Tests for SkillValidator."""

import pytest
from pathlib import Path

from sloth_agent.memory.skill_validator import SkillValidator, ValidationResult


def _write_skill_md(path: Path, frontmatter: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n{body}", encoding="utf-8")


class TestSkillValidator:
    def test_valid_skill_passes(self, tmp_path: Path):
        skill_file = tmp_path / "test/SKILL.md"
        _write_skill_md(
            skill_file,
            "name: test-skill\ntrigger: manual\nversion: 1.0.0\ndescription: A test skill\n",
            "# Test Skill\n\nThis is the skill content.",
        )
        validator = SkillValidator()
        result = validator.validate_file(skill_file)
        assert result.valid is True
        assert not result.errors

    def test_missing_frontmatter_fails(self, tmp_path: Path):
        skill_file = tmp_path / "bad/SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text("# No frontmatter\nJust content.", encoding="utf-8")
        validator = SkillValidator()
        result = validator.validate_file(skill_file)
        assert result.valid is False
        assert "Missing YAML frontmatter" in result.errors[0]

    def test_missing_required_fields_fails(self, tmp_path: Path):
        skill_file = tmp_path / "bad/SKILL.md"
        _write_skill_md(
            skill_file,
            "name: test-skill\ntrigger: manual\n",  # missing version, description
            "# Content",
        )
        validator = SkillValidator()
        result = validator.validate_file(skill_file)
        assert result.valid is False
        assert "Missing required fields" in result.errors[0]

    def test_placeholder_detection(self, tmp_path: Path):
        skill_file = tmp_path / "bad/SKILL.md"
        _write_skill_md(
            skill_file,
            "name: test-skill\ntrigger: manual\nversion: 1.0.0\ndescription: A skill\n",
            "TODO: implement this later",
        )
        validator = SkillValidator()
        result = validator.validate_file(skill_file)
        assert result.valid is False
        assert any("TODO" in e for e in result.errors)

    def test_chinese_placeholder_detection(self, tmp_path: Path):
        skill_file = tmp_path / "bad/SKILL.md"
        _write_skill_md(
            skill_file,
            "name: test-skill\ntrigger: manual\nversion: 1.0.0\ndescription: A skill\n",
            "\u5f85\u8865\u5145",
        )
        validator = SkillValidator()
        result = validator.validate_file(skill_file)
        assert result.valid is False
        assert any("placeholder" in e.lower() for e in result.errors)

    def test_invalid_trigger_fails(self, tmp_path: Path):
        skill_file = tmp_path / "bad/SKILL.md"
        _write_skill_md(
            skill_file,
            "name: test\ntrigger: always\nversion: 1.0.0\ndescription: test\n",
            "Content",
        )
        validator = SkillValidator()
        result = validator.validate_file(skill_file)
        assert result.valid is False
        assert "Invalid trigger" in result.errors[0]

    def test_bad_version_format_fails(self, tmp_path: Path):
        skill_file = tmp_path / "bad/SKILL.md"
        _write_skill_md(
            skill_file,
            "name: test\ntrigger: manual\nversion: abc\ndescription: test\n",
            "Content",
        )
        validator = SkillValidator()
        result = validator.validate_file(skill_file)
        assert result.valid is False
        assert "Version" in result.errors[0]

    def test_file_not_found(self):
        validator = SkillValidator()
        result = validator.validate_file(Path("/nonexistent/SKILL.md"))
        assert result.valid is False
        assert "not found" in result.errors[0]

    def test_duplicate_description_warning(self, tmp_path: Path):
        skill_a = tmp_path / "a/SKILL.md"
        _write_skill_md(
            skill_a,
            "name: skill-a\ntrigger: manual\nversion: 1.0.0\ndescription: Test driven development\n",
            "Content A",
        )
        skill_b = tmp_path / "b/SKILL.md"
        _write_skill_md(
            skill_b,
            "name: skill-b\ntrigger: manual\nversion: 1.0.0\ndescription: Write code without tests\n",
            "Content B",
        )
        validator = SkillValidator()
        # Register skill-a
        validator.register_known("skill-a", "Write code without tests")
        result = validator.validate_file(skill_b)
        assert result.valid is True  # Warning, not error
        assert "similar" in result.warnings[0].lower()

    def test_validate_directory(self, tmp_path: Path):
        for name in ["tdd", "debugging"]:
            f = tmp_path / f"{name}/SKILL.md"
            _write_skill_md(
                f,
                f"name: {name}\ntrigger: manual\nversion: 1.0.0\ndescription: {name} skill\n",
                f"# {name}",
            )
        validator = SkillValidator()
        results = validator.validate_directory(tmp_path)
        assert len(results) == 2
        assert all(r.valid for r in results)

    def test_validate_non_directory(self):
        validator = SkillValidator()
        results = validator.validate_directory(Path("/nonexistent"))
        assert len(results) == 1
        assert results[0].valid is False
