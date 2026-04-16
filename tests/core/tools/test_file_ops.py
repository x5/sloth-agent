"""Unit tests for file operations tools."""

from pathlib import Path

import pytest

from sloth_agent.core.tools.builtin.file_ops import (
    EditFileTool,
    ReadFileTool,
    WriteFileTool,
)


class TestReadFileTool:
    def test_read_existing_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        tool = ReadFileTool()
        result = tool.execute(path=str(f))
        assert result == "hello world"

    def test_read_missing_file(self, tmp_path):
        tool = ReadFileTool()
        with pytest.raises(FileNotFoundError):
            tool.execute(path=str(tmp_path / "missing.txt"))

    def test_metadata(self):
        tool = ReadFileTool()
        assert tool.category.value == "read"
        assert tool.risk_level == 1

    def test_schema(self):
        tool = ReadFileTool()
        schema = tool.get_schema()
        assert schema["name"] == "read_file"
        assert "path" in schema["parameters"]["properties"]


class TestWriteFileTool:
    def test_write_new_file(self, tmp_path):
        tool = WriteFileTool()
        p = tmp_path / "new.txt"
        result = tool.execute(path=str(p), content="new content")
        assert "Written" in str(result)
        assert p.read_text() == "new content"

    def test_write_creates_parent_dirs(self, tmp_path):
        tool = WriteFileTool()
        p = tmp_path / "a" / "b" / "c.txt"
        result = tool.execute(path=str(p), content="deep")
        assert "Written" in str(result)
        assert p.exists()

    def test_overwrite(self, tmp_path):
        tool = WriteFileTool()
        p = tmp_path / "overwrite.txt"
        p.write_text("old")
        tool.execute(path=str(p), content="new")
        assert p.read_text() == "new"

    def test_metadata(self):
        tool = WriteFileTool()
        assert tool.category.value == "write"
        assert tool.risk_level == 2


class TestEditFileTool:
    def test_edit_existing_file(self, tmp_path):
        f = tmp_path / "edit.txt"
        f.write_text("hello world")
        tool = EditFileTool()
        result = tool.execute(
            file_path=str(f), old_string="world", new_string="there"
        )
        assert f.read_text() == "hello there"

    def test_edit_missing_file(self):
        tool = EditFileTool()
        with pytest.raises(FileNotFoundError):
            tool.execute(file_path="/nonexistent/path.txt", old_string="a", new_string="b")

    def test_old_string_not_found(self, tmp_path):
        f = tmp_path / "edit.txt"
        f.write_text("hello world")
        tool = EditFileTool()
        with pytest.raises(ValueError, match="not found"):
            tool.execute(
                file_path=str(f), old_string="missing_string", new_string="replacement"
            )

    def test_old_string_multiple_occurrences(self, tmp_path):
        f = tmp_path / "edit.txt"
        f.write_text("foo foo foo")
        tool = EditFileTool()
        with pytest.raises(ValueError, match="appears 3 times"):
            tool.execute(file_path=str(f), old_string="foo", new_string="bar")

    def test_metadata(self):
        tool = EditFileTool()
        assert tool.category.value == "edit"
        assert tool.risk_level == 2
