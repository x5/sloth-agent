"""
Naming Convention for Sloth Agent Documents

Document Naming Format:
    YYYYMMDD-event-description-type.md

Where:
    - YYYYMMDD: Date in 8-digit format (e.g., 20260415)
    - event-description: Brief description of the event/topic (kebab-case)
    - type: One of:
        - design-spec (设计规格)
        - implementation-plan (实现计划)
        - user-guide (用户手册)
        - report (工作报告)

Examples:
    - 20260415-tools-design-spec.md
    - 20260415-tools-implementation-plan.md
    - 20260415-card-game-design-spec.md
    - 20260416-wuxing-app-implementation-plan.md

Directory Structure:
    docs/
        specs/           # Design specifications
            YYYYMMDD-*-design-spec.md
        plans/           # Implementation plans
            YYYYMMDD-*-implementation-plan.md
        reports/         # Work reports
            YYYYMMDD-*-report.md
"""

from datetime import datetime
from pathlib import Path
import re


class DocumentNaming:
    """Handles document naming conventions for Sloth Agent."""

    # Document types
    TYPE_DESIGN_SPEC = "design-spec"
    TYPE_IMPLEMENTATION_PLAN = "implementation-plan"
    TYPE_REPORT = "report"
    TYPE_USER_GUIDE = "user-guide"

    # Valid types
    VALID_TYPES = {
        TYPE_DESIGN_SPEC,
        TYPE_IMPLEMENTATION_PLAN,
        TYPE_REPORT,
        TYPE_USER_GUIDE,
    }

    # Pattern: YYYYMMDD-description-type.md
    PATTERN = re.compile(r"^(\d{8})-([a-z0-9]+(?:-[a-z0-9]+)*)-(design-spec|implementation-plan|report|user-guide)\.md$")

    @staticmethod
    def today() -> str:
        """Return today's date in YYYYMMDD format."""
        return datetime.now().strftime("%Y%m%d")

    @staticmethod
    def format_date(dt: datetime) -> str:
        """Format a datetime to YYYYMMDD."""
        return dt.strftime("%Y%m%d")

    @classmethod
    def make_filename(cls, date: str | datetime, description: str, doc_type: str) -> str:
        """
        Create a properly formatted document filename.

        Args:
            date: Date in YYYYMMDD format or datetime object
            description: Brief description (kebab-case)
            doc_type: One of the valid types

        Returns:
            Formatted filename like "20260415-tools-design-spec.md"

        Raises:
            ValueError: If doc_type is not valid
        """
        if doc_type not in cls.VALID_TYPES:
            raise ValueError(f"Invalid document type: {doc_type}. Must be one of {cls.VALID_TYPES}")

        if isinstance(date, datetime):
            date = cls.format_date(date)
        elif not re.match(r"^\d{8}$", date):
            raise ValueError(f"Date must be YYYYMMDD format, got: {date}")

        # Clean description (replace spaces with hyphens, lowercase)
        description = description.lower().replace(" ", "-").replace("_", "-")

        return f"{date}-{description}-{doc_type}.md"

    @classmethod
    def parse_filename(cls, filename: str) -> dict | None:
        """
        Parse a filename to extract components.

        Args:
            filename: Filename like "20260415-tools-design-spec.md"

        Returns:
            Dict with keys: date, description, type, or None if invalid
        """
        match = cls.PATTERN.match(filename)
        if not match:
            return None

        return {
            "date": match.group(1),
            "description": match.group(2),
            "type": match.group(3),
        }

    @classmethod
    def is_valid(cls, filename: str) -> bool:
        """Check if a filename follows the naming convention."""
        return cls.PATTERN.match(filename) is not None

    @classmethod
    def get_latest(cls, directory: Path, doc_type: str | None = None) -> Path | None:
        """
        Get the latest document from a directory.

        Args:
            directory: Path to the directory
            doc_type: Optional filter by type

        Returns:
            Path to the latest document, or None if none found
        """
        if not directory.exists():
            return None

        files = []
        for f in directory.glob("*.md"):
            parsed = cls.parse_filename(f.name)
            if parsed:
                if doc_type is None or parsed["type"] == doc_type:
                    files.append((f, parsed["date"]))

        if not files:
            return None

        # Sort by date descending
        files.sort(key=lambda x: x[1], reverse=True)
        return files[0][0]


# Convenience functions
def today_filename(description: str, doc_type: str) -> str:
    """Create a filename with today's date."""
    return DocumentNaming.make_filename(DocumentNaming.today(), description, doc_type)
