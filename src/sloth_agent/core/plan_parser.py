"""Parse markdown plan files into structured task lists (spec §5.1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PlanTask:
    """A single task parsed from a plan file."""
    id: int
    title: str
    description: str = ""
    file_path: str | None = None
    code: str | None = None
    done: bool = False


class PlanParser:
    """Parse markdown plan files into structured task lists.

    Recognises:
    - `#` / `##` headers as task titles
    - Body text under headers as description
    - Fenced code blocks with optional file hints
      (e.g. ```python path/to/file.py)
    """

    @staticmethod
    def parse(plan_path: str | Path) -> list[PlanTask]:
        text = Path(plan_path).read_text(encoding="utf-8")
        return PlanParser._parse_text(text)

    @staticmethod
    def _parse_text(text: str) -> list[PlanTask]:
        lines = text.splitlines()

        # Phase 1: split into sections by header
        sections: list[tuple[str, list[str]]] = []  # (title, body_lines)
        current_title: str | None = None
        current_body: list[str] = []

        for line in lines:
            header_match = re.match(r"^(#{1,3})\s+(.+)$", line)
            if header_match:
                if current_title is not None:
                    sections.append((current_title, current_body))
                current_title = header_match.group(2).strip()
                current_body = []
            else:
                current_body.append(line)

        if current_title is not None:
            sections.append((current_title, current_body))

        # Phase 2: extract tasks from sections
        tasks: list[PlanTask] = []
        task_id = 1

        for title, body_lines in sections:
            # Try to find file hints in code blocks
            file_path = None
            code_parts: list[str] = []
            desc_lines: list[str] = []

            in_code_block = False
            fence_lang = ""
            code_buf: list[str] = []

            for line in body_lines:
                fence_match = re.match(r"^```(\w+)?\s*(.*)$", line)
                if fence_match:
                    if in_code_block:
                        # Close code block
                        code_text = "\n".join(code_buf)
                        code_parts.append(code_text)
                        # Check if fence had a file path
                        if fence_lang is None and fence_match.group(2).strip():
                            file_path = fence_match.group(2).strip()
                        elif file_path is None:
                            # Try to infer from content
                            file_path = None
                        in_code_block = False
                        fence_lang = None
                        code_buf = []
                    else:
                        # Open code block
                        in_code_block = True
                        fence_lang = fence_match.group(1)
                        hint = fence_match.group(2).strip()
                        if hint:
                            file_path = hint
                elif in_code_block:
                    code_buf.append(line)
                else:
                    desc_lines.append(line)

            description = "\n".join(l for l in desc_lines if l.strip()).strip()
            code = "\n".join(code_parts) if code_parts else None

            task_title = title.strip()
            if not task_title:
                continue

            tasks.append(PlanTask(
                id=task_id,
                title=task_title,
                description=description,
                file_path=file_path,
                code=code,
            ))
            task_id += 1

        return tasks

    @staticmethod
    def parse_text(text: str) -> list[PlanTask]:
        """Parse plan from raw text (for testing)."""
        return PlanParser._parse_text(text)
