"""@tool decorator system with global ToolPool registry.

Coexists with the class-based Tool/ToolRegistry system.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, get_type_hints


@dataclass
class ToolDef:
    """Definition of a registered tool."""

    name: str
    description: str
    parameters_schema: dict  # OpenAI-format JSON Schema
    fn: Callable  # The actual function
    is_async: bool = False


@dataclass
class ToolContext:
    """Runtime context passed to every tool execution."""

    project_root: str
    session_id: str = ""
    agent_id: str = ""


class ToolSecurityError(Exception):
    """Raised when a tool call violates path or permission constraints."""


def resolve_safe_path(project_root: str, user_path: str) -> Path:
    """Normalize user_path and ensure it is within project_root.

    Raises ToolSecurityError if path escapes the project root.
    """
    root = Path(project_root).resolve()
    target = (root / user_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise ToolSecurityError(
            f"Path '{user_path}' resolves outside project root '{root}'"
        )
    return target


class ToolPool:
    """Global singleton registry of @tool-decorated functions."""

    _instance: ToolPool | None = None

    def __init__(self):
        self._tools: dict[str, ToolDef] = {}

    @classmethod
    def get(cls) -> ToolPool:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (mainly for tests)."""
        cls._instance = None

    def register(self, tool_def: ToolDef) -> None:
        self._tools[tool_def.name] = tool_def

    def get_tool(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list(self) -> dict[str, ToolDef]:
        return dict(self._tools)

    def __getitem__(self, name: str) -> ToolDef:
        return self._tools[name]

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def _py_to_json_type(py_type: type) -> str:
    """Map Python types to JSON Schema types."""
    origin = getattr(py_type, "__origin__", None)
    if origin is not None:
        py_type = origin
    if py_type is str:
        return "string"
    if py_type is int:
        return "integer"
    if py_type is bool:
        return "boolean"
    if py_type is float:
        return "number"
    return "string"


def _extract_param_desc(fn: Callable, param_name: str) -> str:
    """Extract param description from docstring (reST :param format)."""
    if not fn.__doc__:
        return param_name
    pattern = rf":param\s+{param_name}\s*:\s*(.+?)(?:\n|$)"
    match = re.search(pattern, fn.__doc__)
    return match.group(1).strip() if match else param_name


def _infer_json_schema(fn: Callable, description: str) -> dict:
    """Generate a JSON Schema from function type hints and docstring."""
    hints = get_type_hints(fn)
    sig = inspect.signature(fn)
    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ("ctx", "tool_context"):
            continue  # ToolContext is injected at runtime, not exposed to LLM

        py_type = hints.get(param_name, str)
        json_type = _py_to_json_type(py_type)
        param_desc = _extract_param_desc(fn, param_name)

        prop: dict[str, Any] = {"type": json_type, "description": param_desc}
        if param.default is not inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(param_name)
        properties[param_name] = prop

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def tool(
    name: str | None = None,
    description: str | None = None,
):
    """Decorator that registers a function into the global ToolPool.

    Usage:
        @tool(name="read", description="Read a file")
        def read(path: str, ctx: ToolContext) -> str:
            ...
    """

    def decorator(fn: Callable) -> Callable:
        tool_name = name or fn.__name__
        tool_desc = description or (fn.__doc__ or "").split("\n")[0].strip()
        schema = _infer_json_schema(fn, tool_desc)
        is_async = inspect.iscoroutinefunction(fn)

        tool_def = ToolDef(
            name=tool_name,
            description=tool_desc,
            parameters_schema=schema,
            fn=fn,
            is_async=is_async,
        )
        ToolPool.get().register(tool_def)
        return fn

    return decorator
