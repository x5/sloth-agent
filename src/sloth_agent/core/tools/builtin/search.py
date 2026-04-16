"""Search operations: glob, grep.

Canonical spec: docs/specs/20260416-02-tools-invocation-spec.md §10.5.1
"""

import re
from pathlib import Path

from sloth_agent.core.tools.models import ToolCategory
from sloth_agent.core.tools.tool_registry import Tool, ToolMetadata


class GlobTool(Tool):
    """Find files by glob pattern."""

    name = "glob"
    description = "Find files matching a glob pattern"
    group = "fs"
    risk_level = 1
    permission = "auto"
    category = ToolCategory.SEARCH
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=60, max_retries=0)

    def execute(self, pattern: str, root: str = ".") -> list[str]:
        root_path = Path(root)
        if not root_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")
        return [str(p) for p in root_path.glob(pattern) if p.is_file()]

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern (e.g., *.py, **/*.md)"},
                    "root": {"type": "string", "default": "."},
                },
                "required": ["pattern"],
            },
        }


class GrepTool(Tool):
    """Search file contents by regex pattern."""

    name = "grep"
    description = "Search for regex patterns in file contents"
    group = "fs"
    risk_level = 1
    permission = "auto"
    category = ToolCategory.SEARCH
    inherit_from = "Claude Code"
    metadata = ToolMetadata(timeout_seconds=120, max_retries=0)

    def execute(
        self,
        pattern: str,
        root: str = ".",
        file_pattern: str = "*",
        max_results: int = 100,
    ) -> list[dict]:
        root_path = Path(root)
        if not root_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {root}")

        results = []
        for file_path in root_path.rglob(file_pattern):
            if not file_path.is_file():
                continue
            if file_path.stat().st_size > 10_000_000:
                continue
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(pattern, line):
                        results.append(
                            {"file": str(file_path), "line": i, "content": line.strip()}
                        )
                        if len(results) >= max_results:
                            return results
            except Exception:
                pass

        return results

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Regex pattern to search for"},
                    "root": {"type": "string", "default": "."},
                    "file_pattern": {"type": "string", "default": "*", "description": "Glob pattern to filter files"},
                    "max_results": {"type": "integer", "default": 100},
                },
                "required": ["pattern"],
            },
        }
