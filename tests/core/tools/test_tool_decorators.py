"""Tests for @tool decorator system."""

import pytest
from sloth_agent.core.tools.decorators import (
    ToolContext,
    ToolPool,
    ToolSecurityError,
    _infer_json_schema,
    resolve_safe_path,
    tool,
)
from sloth_agent.core.tools import ToolDef


class TestToolDecorator:
    def setup_method(self):
        ToolPool.reset()

    def test_register_and_retrieve(self):
        @tool(name="echo", description="Echo back input")
        def echo(text: str, ctx: ToolContext) -> str:
            """Echo text.

            :param text: The text to echo
            """
            return text

        assert "echo" in ToolPool.get()
        td = ToolPool.get()["echo"]
        assert td.name == "echo"
        assert td.description == "Echo back input"
        assert td.fn is echo
        assert td.is_async is False

    def test_name_from_function(self):
        @tool()
        def my_func(path: str, ctx: ToolContext) -> str:
            """Do something."""
            return path

        assert "my_func" in ToolPool.get()

    def test_description_from_docstring(self):
        @tool()
        def do_thing(x: str, ctx: ToolContext) -> str:
            """Perform the thing with given input."""
            return x

        td = ToolPool.get()["do_thing"]
        assert td.description == "Perform the thing with given input."

    def test_schema_respects_types(self):
        @tool(name="add", description="Add two numbers")
        def add(a: int, b: int, ctx: ToolContext) -> int:
            """Add.

            :param a: First number
            :param b: Second number
            """
            return a + b

        td = ToolPool.get()["add"]
        schema = td.parameters_schema
        assert schema["type"] == "object"
        assert "ctx" not in schema["properties"]
        assert schema["properties"]["a"]["type"] == "integer"
        assert schema["properties"]["b"]["type"] == "integer"
        assert set(schema["required"]) == {"a", "b"}

    def test_default_params_not_required(self):
        @tool()
        def search(query: str, limit: int = 10, ctx: ToolContext = ToolContext(".")) -> str:
            """Search.

            :param query: Search query
            :param limit: Max results
            """
            return query

        td = ToolPool.get()["search"]
        schema = td.parameters_schema
        assert "query" in schema["required"]
        assert "limit" not in schema["required"]
        assert schema["properties"]["limit"]["default"] == 10

    def test_tool_context_excluded_from_schema(self):
        @tool()
        def test_fn(path: str, tool_context: ToolContext) -> str:
            """Test.

            :param path: File path
            """
            return path

        td = ToolPool.get()["test_fn"]
        assert "tool_context" not in td.parameters_schema["properties"]
        assert "ctx" not in td.parameters_schema["properties"]

    def test_async_detection(self):
        @tool()
        async def async_read(path: str, ctx: ToolContext) -> str:
            """Read async."""
            return path

        td = ToolPool.get()["async_read"]
        assert td.is_async is True

    def test_schema_from_type_hints_no_docstring(self):
        @tool()
        def no_doc(x: bool, ctx: ToolContext) -> bool:
            return x

        td = ToolPool.get()["no_doc"]
        assert td.parameters_schema["properties"]["x"]["type"] == "boolean"


class TestResolveSafePath:
    def test_within_root(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "file.txt").write_text("hello")

        result = resolve_safe_path(root, "sub/file.txt")
        assert result.is_file()
        assert result.read_text() == "hello"

    def test_root_itself(self, tmp_path):
        root = str(tmp_path)
        result = resolve_safe_path(root, ".")
        assert result == tmp_path.resolve()

    def test_outside_root_raises(self, tmp_path):
        root = str(tmp_path / "subdir")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "outside.txt").write_text("bad")

        with pytest.raises(ToolSecurityError):
            resolve_safe_path(root, "../outside.txt")

    def test_absolute_path_escape(self, tmp_path):
        root = str(tmp_path / "subdir")
        (tmp_path / "subdir").mkdir()

        with pytest.raises(ToolSecurityError):
            resolve_safe_path(root, str(tmp_path / "other"))


class TestToolPoolSingleton:
    def setup_method(self):
        ToolPool.reset()

    def test_same_instance(self):
        a = ToolPool.get()
        b = ToolPool.get()
        assert a is b

    def test_reset_creates_new(self):
        a = ToolPool.get()
        ToolPool.reset()
        b = ToolPool.get()
        assert a is not b

    def test_list_returns_copy(self):
        @tool()
        def one(ctx: ToolContext) -> str:
            return "1"

        tools = ToolPool.get().list()
        assert "one" in tools
        tools.pop("one")
        assert "one" in ToolPool.get()  # original unaffected

    def test_contains(self):
        @tool()
        def exists(ctx: ToolContext) -> str:
            return "yes"

        assert "exists" in ToolPool.get()
        assert "missing" not in ToolPool.get()

    def test_get_none_for_missing(self):
        assert ToolPool.get().get_tool("nonexistent") is None
