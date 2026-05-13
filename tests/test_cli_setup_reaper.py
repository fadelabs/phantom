"""Tests for phantom setup-reaper CLI command and D-05 phantom serve alias."""

from __future__ import annotations

import os
import subprocess
from unittest.mock import MagicMock, patch

import click
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


# ---------------------------------------------------------------------------
# _run_step timeout tests
# ---------------------------------------------------------------------------


class TestRunStepTimeout:
    """Tests for _run_step timeout handling."""

    def test_timeout_raises_click_exception(self):
        """_run_step raises ClickException with 'timed out' when subprocess times out."""
        from phantom.cli.setup_reaper import _run_step

        with patch(
            "phantom.cli.setup_reaper.subprocess.run",
            side_effect=subprocess.TimeoutExpired(
                cmd=["git", "clone", "https://example.com"], timeout=30
            ),
        ):
            with pytest.raises(click.ClickException, match="timed out"):
                _run_step(
                    ["git", "clone", "https://example.com"], "Git clone", timeout=30
                )

    def test_timeout_passes_to_subprocess(self):
        """_run_step passes timeout parameter to subprocess.run."""
        from phantom.cli.setup_reaper import _run_step

        with patch("phantom.cli.setup_reaper.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            _run_step(["git", "status"], "Git status", timeout=30)
            mock_run.assert_called_once_with(
                ["git", "status"], check=True, capture_output=True, timeout=30
            )

    def test_timeout_error_message_content(self):
        """Timeout error message includes '30 seconds' and 'Check your connection'."""
        from phantom.cli.setup_reaper import _run_step

        with patch(
            "phantom.cli.setup_reaper.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd=["git", "pull"], timeout=30),
        ):
            with pytest.raises(
                click.ClickException, match=r"30 seconds.*Check your connection"
            ):
                _run_step(["git", "pull"], "Git pull", timeout=30)

    def test_git_clone_uses_timeout_constant(self, runner, tmp_path):
        """setup-reaper passes _GIT_TIMEOUT_SECONDS to git clone call."""
        from phantom.cli.setup_reaper import _GIT_TIMEOUT_SECONDS

        install_dir = tmp_path / "reaper-mcp"
        scripts_dir = tmp_path / "reaper-scripts"
        scripts_dir.mkdir()

        with (
            patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
            patch(
                "phantom.cli.setup_reaper._get_reaper_scripts_dir",
                return_value=scripts_dir,
            ),
            patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            runner.invoke(
                cli,
                ["setup-reaper", "--install-dir", str(install_dir), "--json"],
            )

        # Find the clone call and verify timeout was passed
        clone_calls = [c for c in mock_run.call_args_list if "clone" in str(c)]
        assert len(clone_calls) >= 1
        # The clone call should have timeout=_GIT_TIMEOUT_SECONDS
        clone_kwargs = clone_calls[0][1] if clone_calls[0][1] else {}
        assert clone_kwargs.get("timeout") == _GIT_TIMEOUT_SECONDS


# ---------------------------------------------------------------------------
# D-01 / D-03: Version pinning tests
# ---------------------------------------------------------------------------


class TestVersionPinning:
    """Tests for version-pinned clone and tag-based update (D-01, D-03)."""

    def test_version_pin_fresh_clone(self, runner, tmp_path):
        """D-01: Fresh clone includes --branch v{__version__} arguments."""
        install_dir = tmp_path / "reaper-mcp"
        scripts_dir = tmp_path / "reaper-scripts"
        scripts_dir.mkdir()

        with (
            patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
            patch(
                "phantom.cli.setup_reaper._get_reaper_scripts_dir",
                return_value=scripts_dir,
            ),
            patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0)
            runner.invoke(
                cli,
                ["setup-reaper", "--install-dir", str(install_dir), "--json"],
            )

        # Find the clone call
        clone_calls = [c for c in mock_run.call_args_list if "clone" in str(c)]
        assert len(clone_calls) >= 1
        cmd_args = clone_calls[0][0][0]
        assert "--branch" in cmd_args
        # Version tag should start with 'v'
        branch_idx = cmd_args.index("--branch")
        assert cmd_args[branch_idx + 1].startswith("v")

    def test_version_pin_update_uses_fetch_checkout(self, runner, tmp_path):
        """D-01: Update path uses fetch --tags + checkout v{version}, not pull --ff-only."""
        install_dir = tmp_path / "reaper-mcp"
        install_dir.mkdir()
        (install_dir / ".git").mkdir()  # Make it look like a git repo
        scripts_dir = tmp_path / "reaper-scripts"
        scripts_dir.mkdir()

        with (
            patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
            patch(
                "phantom.cli.setup_reaper._get_reaper_scripts_dir",
                return_value=scripts_dir,
            ),
            patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(returncode=0, stdout=b"https://github.com/fadelabs/reaper-mcp.git\n")
            runner.invoke(
                cli,
                ["setup-reaper", "--install-dir", str(install_dir), "--json"],
            )

        all_cmds = [c[0][0] for c in mock_run.call_args_list]
        # Should have fetch and checkout commands, not pull --ff-only
        has_fetch = any("fetch" in cmd for cmd in all_cmds)
        has_checkout = any("checkout" in cmd for cmd in all_cmds)
        has_pull_ff = any("pull" in cmd and "--ff-only" in cmd for cmd in all_cmds)
        assert has_fetch, f"Expected fetch command in {all_cmds}"
        assert has_checkout, f"Expected checkout command in {all_cmds}"
        assert not has_pull_ff, f"Should not use pull --ff-only, found in {all_cmds}"

    def test_version_pin_fallback_on_missing_tag(self, runner, tmp_path):
        """D-03: When pinned clone fails, falls back to HEAD with warning."""
        install_dir = tmp_path / "reaper-mcp"
        scripts_dir = tmp_path / "reaper-scripts"
        scripts_dir.mkdir()

        call_count = 0

        def side_effect_fn(cmd, **kwargs):
            nonlocal call_count
            call_count += 1
            # First clone call (with --branch) should fail
            if "clone" in cmd and "--branch" in cmd:
                raise subprocess.CalledProcessError(
                    128, cmd, stderr=b"fatal: Remote branch v99.99.99 not found"
                )
            # All other calls succeed
            return MagicMock(returncode=0, stdout=b"")

        with (
            patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
            patch(
                "phantom.cli.setup_reaper._get_reaper_scripts_dir",
                return_value=scripts_dir,
            ),
            patch("phantom.cli.setup_reaper.subprocess.run", side_effect=side_effect_fn),
        ):
            result = runner.invoke(
                cli,
                ["setup-reaper", "--install-dir", str(install_dir)],
            )

        # Should contain warning about unverified version
        output_lower = result.output.lower()
        assert "unverified" in output_lower or "warning" in output_lower, (
            f"Expected fallback warning in output: {result.output}"
        )


# ---------------------------------------------------------------------------
# D-06 / D-07: Lua whitelist tests
# ---------------------------------------------------------------------------


class TestLuaWhitelist:
    """Tests for Lua filename whitelist (D-06, D-07)."""

    def test_whitelist_copies_expected_file(self, runner, tmp_path):
        """D-06: Whitelisted file reaper_mcp_bridge.lua IS copied to scripts_dir."""
        install_dir = tmp_path / "reaper-mcp"
        install_dir.mkdir()
        (install_dir / ".git").mkdir()  # Make it look like a git repo
        scripts_dir = tmp_path / "reaper-scripts"
        scripts_dir.mkdir()

        # Pre-create the expected Lua file in install dir
        (install_dir / "reaper_mcp_bridge.lua").write_text("-- bridge script")

        with (
            patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
            patch(
                "phantom.cli.setup_reaper._get_reaper_scripts_dir",
                return_value=scripts_dir,
            ),
            patch("phantom.cli.setup_reaper._run_step"),  # Skip actual git
            patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/fadelabs/reaper-mcp.git\n",
            )
            runner.invoke(
                cli,
                ["setup-reaper", "--install-dir", str(install_dir), "--json"],
            )

        assert (scripts_dir / "reaper_mcp_bridge.lua").exists()

    def test_whitelist_blocks_unexpected_file(self, runner, tmp_path):
        """D-06: Unexpected Lua file evil_payload.lua is NOT copied."""
        install_dir = tmp_path / "reaper-mcp"
        install_dir.mkdir()
        (install_dir / ".git").mkdir()  # Make it look like a git repo
        scripts_dir = tmp_path / "reaper-scripts"
        scripts_dir.mkdir()

        # Create both expected and unexpected Lua files
        (install_dir / "reaper_mcp_bridge.lua").write_text("-- bridge script")
        (install_dir / "evil_payload.lua").write_text("-- malicious payload")

        with (
            patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
            patch(
                "phantom.cli.setup_reaper._get_reaper_scripts_dir",
                return_value=scripts_dir,
            ),
            patch("phantom.cli.setup_reaper._run_step"),  # Skip actual git
            patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/fadelabs/reaper-mcp.git\n",
            )
            runner.invoke(
                cli,
                ["setup-reaper", "--install-dir", str(install_dir), "--json"],
            )

        # Only the whitelisted file should be copied
        assert (scripts_dir / "reaper_mcp_bridge.lua").exists()
        assert not (scripts_dir / "evil_payload.lua").exists()

    def test_unexpected_lua_warning(self, runner, tmp_path):
        """D-07: Unexpected Lua files produce a warning in output."""
        install_dir = tmp_path / "reaper-mcp"
        install_dir.mkdir()
        (install_dir / ".git").mkdir()  # Make it look like a git repo
        scripts_dir = tmp_path / "reaper-scripts"
        scripts_dir.mkdir()

        # Create expected + unexpected Lua files
        (install_dir / "reaper_mcp_bridge.lua").write_text("-- bridge script")
        (install_dir / "sneaky.lua").write_text("-- sneaky script")

        with (
            patch("phantom.cli.setup_reaper.shutil.which", return_value="/usr/bin/git"),
            patch(
                "phantom.cli.setup_reaper._get_reaper_scripts_dir",
                return_value=scripts_dir,
            ),
            patch("phantom.cli.setup_reaper._run_step"),  # Skip actual git
            patch("phantom.cli.setup_reaper.subprocess.run") as mock_run,
        ):
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="https://github.com/fadelabs/reaper-mcp.git\n",
            )
            result = runner.invoke(
                cli,
                ["setup-reaper", "--install-dir", str(install_dir)],
            )

        output_lower = result.output.lower()
        assert "skipping unexpected" in output_lower or "unexpected lua" in output_lower, (
            f"Expected warning about unexpected Lua files in output: {result.output}"
        )
