"""Tests for run_tool_loop function calling dispatch."""

import pytest
from sloth_agent.core.brainstorm.tool_loop import (
    DoneEvent,
    TextTokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    run_tool_loop,
)
from sloth_agent.core.tools.decorators import ToolContext, ToolDef, ToolPool, tool


@pytest.fixture(autouse=True)
def reset_pool():
    ToolPool.reset()
    yield
    ToolPool.reset()


async def _make_llm_call(response):
    """Create an async llm_call that returns a fixed response."""

    async def fn(messages, tools_schema):
        return response

    return fn


def _register_dummy_tool(name="echo", description="Echo test tool"):
    @tool(name=name, description=description)
    def echo_fn(text: str, ctx: ToolContext) -> str:
        """Echo.

        :param text: Text to echo
        """
        return f"echo: {text}"

    return echo_fn


class TestRunToolLoop:
    async def test_no_tool_calls_yields_text_and_done(self):
        fn = await _make_llm_call({"content": "Hello world", "tool_calls": []})
        ctx = ToolContext(project_root=".")
        events = []
        async for event in run_tool_loop(
            messages=[{"role": "user", "content": "hi"}],
            effective_tools=[],
            tool_pool=ToolPool.get(),
            ctx=ctx,
            llm_call=fn,
        ):
            events.append(event)

        assert isinstance(events[0], TextTokenEvent)
        assert events[0].token == "Hello world"
        assert isinstance(events[1], DoneEvent)

    async def test_tool_call_executes_and_yields_events(self):
        _register_dummy_tool("echo")

        async def llm_call(messages, tools_schema):
            return {
                "content": "",
                "tool_calls": [{"name": "echo", "arguments": {"text": "hi"}}],
            }

        ctx = ToolContext(project_root=".")
        events = []
        async for event in run_tool_loop(
            messages=[{"role": "user", "content": "use echo"}],
            effective_tools=["echo"],
            tool_pool=ToolPool.get(),
            ctx=ctx,
            llm_call=llm_call,
        ):
            events.append(event)

        assert len(events) >= 3
        assert any(isinstance(e, ToolCallEvent) and e.tool_name == "echo" for e in events)
        assert any(
            isinstance(e, ToolResultEvent) and e.success and "echo: hi" in e.output
            for e in events
        )

    async def test_non_whitelist_tool_rejected(self):
        _register_dummy_tool("echo")
        calls = 0

        async def llm_call(messages, tools_schema):
            nonlocal calls
            calls += 1
            if calls > 1:
                return {"content": "", "tool_calls": []}
            return {
                "content": "",
                "tool_calls": [{"name": "echo", "arguments": {"text": "bad"}}],
            }

        ctx = ToolContext(project_root=".")
        events = []
        async for event in run_tool_loop(
            messages=[{"role": "user", "content": "use echo"}],
            effective_tools=[],  # echo not whitelisted
            tool_pool=ToolPool.get(),
            ctx=ctx,
            llm_call=llm_call,
        ):
            events.append(event)

        results = [e for e in events if isinstance(e, ToolResultEvent)]
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error_code == "TOOL_NOT_ALLOWED"

    async def test_unregistered_tool_errors(self):
        calls = 0

        async def llm_call(messages, tools_schema):
            nonlocal calls
            calls += 1
            if calls > 1:
                return {"content": "", "tool_calls": []}
            return {
                "content": "",
                "tool_calls": [{"name": "nonexistent_tool", "arguments": {}}],
            }

        ctx = ToolContext(project_root=".")
        events = []
        async for event in run_tool_loop(
            messages=[{"role": "user", "content": "use bad tool"}],
            effective_tools=["nonexistent_tool"],
            tool_pool=ToolPool.get(),
            ctx=ctx,
            llm_call=llm_call,
        ):
            events.append(event)

        results = [e for e in events if isinstance(e, ToolResultEvent)]
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error_code == "TOOL_NOT_FOUND"

    async def test_max_iterations_forces_done(self):
        _register_dummy_tool("echo")

        call_count = 0

        async def llm_call(messages, tools_schema):
            nonlocal call_count
            call_count += 1
            return {
                "content": f"Round {call_count}",
                "tool_calls": [{"name": "echo", "arguments": {"text": f"round{call_count}"}}],
            }

        ctx = ToolContext(project_root=".")
        events = []
        async for event in run_tool_loop(
            messages=[{"role": "user", "content": "loop"}],
            effective_tools=["echo"],
            tool_pool=ToolPool.get(),
            ctx=ctx,
            llm_call=llm_call,
            max_iterations=2,
        ):
            events.append(event)

        assert call_count == 2
        assert isinstance(events[-1], DoneEvent)

    async def test_tool_execution_error(self):
        @tool(name="broken", description="Always fails")
        def broken_fn(ctx: ToolContext) -> str:
            raise RuntimeError("Simulated failure")

        calls = 0

        async def llm_call(messages, tools_schema):
            nonlocal calls
            calls += 1
            if calls > 1:
                return {"content": "", "tool_calls": []}
            return {
                "content": "",
                "tool_calls": [{"name": "broken", "arguments": {}}],
            }

        ctx = ToolContext(project_root=".")
        events = []
        async for event in run_tool_loop(
            messages=[{"role": "user", "content": "break"}],
            effective_tools=["broken"],
            tool_pool=ToolPool.get(),
            ctx=ctx,
            llm_call=llm_call,
        ):
            events.append(event)

        results = [e for e in events if isinstance(e, ToolResultEvent)]
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error_code == "TOOL_EXECUTION_ERROR"

    async def test_tool_schema_generation(self):
        _register_dummy_tool("echo")

        from sloth_agent.core.brainstorm.tool_loop import _tools_to_openai_schema

        schemas = _tools_to_openai_schema(["echo"], ToolPool.get())
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        func = schemas[0]["function"]
        assert func["name"] == "echo"
        assert "text" in func["parameters"]["properties"]

    async def test_missing_tool_in_schema_skipped(self):
        from sloth_agent.core.brainstorm.tool_loop import _tools_to_openai_schema

        schemas = _tools_to_openai_schema(["missing"], ToolPool.get())
        assert len(schemas) == 0
