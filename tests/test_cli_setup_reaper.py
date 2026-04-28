"""Tests for phantom setup-reaper CLI command and D-05 phantom serve alias."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from phantom.cli import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


# ---------------------------------------------------------------------------
# setup-reaper tests
# ---------------------------------------------------------------------------


def test_setup_reaper_help(runner):
    """setup-reaper --help shows Reaper info and exits cleanly."""
    result = runner.invoke(cli, ["setup-reaper", "--help"])
    assert result.exit_code == 0
    assert "Reaper" in result.output


def test_setup_reaper_missing_git(runner):
    """When git is not installed, setup-reaper shows error."""
    with patch("phantom.cli.setup_reaper.shutil.which", return_value=None):
        result = runner.invoke(cli, ["setup-reaper"])
    assert result.exit_code != 0
    assert "git" in result.output.lower()


def test_setup_reaper_clone(runner, tmp_path):
    """setup-reaper attempts to clone when install dir does not exist."""
    install_dir = tmp_path / "reaper-mcp"
    scripts_dir = tmp_path / "reaper-scripts"
    scripts_dir.mkdir()

    with (
        patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
        patch(
            "phantom.cli.setup_reaper._get_reaper_scripts_dir", return_value=scripts_dir
        ),
        patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        runner.invoke(
            cli,
            ["setup-reaper", "--install-dir", str(install_dir), "--json"],
        )

    assert mock_run.called
    clone_call = mock_run.call_args_list[0]
    assert "clone" in clone_call[0][0]


def test_setup_reaper_skips_when_no_reaper(runner, tmp_path):
    """setup-reaper exits silently when Reaper is not installed."""
    with (
        patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
        patch(
            "phantom.cli.setup_reaper._get_reaper_scripts_dir",
            return_value=tmp_path / "nonexistent",
        ),
    ):
        result = runner.invoke(cli, ["setup-reaper", "--json"])

    assert result.exit_code == 0
    import json

    data = json.loads(result.output)
    assert data["reaper_detected"] is False


def test_setup_reaper_hardcoded_url(runner, tmp_path):
    """Security: setup-reaper only uses the hardcoded fadelabs URL."""
    install_dir = tmp_path / "reaper-mcp"
    scripts_dir = tmp_path / "reaper-scripts"
    scripts_dir.mkdir()

    with (
        patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
        patch(
            "phantom.cli.setup_reaper._get_reaper_scripts_dir", return_value=scripts_dir
        ),
        patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        runner.invoke(
            cli,
            ["setup-reaper", "--install-dir", str(install_dir), "--json"],
        )

    clone_calls = [c for c in mock_run.call_args_list if "clone" in c[0][0]]
    assert len(clone_calls) >= 1
    cmd_args = clone_calls[0][0][0]
    assert "https://github.com/fadelabs/reaper-mcp.git" in cmd_args


def test_get_reaper_scripts_dir_macos():
    """macOS Reaper Scripts path is under Library/Application Support."""
    from phantom.cli.setup_reaper import _get_reaper_scripts_dir

    with patch("phantom.cli.setup_reaper.platform.system", return_value="Darwin"):
        path = _get_reaper_scripts_dir()
    assert "Library/Application Support/REAPER/Scripts" in str(path)


def test_get_reaper_scripts_dir_linux():
    """Linux Reaper Scripts path is under .config/REAPER."""
    from phantom.cli.setup_reaper import _get_reaper_scripts_dir

    with patch("phantom.cli.setup_reaper.platform.system", return_value="Linux"):
        path = _get_reaper_scripts_dir()
    assert ".config/REAPER/Scripts" in str(path)


def test_get_reaper_scripts_dir_windows():
    """Windows Reaper Scripts path is under APPDATA/REAPER."""
    from phantom.cli.setup_reaper import _get_reaper_scripts_dir

    with (
        patch("phantom.cli.setup_reaper.platform.system", return_value="Windows"),
        patch.dict(os.environ, {"APPDATA": "C:\\Users\\test\\AppData\\Roaming"}),
    ):
        path = _get_reaper_scripts_dir()
    path_str = str(path)
    assert "REAPER" in path_str
    assert "Scripts" in path_str


# ---------------------------------------------------------------------------
# __startup.lua auto-start tests
# ---------------------------------------------------------------------------


def test_configure_startup_creates_file(tmp_path):
    """_configure_startup_script creates __startup.lua when it doesn't exist."""
    from phantom.cli.setup_reaper import _configure_startup_script

    console = MagicMock()
    result = _configure_startup_script(tmp_path, console, json_output=False)
    startup = tmp_path / "__startup.lua"
    assert result is True
    assert startup.exists()
    content = startup.read_text()
    assert "reaper_mcp_bridge.lua" in content
    assert "[phantom]" in content


def test_configure_startup_idempotent(tmp_path):
    """Running _configure_startup_script twice doesn't duplicate the block."""
    from phantom.cli.setup_reaper import _configure_startup_script

    console = MagicMock()
    _configure_startup_script(tmp_path, console, json_output=False)
    _configure_startup_script(tmp_path, console, json_output=False)
    content = (tmp_path / "__startup.lua").read_text()
    assert content.count("[phantom]") == 1


def test_configure_startup_preserves_existing(tmp_path):
    """Existing __startup.lua content is preserved when appending."""
    from phantom.cli.setup_reaper import _configure_startup_script

    startup = tmp_path / "__startup.lua"
    startup.write_text(
        "-- user's custom startup code\nreaper.ShowConsoleMsg('hello')\n"
    )

    console = MagicMock()
    _configure_startup_script(tmp_path, console, json_output=False)
    content = startup.read_text()
    assert "user's custom startup code" in content
    assert "reaper_mcp_bridge.lua" in content


# ---------------------------------------------------------------------------
# D-05: phantom serve alias
# ---------------------------------------------------------------------------


def test_serve_command(runner):
    """D-05 validation: phantom serve exists and describes MCP server."""
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    assert "mcp" in output_lower or "server" in output_lower
