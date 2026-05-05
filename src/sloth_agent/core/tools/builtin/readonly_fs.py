"""Read-only filesystem tools for agent use.

Import this module to auto-register all 6 tools into the global ToolPool.
"""

from __future__ import annotations

import re
from pathlib import Path

from sloth_agent.core.tools.decorators import (
    ToolContext,
    ToolSecurityError,
    resolve_safe_path,
    tool,
)

MAX_READ_LINES = 500
MAX_GREP_RESULTS = 50
MAX_GREP_REPO_RESULTS = 100
MAX_GLOB_RESULTS = 200
MAX_LS_RESULTS = 100
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".sloth"}


def _resolve(path: str, ctx: ToolContext):
    """Resolve safe path, returning error string on failure."""
    try:
        return resolve_safe_path(ctx.project_root, path)
    except ToolSecurityError as e:
        return str(e)


@tool(name="read", description="Read the full contents of a file. Returns up to 500 lines.")
def read(path: str, ctx: ToolContext) -> str:
    """Read a file's full content.

    :param path: Relative path to the file within the project
    """
    safe = _resolve(path, ctx)
    if isinstance(safe, str):
        return safe
    if not safe.is_file():
        return f"Error: File not found: {path}"
    try:
        lines = safe.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_READ_LINES:
            truncated = "\n".join(lines[:MAX_READ_LINES])
            return (
                truncated
                + f"\n\n[Truncated: {len(lines)} total lines, showing first {MAX_READ_LINES}]"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading file: {e}"


@tool(
    name="read_range",
    description="Read a specific line range from a file (1-based, inclusive).",
)
def read_range(path: str, start: int, end: int, ctx: ToolContext) -> str:
    """Read lines start through end (1-based, inclusive).

    :param path: Relative path to the file
    :param start: Starting line number (1-based)
    :param end: Ending line number (1-based, inclusive)
    """
    safe = _resolve(path, ctx)
    if isinstance(safe, str):
        return safe
    if not safe.is_file():
        return f"Error: File not found: {path}"
    try:
        lines = safe.read_text(encoding="utf-8").splitlines()
        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        return "\n".join(lines[start_idx:end_idx])
    except Exception as e:
        return f"Error reading file: {e}"


@tool(
    name="grep",
    description="Search a file for lines matching a regex pattern. Returns up to 50 results.",
)
def grep(pattern: str, path: str, ctx: ToolContext) -> str:
    """Regex search in a single file.

    :param pattern: Regex pattern to search for
    :param path: Relative path to the file
    """
    safe = _resolve(path, ctx)
    if isinstance(safe, str):
        return safe
    if not safe.is_file():
        return f"Error: File not found: {path}"
    try:
        content = safe.read_text(encoding="utf-8", errors="replace")
        results = []
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line):
                results.append(f"{i}: {line.rstrip()}")
                if len(results) >= MAX_GREP_RESULTS:
                    break
        if not results:
            return f"No matches for '{pattern}' in {path}"
        output = "\n".join(results)
        if len(results) >= MAX_GREP_RESULTS:
            output += f"\n\n[Truncated: {MAX_GREP_RESULTS} results shown]"
        return output
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="grep_repo",
    description="Search entire project for regex pattern. Excludes .git, node_modules, etc. Up to 100 results.",
)
def grep_repo(pattern: str, ctx: ToolContext) -> str:
    """Recursive regex search across the project.

    :param pattern: Regex pattern to search for
    """
    root = Path(ctx.project_root).resolve()
    results = []
    try:
        for file in root.rglob("*"):
            if any(part in EXCLUDE_DIRS for part in file.parts):
                continue
            if not file.is_file():
                continue
            try:
                content = file.read_text(encoding="utf-8", errors="replace")
                for i, line in enumerate(content.splitlines(), 1):
                    if re.search(pattern, line):
                        rel = file.relative_to(root)
                        results.append(f"{rel}:{i}: {line.rstrip()}")
                        if len(results) >= MAX_GREP_REPO_RESULTS:
                            break
            except Exception:
                pass
            if len(results) >= MAX_GREP_REPO_RESULTS:
                break
        if not results:
            return f"No matches for '{pattern}' in project"
        output = "\n".join(results)
        if len(results) >= MAX_GREP_REPO_RESULTS:
            output += f"\n\n[Truncated: {MAX_GREP_REPO_RESULTS} results shown]"
        return output
    except Exception as e:
        return f"Error: {e}"


@tool(
    name="glob",
    description="Find files matching a glob pattern. Returns up to 200 relative paths.",
)
def glob(pattern: str, ctx: ToolContext) -> str:
    """Glob pattern file matching.

    :param pattern: Glob pattern (e.g., '**/*.py', 'src/**/*.ts')
    """
    root = Path(ctx.project_root).resolve()
    matches = []
    for file in root.glob(pattern):
        if any(part in EXCLUDE_DIRS for part in file.parts):
            continue
        if file.is_file():
            rel = file.relative_to(root)
            matches.append(str(rel))
            if len(matches) >= MAX_GLOB_RESULTS:
                break
    if not matches:
        return f"No files matching '{pattern}'"
    output = "\n".join(matches)
    if len(matches) >= MAX_GLOB_RESULTS:
        output += f"\n\n[Truncated: {MAX_GLOB_RESULTS} results shown]"
    return output


@tool(
    name="ls_dir",
    description="List directory contents. Returns up to 100 entries with type and size.",
)
def ls_dir(path: str, ctx: ToolContext) -> str:
    """List directory contents.

    :param path: Relative directory path (use '.' for project root)
    """
    safe = _resolve(path, ctx)
    if isinstance(safe, str):
        return safe
    if not safe.is_dir():
        return f"Error: Not a directory: {path}"
    entries = []
    for item in sorted(safe.iterdir(), key=lambda x: (x.is_file(), x.name)):
        entry_type = "dir" if item.is_dir() else "file"
        try:
            size = item.stat().st_size if item.is_file() else 0
        except Exception:
            size = 0
        rel = item.relative_to(Path(ctx.project_root).resolve())
        entries.append(
            f"{'[DIR]' if entry_type == 'dir' else '[FILE]'} {rel} ({_fmt_size(size)})"
        )
        if len(entries) >= MAX_LS_RESULTS:
            break
    if not entries:
        return f"Directory '{path}' is empty"
    output = "\n".join(entries)
    if len(entries) >= MAX_LS_RESULTS:
        output += f"\n\n[Truncated: {MAX_LS_RESULTS} entries shown]"
    return output


def _fmt_size(size: int) -> str:
    if size >= 1_000_000:
        return f"{size / 1_000_000:.1f}MB"
    if size >= 1_000:
        return f"{size / 1_000:.1f}KB"
    return f"{size}B"
