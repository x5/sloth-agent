"""Function calling dispatch loop — runs tool calls for an agent turn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable, Union

from sloth_agent.core.tools.decorators import ToolContext, ToolPool


@dataclass
class ToolCallEvent:
    tool_name: str
    arguments: dict
    agent_id: str = ""


@dataclass
class ToolResultEvent:
    tool_name: str
    success: bool
    output: str
    error_code: str | None = None


@dataclass
class TextTokenEvent:
    token: str


@dataclass
class DoneEvent:
    """Emitted when the loop terminates (no more tool calls or max iterations)."""


ToolLoopEvent = Union[ToolCallEvent, ToolResultEvent, TextTokenEvent, DoneEvent]

# llm_call signature: (messages, tools_schema) -> dict with {"content": str, "tool_calls": [...]}
LlmCallFn = Callable[[list[dict], list[dict]], Any]


def _tools_to_openai_schema(tool_names: list[str], pool: ToolPool) -> list[dict]:
    """Build OpenAI-format tools array from names and pool."""
    schemas = []
    for name in tool_names:
        td = pool.get_tool(name)
        if td:
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": td.name,
                        "description": td.description,
                        "parameters": td.parameters_schema,
                    },
                }
            )
    return schemas


async def run_tool_loop(
    messages: list[dict],
    effective_tools: list[str],
    tool_pool: ToolPool,
    ctx: ToolContext,
    llm_call: LlmCallFn,
    max_iterations: int = 3,
) -> AsyncIterator[ToolLoopEvent]:
    """Execute function calling loop.

    Args:
        messages: Chat history (role/content dicts)
        effective_tools: Whitelist of tool names for this agent
        tool_pool: Tool registry
        ctx: Tool execution context (project root, session, agent)
        llm_call: Async callable injected by Desktop/CLI
        max_iterations: Max tool-call rounds before forced done
    """
    tools_schema = _tools_to_openai_schema(effective_tools, tool_pool)

    for _iteration in range(max_iterations):
        response = await llm_call(messages, tools_schema)

        content = response.get("content", "") or ""
        if content:
            yield TextTokenEvent(token=content)

        tool_calls = response.get("tool_calls") or []
        if not tool_calls:
            yield DoneEvent()
            return

        for tc in tool_calls:
            name = tc.get("name", tc.get("function", {}).get("name", ""))
            args = tc.get("arguments", tc.get("function", {}).get("arguments", {}))

            if isinstance(args, str):
                import json

                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    args = {}

            # Whitelist check
            if name not in effective_tools:
                yield ToolResultEvent(
                    tool_name=name,
                    success=False,
                    output=f"Tool '{name}' is not allowed for this agent.",
                    error_code="TOOL_NOT_ALLOWED",
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", name),
                        "content": f"Error: Tool '{name}' not allowed.",
                    }
                )
                continue

            tool_def = tool_pool.get_tool(name)
            if not tool_def:
                yield ToolResultEvent(
                    tool_name=name,
                    success=False,
                    output=f"Tool '{name}' not registered.",
                    error_code="TOOL_NOT_FOUND",
                )
                continue

            yield ToolCallEvent(
                tool_name=name, arguments=args, agent_id=ctx.agent_id
            )

            # Execute tool
            try:
                if tool_def.is_async:
                    result = await tool_def.fn(**args, ctx=ctx)
                else:
                    result = tool_def.fn(**args, ctx=ctx)
            except Exception as e:
                yield ToolResultEvent(
                    tool_name=name,
                    success=False,
                    output=str(e),
                    error_code="TOOL_EXECUTION_ERROR",
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.get("id", name),
                        "content": f"Error: {e}",
                    }
                )
                continue

            yield ToolResultEvent(tool_name=name, success=True, output=str(result))

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", name),
                    "content": str(result),
                }
            )

    yield DoneEvent()
