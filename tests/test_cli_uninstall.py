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
        with patch("phantom.cli.uninstall.subprocess.run", return_value=mock_proc):
            result = runner.invoke(cli, ["uninstall", "--yes"])
            assert result.exit_code == 0
            assert "Uninstalled" in result.output or "removed" in result.output.lower()

    def test_shows_artifacts_table(self, runner, phantom_dir):
        result = runner.invoke(cli, ["uninstall"], input="n\n")
        assert "Phantom Artifacts Found" in result.output
        assert "phantom-audio" in result.output
