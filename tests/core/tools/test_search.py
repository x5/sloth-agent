"""Unit tests for search tools (glob, grep)."""

from pathlib import Path

import pytest

from sloth_agent.core.tools.builtin.search import GlobTool, GrepTool


class TestGlobTool:
    def test_find_python_files(self, tmp_path):
        (tmp_path / "a.py").write_text("# a")
        (tmp_path / "b.py").write_text("# b")
        (tmp_path / "c.txt").write_text("text")
        tool = GlobTool()
        results = tool.execute(pattern="*.py", root=str(tmp_path))
        assert len(results) == 2

    def test_no_matches(self, tmp_path):
        tool = GlobTool()
        results = tool.execute(pattern="*.xyz", root=str(tmp_path))
        assert results == []

    def test_recursive_pattern(self, tmp_path):
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "deep.txt").write_text("deep")
        tool = GlobTool()
        results = tool.execute(pattern="**/*.txt", root=str(tmp_path))
        assert len(results) == 1

    def test_not_a_directory(self):
        tool = GlobTool()
        with pytest.raises(NotADirectoryError):
            tool.execute(pattern="*.py", root="/nonexistent/dir")

    def test_metadata(self):
        tool = GlobTool()
        assert tool.category.value == "search"
        assert tool.risk_level == 1


class TestGrepTool:
    def test_find_pattern(self, tmp_path):
        f = tmp_path / "code.py"
        f.write_text("def hello():\n    pass\ndef world():\n    pass")
        tool = GrepTool()
        results = tool.execute(pattern=r"^def ", root=str(tmp_path))
        assert len(results) == 2

    def test_file_filter(self, tmp_path):
        (tmp_path / "a.py").write_text("def foo(): pass")
        (tmp_path / "b.txt").write_text("def bar(): pass")
        tool = GrepTool()
        results = tool.execute(
            pattern=r"def ", root=str(tmp_path), file_pattern="*.py"
        )
        assert len(results) == 1

    def test_no_matches(self, tmp_path):
        (tmp_path / "empty.py").write_text("no functions here")
        tool = GrepTool()
        results = tool.execute(pattern=r"^class ", root=str(tmp_path))
        assert results == []

    def test_max_results(self, tmp_path):
        for i in range(10):
            (tmp_path / f"file{i}.py").write_text("def foo(): pass")
        tool = GrepTool()
        results = tool.execute(
            pattern=r"def foo", root=str(tmp_path), max_results=3
        )
        assert len(results) == 3

    def test_not_a_directory(self):
        tool = GrepTool()
        with pytest.raises(NotADirectoryError):
            tool.execute(pattern="x", root="/nonexistent/dir")

    def test_metadata(self):
        tool = GrepTool()
        assert tool.category.value == "search"
        assert tool.risk_level == 1
