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

    with (
        patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
        patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        runner.invoke(
            cli,
            ["setup-reaper", "--install-dir", str(install_dir), "--json"],
        )

    # The clone call should have been made
    assert mock_run.called
    clone_call = mock_run.call_args_list[0]
    assert "clone" in clone_call[0][0]


def test_setup_reaper_hardcoded_url(runner, tmp_path):
    """Security: setup-reaper only uses the hardcoded TwelveTake-Studios URL."""
    install_dir = tmp_path / "reaper-mcp"

    with (
        patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
        patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
    ):
        mock_run.return_value = MagicMock(returncode=0)
        runner.invoke(
            cli,
            ["setup-reaper", "--install-dir", str(install_dir), "--json"],
        )

    # Find the git clone call
    clone_calls = [c for c in mock_run.call_args_list if "clone" in c[0][0]]
    assert len(clone_calls) >= 1
    cmd_args = clone_calls[0][0][0]
    assert "https://github.com/TwelveTake-Studios/reaper-mcp.git" in cmd_args


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
# D-05: phantom serve alias
# ---------------------------------------------------------------------------


def test_serve_command(runner):
    """D-05 validation: phantom serve exists and describes MCP server."""
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    assert "mcp" in output_lower or "server" in output_lower
