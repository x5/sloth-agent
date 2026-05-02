"""SkillValidator — validate SKILL.md format and content."""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

REQUIRED_FIELDS = {"name", "trigger", "version", "description"}
PLACEHOLDER_PATTERNS = ["TBD", "TODO", "未完成", "待完成", "待补充"]


class ValidationResult(NamedTuple):
    """Result of validating a single SKILL.md file."""

    valid: bool
    path: str
    errors: list[str]
    warnings: list[str]


class SkillValidator:
    """Validate SKILL.md files for required fields, placeholders, and duplicates."""

    def __init__(self):
        self._known_descriptions: list[tuple[str, str]] = []

    def register_known(self, skill_id: str, description: str) -> None:
        """Register a known skill for duplicate detection."""
        self._known_descriptions.append((skill_id, description))

    def validate_file(self, path: Path) -> ValidationResult:
        """Validate a single SKILL.md file."""
        errors: list[str] = []
        warnings: list[str] = []

        if not path.exists():
            return ValidationResult(
                valid=False, path=str(path),
                errors=[f"File not found: {path}"], warnings=[],
            )

        text = path.read_text(encoding="utf-8")

        # Parse frontmatter
        fields = self._parse_frontmatter(text)
        if fields is None:
            return ValidationResult(
                valid=False, path=str(path),
                errors=["Missing YAML frontmatter (--- ... ---)"], warnings=[],
            )

        # Check required fields
        missing = REQUIRED_FIELDS - set(fields.keys())
        if missing:
            errors.append(f"Missing required fields: {', '.join(sorted(missing))}")

        # Check for placeholders in content
        body = text.split("---", 2)[-1].strip() if text.count("---") >= 2 else ""
        for placeholder in PLACEHOLDER_PATTERNS:
            if placeholder in body or placeholder in str(fields.values()):
                errors.append(
                    f"Contains placeholder '{placeholder}' — "
                    f"skill must be complete before registration"
                )

        # Check duplicate description
        desc = fields.get("description", "")
        if desc:
            dup = self._check_duplicate(desc)
            if dup:
                warnings.append(
                    f"Description similar to existing skill '{dup}' "
                    f"(consider merging or differentiating)"
                )

        # Validate trigger value
        trigger = fields.get("trigger", "")
        valid_triggers = {"auto", "manual", "auto+manual", "error-driven"}
        if trigger and trigger not in valid_triggers:
            errors.append(
                f"Invalid trigger '{trigger}'. Must be one of: {', '.join(sorted(valid_triggers))}"
            )

        # Validate version format
        version = fields.get("version", "")
        if version and not version.replace(".", "").isdigit():
            errors.append(f"Version '{version}' should be numeric (e.g., 1.0.0)")

        return ValidationResult(
            valid=len(errors) == 0, path=str(path),
            errors=errors, warnings=warnings,
        )

    def validate_directory(self, dir_path: Path) -> list[ValidationResult]:
        """Validate all SKILL.md files in a directory tree."""
        results = []
        if not dir_path.is_dir():
            return [ValidationResult(
                valid=False, path=str(dir_path),
                errors=[f"Not a directory: {dir_path}"], warnings=[],
            )]
        for skill_file in dir_path.rglob("SKILL.md"):
            results.append(self.validate_file(skill_file))
        return results

    def _parse_frontmatter(self, text: str) -> dict | None:
        """Extract YAML frontmatter from SKILL.md content."""
        import re
        m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not m:
            return None
        try:
            import yaml
            return yaml.safe_load(m.group(1)) or {}
        except Exception:
            return None

    def _check_duplicate(self, description: str, threshold: float = 0.8) -> str | None:
        """Check if description is too similar to any known skill."""
        desc_lower = description.lower().strip()
        for skill_id, known_desc in self._known_descriptions:
            known_lower = known_desc.lower().strip()
            if not desc_lower or not known_lower:
                continue
            similarity = self._jaccard_similarity(desc_lower, known_lower)
            if similarity >= threshold:
                return skill_id
        return None

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        """Compute Jaccard similarity between two strings (word-level)."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a and not words_b:
            return 1.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0
