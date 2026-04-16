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
    - 20260416-02-tools-invocation-spec.md
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
            Formatted filename like "20260416-02-tools-invocation-spec.md"

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
            filename: Filename like "20260416-02-tools-invocation-spec.md"

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


class DocumentEnforcer:
    """
    Enforces document naming and directory structure conventions.

    Used during sloth init and workflow execution to ensure
    projects maintain a consistent,规范的文档结构.
    """

    # Required directory structure for docs/
    REQUIRED_DOCS_SUBDIRS = {
        "specs",
        "plans",
        "reports",
    }

    # Required project directories (when using Sloth Agent)
    REQUIRED_PROJECT_DIRS = {
        ".sloth",
        "docs/specs",
        "docs/plans",
        "docs/reports",
        "src",
        "tests",
    }

    # Optional directories based on project type
    OPTIONAL_DIRS = {
        "scripts",
        "configs",
        "assets",
    }

    @classmethod
    def validate_project_structure(cls, project_path: Path) -> tuple[bool, list[str]]:
        """
        Validate that a project has the required directory structure.

        Args:
            project_path: Path to the project root

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        for dir_path in cls.REQUIRED_PROJECT_DIRS:
            full_path = project_path / dir_path
            if not full_path.exists():
                errors.append(f"Missing required directory: {dir_path}")
            elif not full_path.is_dir():
                errors.append(f"Expected directory but found file: {dir_path}")

        return len(errors) == 0, errors

    @classmethod
    def validate_docs_structure(cls, project_path: Path) -> tuple[bool, list[str]]:
        """
        Validate the docs/ directory structure.

        Args:
            project_path: Path to the project root

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        docs_path = project_path / "docs"

        if not docs_path.exists():
            return False, ["docs/ directory does not exist"]

        for subdir in cls.REQUIRED_DOCS_SUBDIRS:
            subdir_path = docs_path / subdir
            if not subdir_path.exists():
                errors.append(f"Missing docs/ subdirectory: {subdir}")

        return len(errors) == 0, errors

    @classmethod
    def validate_document_path(cls, doc_path: Path) -> tuple[bool, str | None]:
        """
        Validate that a document path follows naming and location conventions.

        Args:
            doc_path: Path to the document

        Returns:
            (is_valid, error_message)
        """
        if not doc_path.exists():
            return False, f"Document does not exist: {doc_path}"

        if not doc_path.is_file():
            return False, f"Expected file but found directory: {doc_path}"

        filename = doc_path.name

        # Check naming convention
        if not DocumentNaming.is_valid(filename):
            return False, (
                f"Invalid document name: {filename}\n"
                f"Expected format: YYYYMMDD-description-type.md\n"
                f"Examples:\n"
                f"  20260416-02-tools-invocation-spec.md\n"
                f"  20260415-tools-implementation-plan.md\n"
                f"  20260415-daily-report.md"
            )

        # Check it's in the correct subdirectory
        doc_type = DocumentNaming.parse_filename(filename)["type"]
        expected_subdir = {
            "design-spec": "specs",
            "implementation-plan": "plans",
            "report": "reports",
            "user-guide": "guides",
        }.get(doc_type)

        if expected_subdir:
            actual_parent = doc_path.parent.name
            if actual_parent != expected_subdir:
                return False, (
                    f"Document in wrong directory: {actual_parent}/\n"
                    f"Expected: {expected_subdir}/\n"
                    f"Document type '{doc_type}' must be in {expected_subdir}/"
                )

        return True, None

    @classmethod
    def create_project_structure(cls, project_path: Path, project_type: str = "python") -> None:
        """
        Create the required project directory structure.

        Args:
            project_path: Path to the project root
            project_type: One of "python", "rust", "node", "go"
        """
        # Create all required directories
        for dir_path in cls.REQUIRED_PROJECT_DIRS:
            (project_path / dir_path).mkdir(parents=True, exist_ok=True)

        # Create optional directories
        for dir_path in cls.OPTIONAL_DIRS:
            (project_path / dir_path).mkdir(parents=True, exist_ok=True)

        # Create docs README to guide users
        docs_readme = project_path / "docs" / "README.md"
        if not docs_readme.exists():
            docs_readme.write_text(
                "# Project Documentation\n"
                "\n"
                "This directory follows Sloth Agent naming conventions:\n"
                "\n"
                "## Structure\n"
                "- `specs/` - Design specifications (YYYYMMDD-*-design-spec.md)\n"
                "- `plans/` - Implementation plans (YYYYMMDD-*-implementation-plan.md)\n"
                "- `reports/` - Work reports (YYYYMMDD-*-report.md)\n"
                "\n"
                "## Naming Convention\n"
                "Format: YYYYMMDD-event-description-type.md\n"
                "\n"
                "Example: 20260416-02-tools-invocation-spec.md\n"
            )

        # Create type-specific files
        if project_type == "python":
            cls._create_python_structure(project_path)
        elif project_type == "rust":
            cls._create_rust_structure(project_path)
        elif project_type == "node":
            cls._create_node_structure(project_path)

    @classmethod
    def _create_python_structure(cls, project_path: Path) -> None:
        """Create Python project specific files."""
        if not (project_path / "pyproject.toml").exists():
            project_name = project_path.name
            (project_path / "pyproject.toml").write_text(
                f"[project]\n"
                f"name = \"{project_name}\"\n"
                f"version = \"0.1.0\"\n"
                f"description = \"Project description\"\n"
                f"requires-python = \">=3.10\"\n"
                f"\n"
                f"[tool.pytest.ini_options]\n"
                f"testpaths = [\"tests\"]\n"
            )

        # Create src directory with __init__.py
        src_init = project_path / "src" / "__init__.py"
        src_init.parent.mkdir(parents=True, exist_ok=True)
        if not src_init.exists():
            src_init.write_text("")

    @classmethod
    def _create_rust_structure(cls, project_path: Path) -> None:
        """Create Rust project specific files."""
        if not (project_path / "Cargo.toml").exists():
            project_name = project_path.name.replace("-", "_")
            (project_path / "Cargo.toml").write_text(
                f"[package]\n"
                f"name = \"{project_name}\"\n"
                f"version = \"0.1.0\"\n"
                f"edition = \"2021\"\n"
            )

    @classmethod
    def _create_node_structure(cls, project_path: Path) -> None:
        """Create Node.js project specific files."""
        if not (project_path / "package.json").exists():
            project_name = project_path.name
            (project_path / "package.json").write_text(
                f'{{\n'
                f'  "name": "{project_name}",\n'
                f'  "version": "0.1.0",\n'
                f'  "description": "Project description"\n'
                f'}}\n'
            )
