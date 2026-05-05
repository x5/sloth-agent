"""Tests for 6 built-in read-only filesystem tools."""

import pytest
from sloth_agent.core.tools.decorators import ToolContext, ToolPool
from sloth_agent.core.tools.builtin import readonly_fs  # noqa: F401 — auto-registers tools


class TestReadTool:
    def test_read_normal_file(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "hello.txt").write_text("line1\nline2\nline3")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.read("hello.txt", ctx)
        assert "line1" in result
        assert "line2" in result

    def test_read_missing_file(self, tmp_path):
        ctx = ToolContext(project_root=str(tmp_path))
        result = readonly_fs.read("nope.txt", ctx)
        assert "Error" in result

    def test_read_truncation(self, tmp_path):
        root = str(tmp_path)
        lines = [f"line{i}" for i in range(600)]
        (tmp_path / "big.txt").write_text("\n".join(lines))
        ctx = ToolContext(project_root=root)
        result = readonly_fs.read("big.txt", ctx)
        assert "Truncated" in result
        assert "500" in result

    def test_read_outside_root(self, tmp_path):
        root = str(tmp_path / "sub")
        (tmp_path / "sub").mkdir()
        (tmp_path / "outside.txt").write_text("secret")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.read("../outside.txt", ctx)
        assert "outside" in result or "resolves outside" in result


class TestReadRangeTool:
    def test_valid_range(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "nums.txt").write_text("1\n2\n3\n4\n5")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.read_range("nums.txt", 2, 4, ctx)
        assert "2" in result
        assert "4" in result
        assert "1" not in result

    def test_missing_file(self, tmp_path):
        ctx = ToolContext(project_root=str(tmp_path))
        result = readonly_fs.read_range("nope.txt", 1, 10, ctx)
        assert "Error" in result


class TestGrepTool:
    def test_match_found(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "code.py").write_text("def foo():\n    pass\ndef bar():\n    pass\n")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.grep("def", "code.py", ctx)
        assert "foo" in result
        assert "bar" in result

    def test_no_match(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "empty.txt").write_text("nothing here")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.grep("xyzzy", "empty.txt", ctx)
        assert "No matches" in result

    def test_missing_file(self, tmp_path):
        ctx = ToolContext(project_root=str(tmp_path))
        result = readonly_fs.grep("x", "nope.txt", ctx)
        assert "Error" in result


class TestGrepRepoTool:
    def test_match_across_files(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "a.py").write_text("TODO: fix this")
        (tmp_path / "b.py").write_text("# no todo here")
        (tmp_path / "sub").mkdir()
        (tmp_path / "sub" / "c.py").write_text("// TODO: also here")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.grep_repo("TODO", ctx)
        assert "a.py" in result
        assert "c.py" in result
        assert "b.py" not in result

    def test_no_match(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "x.txt").write_text("nothing")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.grep_repo("XYZ_NOT_FOUND", ctx)
        assert "No matches" in result

    def test_excludes_git_dir(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("TODO")
        (tmp_path / "src.py").write_text("no match")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.grep_repo("TODO", ctx)
        assert "No matches" in result  # .git excluded


class TestGlobTool:
    def test_match_found(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "a.py").write_text("")
        (tmp_path / "b.ts").write_text("")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "c.py").write_text("")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.glob("**/*.py", ctx)
        assert "a.py" in result
        assert "c.py" in result
        assert "b.ts" not in result

    def test_no_match(self, tmp_path):
        ctx = ToolContext(project_root=str(tmp_path))
        result = readonly_fs.glob("**/*.xyz", ctx)
        assert "No files" in result

    def test_excludes_venv(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "lib.py").write_text("")
        (tmp_path / "main.py").write_text("")
        ctx = ToolContext(project_root=root)
        result = readonly_fs.glob("**/*.py", ctx)
        assert "main.py" in result
        assert ".venv" not in result


class TestLsDirTool:
    def test_nonempty(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "file.txt").write_text("hello")
        (tmp_path / "subdir").mkdir()
        ctx = ToolContext(project_root=root)
        result = readonly_fs.ls_dir(".", ctx)
        assert "file.txt" in result
        assert "subdir" in result

    def test_empty_dir(self, tmp_path):
        root = str(tmp_path)
        (tmp_path / "empty").mkdir()
        ctx = ToolContext(project_root=root)
        result = readonly_fs.ls_dir("empty", ctx)
        assert "empty" in result

    def test_missing_path(self, tmp_path):
        ctx = ToolContext(project_root=str(tmp_path))
        result = readonly_fs.ls_dir("nope", ctx)
        assert "Error" in result


class TestAutoRegistration:
    def setup_method(self):
        ToolPool.reset()

    def test_all_six_tools_registered(self):
        # Re-import triggers registration
        from importlib import reload
        reload(readonly_fs)
        pool = ToolPool.get()
        for name in ["read", "read_range", "grep", "grep_repo", "glob", "ls_dir"]:
            assert name in pool, f"Tool '{name}' not registered"
            td = pool[name]
            assert td.description
            assert callable(td.fn)
