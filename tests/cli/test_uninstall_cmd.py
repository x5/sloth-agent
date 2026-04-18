"""Tests for the uninstall CLI command."""

import os
import shutil
from pathlib import Path
from unittest import mock

import pytest
import typer

from sloth_agent.cli.uninstall_cmd import (
    _collect_items,
    _clean_shell_profiles,
    _find_shell_profiles,
    PATH_COMMENT,
)


class TestCollectItems:
    def test_returns_dir_when_exists(self, tmp_path):
        sloth_dir = tmp_path / ".sloth-agent"
        sloth_dir.mkdir()
        items = _collect_items(sloth_dir, full=False)
        assert str(sloth_dir) in items

    def test_empty_when_nothing_installed(self, tmp_path):
        sloth_dir = tmp_path / "nonexistent"
        with mock.patch.object(Path, "home", return_value=tmp_path):
            items = _collect_items(sloth_dir, full=False)
            assert len(items) == 0

    def test_shims_included_when_present(self, tmp_path):
        sloth_dir = tmp_path / ".sloth-agent"
        sloth_dir.mkdir()
        local_bin = tmp_path / ".local" / "bin"
        local_bin.mkdir(parents=True)
        (local_bin / "sloth").write_text("# shim")
        (local_bin / "sloth.bat").write_text("@echo off")

        with mock.patch.object(Path, "home", return_value=tmp_path):
            items = _collect_items(sloth_dir, full=False)

        assert str(local_bin / "sloth") in items
        assert str(local_bin / "sloth.bat") in items
        assert str(sloth_dir) in items


class TestCleanShellProfiles:
    def test_removes_comment_line_and_adjacent_empty_lines(self, tmp_path):
        profile = tmp_path / ".bashrc"
        profile.write_text(
            "# Some existing config\n"
            "\n"
            "# Sloth Agent: add uv / local bin to PATH\n"
            'export PATH="${HOME}/.local/bin:${PATH}"\n'
            "\n"
            "# Another section\n"
        )

        lines = [(profile, 2, "# Sloth Agent: add uv / local bin to PATH")]
        _clean_shell_profiles(lines)

        result = profile.read_text()
        assert PATH_COMMENT not in result
        assert "Another section" in result

    def test_no_op_when_no_lines(self, tmp_path):
        profile = tmp_path / ".zshrc"
        profile.write_text("some content\n")
        _clean_shell_profiles([])
        assert profile.read_text() == "some content\n"

    def test_preserves_unrelated_content(self, tmp_path):
        profile = tmp_path / ".bashrc"
        profile.write_text(
            "# My aliases\n"
            "alias ll='ls -la'\n"
            "\n"
            "# Sloth Agent: add uv / local bin to PATH\n"
            'export PATH="${HOME}/.local/bin:${PATH}"\n'
            "\n"
            "export EDITOR=vim\n"
        )

        lines = [(profile, 3, "# Sloth Agent: add uv / local bin to PATH")]
        _clean_shell_profiles(lines)

        result = profile.read_text()
        assert "alias ll=" in result
        assert "export EDITOR=vim" in result
        assert PATH_COMMENT not in result


class TestUninstallDryRun:
    def test_dry_run_does_not_delete(self, tmp_path):
        """Dry run should list items but not delete anything."""
        sloth_dir = tmp_path / ".sloth-agent"
        sloth_dir.mkdir()
        marker = sloth_dir / "marker.txt"
        marker.write_text("test")

        from sloth_agent.cli.uninstall_cmd import uninstall

        with mock.patch.object(Path, "home", return_value=tmp_path):
            uninstall(dry_run=True, full=False, yes=True)

        # Verify nothing was deleted
        assert marker.exists()
        assert sloth_dir.exists()


class TestUninstallActual:
    def test_removes_sloth_dir_and_shims(self, tmp_path):
        sloth_dir = tmp_path / ".sloth-agent"
        sloth_dir.mkdir()
        local_bin = tmp_path / ".local" / "bin"
        local_bin.mkdir(parents=True)
        (local_bin / "sloth").write_text("#!/bin/bash\nexec sloth")

        from sloth_agent.cli.uninstall_cmd import uninstall

        with mock.patch.object(Path, "home", return_value=tmp_path):
            uninstall(dry_run=False, full=False, yes=True)

        assert not sloth_dir.exists()
        assert not (local_bin / "sloth").exists()

    def test_cancels_on_negative_input(self, tmp_path, capsys):
        sloth_dir = tmp_path / ".sloth-agent"
        sloth_dir.mkdir()

        from sloth_agent.cli.uninstall_cmd import uninstall

        # Simulate user typing "n"
        with mock.patch.object(Path, "home", return_value=tmp_path):
            with mock.patch("sloth_agent.cli.uninstall_cmd.console.input", return_value="n"):
                with pytest.raises(typer.Exit):
                    uninstall(dry_run=False, full=False, yes=False)

        # Dir should still exist
        assert sloth_dir.exists()
