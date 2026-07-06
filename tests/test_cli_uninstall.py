"""Tests for phantom uninstall CLI command."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from phantom.cli import cli
from phantom.cli.uninstall import (
    _find_artifacts,
    _remove_mcp_entries,
    _remove_startup_hook,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def phantom_dir(tmp_path, monkeypatch):
    """Create a fake ~/.phantom directory."""
    d = tmp_path / ".phantom"
    d.mkdir()
    (d / "update-check.json").write_text("{}")
    monkeypatch.setattr("phantom.cli.uninstall._PHANTOM_DIR", d)
    return d


# ---------------------------------------------------------------------------
# _find_artifacts
# ---------------------------------------------------------------------------


class TestFindArtifacts:
    def test_finds_phantom_dir(self, phantom_dir):
        artifacts = _find_artifacts()
        assert "phantom_dir" in artifacts
        assert artifacts["phantom_dir"] == str(phantom_dir)

    def test_no_phantom_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "phantom.cli.uninstall._PHANTOM_DIR", tmp_path / "nonexistent"
        )
        artifacts = _find_artifacts()
        assert "phantom_dir" not in artifacts

    def test_finds_mcp_config(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "phantom.cli.uninstall._PHANTOM_DIR", tmp_path / "nonexistent"
        )
        mcp = tmp_path / ".mcp.json"
        mcp.write_text(
            json.dumps({"mcpServers": {"phantom": {"command": "phantom-mcp"}}})
        )
        with patch("phantom.cli.uninstall.Path.cwd", return_value=tmp_path):
            artifacts = _find_artifacts()
        assert "mcp_configs" in artifacts
        assert artifacts["mcp_configs"][0]["has_phantom"] is True


# ---------------------------------------------------------------------------
# _remove_mcp_entries
# ---------------------------------------------------------------------------


class TestRemoveMcpEntries:
    def test_removes_phantom_entry(self, tmp_path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "phantom": {"command": "phantom-mcp"},
                        "other": {"command": "other"},
                    }
                }
            )
        )
        _remove_mcp_entries(str(cfg), remove_phantom=True, remove_reaper=False)
        data = json.loads(cfg.read_text())
        assert "phantom" not in data["mcpServers"]
        assert "other" in data["mcpServers"]

    def test_removes_both_entries(self, tmp_path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "phantom": {"command": "phantom-mcp"},
                        "reaper": {"command": "reaper-mcp"},
                    }
                }
            )
        )
        _remove_mcp_entries(str(cfg), remove_phantom=True, remove_reaper=True)
        assert not cfg.exists()

    def test_deletes_empty_file(self, tmp_path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text(
            json.dumps({"mcpServers": {"phantom": {"command": "phantom-mcp"}}})
        )
        _remove_mcp_entries(str(cfg), remove_phantom=True, remove_reaper=False)
        assert not cfg.exists()

    def test_remove_mcp_entries_returns_false_on_write_error(
        self, tmp_path, monkeypatch
    ):
        # A write failure must be reported, not silently swallowed (P-15).
        from phantom.cli import uninstall

        cfg = tmp_path / "config.json"
        cfg.write_text('{"mcpServers": {"phantom": {}, "other": {}}}')

        def _boom(*a, **k):
            raise OSError("disk full")

        monkeypatch.setattr(uninstall, "atomic_write_text", _boom)
        ok = uninstall._remove_mcp_entries(
            str(cfg), remove_phantom=True, remove_reaper=False
        )
        assert ok is False

    def test_remove_mcp_entries_returns_true_on_success(self, tmp_path):
        from phantom.cli import uninstall

        cfg = tmp_path / "config.json"
        cfg.write_text('{"mcpServers": {"phantom": {}, "other": {}}}')
        ok = uninstall._remove_mcp_entries(
            str(cfg), remove_phantom=True, remove_reaper=False
        )
        assert ok is True


# ---------------------------------------------------------------------------
# _remove_startup_hook
# ---------------------------------------------------------------------------


class TestRemoveStartupHook:
    def test_removes_phantom_block(self, tmp_path):
        startup = tmp_path / "__startup.lua"
        startup.write_text(
            "-- other stuff\n"
            "dofile('something.lua')\n"
            "-- [phantom] auto-start MCP bridge\n"
            "dofile(reaper.GetResourcePath())\n"
            "-- [/phantom]\n"
            "-- more stuff\n"
        )
        _remove_startup_hook(str(startup))
        content = startup.read_text()
        assert "[phantom]" not in content
        assert "other stuff" in content
        assert "more stuff" in content

    def test_deletes_file_if_only_phantom(self, tmp_path):
        startup = tmp_path / "__startup.lua"
        startup.write_text(
            "-- [phantom] auto-start MCP bridge\n"
            "dofile(reaper.GetResourcePath())\n"
            "-- [/phantom]\n"
        )
        _remove_startup_hook(str(startup))
        assert not startup.exists()

    def test_remove_startup_hook_returns_false_on_error(self, tmp_path, monkeypatch):
        from phantom.cli import uninstall

        startup = tmp_path / "__startup.lua"
        startup.write_text(
            "-- [phantom] auto-start MCP bridge\nfoo()\n-- [/phantom]\nkeep()\n"
        )

        def _boom(*a, **k):
            raise OSError("read-only fs")

        monkeypatch.setattr(uninstall, "atomic_write_text", _boom)
        ok = uninstall._remove_startup_hook(str(startup))
        assert ok is False

    def test_missing_end_marker_preserves_trailing_lines(self, tmp_path):
        """A phantom block missing its ``-- [/phantom]`` end marker must not
        swallow the user's trailing content (the old uninstall bug deleted to
        EOF once the skip flag latched).
        """
        from phantom.cli import uninstall

        startup = tmp_path / "__startup.lua"
        startup.write_text(
            "-- user header line\n"
            "-- [phantom] auto-start MCP bridge\n"
            "dofile(reaper.GetResourcePath())\n"
            "-- (end marker was manually deleted)\n"
            "dofile('user_own_script.lua')\n"
            "-- user trailing line\n"
        )
        ok = uninstall._remove_startup_hook(str(startup))
        assert ok is True
        content = startup.read_text()
        # The marker line itself is stripped, but real user content survives.
        assert "auto-start MCP bridge" not in content
        assert "user header line" in content
        assert "user_own_script.lua" in content
        assert "user trailing line" in content


# ---------------------------------------------------------------------------
# phantom uninstall command
# ---------------------------------------------------------------------------


class TestUninstallCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ["uninstall", "--help"])
        assert result.exit_code == 0
        assert "Remove Phantom" in result.output

    def test_cancel(self, runner, phantom_dir):
        result = runner.invoke(cli, ["uninstall"], input="n\n")
        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()
        assert phantom_dir.exists()

    def test_uninstall_with_yes(self, runner, phantom_dir):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        # Run in an isolated cwd so the --yes uninstall can't rewrite the
        # developer's real ./.mcp.json (which would strip the phantom entry and
        # trip the CLI group's first-run auto-setup in later tests).
        with (
            runner.isolated_filesystem(),
            patch("phantom.cli.uninstall.subprocess.run", return_value=mock_proc),
        ):
            result = runner.invoke(cli, ["uninstall", "--yes"])
            assert result.exit_code == 0
            assert "Uninstalled" in result.output or "removed" in result.output.lower()

    def test_shows_artifacts_table(self, runner, phantom_dir):
        result = runner.invoke(cli, ["uninstall"], input="n\n")
        assert "Phantom Artifacts Found" in result.output
        assert "phantom-audio" in result.output

    def test_uv_uninstall_has_timeout(self, monkeypatch):
        # The uv tool uninstall call must pass a timeout (P-16).
        from phantom.cli import uninstall

        captured = {}

        class _Proc:
            returncode = 0
            stdout = "uninstalled phantom-audio"
            stderr = ""

        def _fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return _Proc()

        monkeypatch.setattr(uninstall.subprocess, "run", _fake_run)
        uninstall._uninstall_uv_package(uninstall.get_console(), [])
        assert "timeout" in captured and captured["timeout"] == 30
