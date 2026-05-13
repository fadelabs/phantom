"""Tests for phantom setup CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from phantom.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def clean_env(tmp_path, monkeypatch):
    """Isolated environment with no existing config."""
    monkeypatch.setattr(
        "phantom.cli.setup._mcp_candidates", lambda: [tmp_path / ".mcp.json"]
    )
    return tmp_path


class TestMcpConfig:
    def test_writes_phantom_entry(self, runner, clean_env):
        result = runner.invoke(cli, ["setup", "--skip-plugin", "--skip-reaper"])
        assert result.exit_code == 0
        mcp = clean_env / ".mcp.json"
        assert mcp.exists()
        data = json.loads(mcp.read_text())
        assert "phantom" in data["mcpServers"]
        assert data["mcpServers"]["phantom"]["command"] == "phantom-mcp"

    def test_skips_if_already_configured(self, runner, clean_env):
        mcp = clean_env / ".mcp.json"
        mcp.write_text(
            json.dumps({"mcpServers": {"phantom": {"command": "phantom-mcp"}}})
        )
        result = runner.invoke(cli, ["setup", "--skip-plugin", "--skip-reaper"])
        assert result.exit_code == 0
        assert "already configured" in result.output.lower()

    def test_preserves_existing_servers(self, runner, clean_env):
        mcp = clean_env / ".mcp.json"
        mcp.write_text(
            json.dumps({"mcpServers": {"other": {"command": "other-server"}}})
        )
        result = runner.invoke(cli, ["setup", "--skip-plugin", "--skip-reaper"])
        assert result.exit_code == 0
        data = json.loads(mcp.read_text())
        assert "other" in data["mcpServers"]
        assert "phantom" in data["mcpServers"]


class TestPluginSetup:
    def test_skips_when_claude_not_installed(self, runner, clean_env):
        with patch("phantom.cli.setup.shutil.which", return_value=None):
            result = runner.invoke(cli, ["setup", "--skip-reaper"])
            assert result.exit_code == 0
            assert "Claude Code not installed" in result.output

    def test_skip_plugin_flag(self, runner, clean_env):
        result = runner.invoke(cli, ["setup", "--skip-plugin", "--skip-reaper"])
        assert result.exit_code == 0
        assert "skipped" in result.output.lower()


class TestReaperSetup:
    def test_skips_when_reaper_not_detected(self, runner, clean_env):
        with patch(
            "phantom.cli.setup_reaper._get_reaper_scripts_dir",
            return_value=clean_env / "nonexistent",
        ):
            result = runner.invoke(cli, ["setup", "--skip-plugin"])
            assert result.exit_code == 0
            assert "not detected" in result.output.lower()

    def test_skip_reaper_flag(self, runner, clean_env):
        result = runner.invoke(cli, ["setup", "--skip-plugin", "--skip-reaper"])
        assert result.exit_code == 0
        assert "skipped" in result.output.lower()


class TestSetupCommand:
    def test_help(self, runner):
        result = runner.invoke(cli, ["setup", "--help"])
        assert result.exit_code == 0
        assert "Set up Phantom" in result.output

    def test_json_output(self, runner, clean_env):
        with patch("phantom.cli.setup.shutil.which", return_value=None):
            result = runner.invoke(cli, ["setup", "--json", "--skip-reaper"])
            data = json.loads(result.output)
            assert "steps" in data
            assert len(data["steps"]) == 3


class TestMarketplaceVersionPin:
    """Verify marketplace.json ref field stays in sync with plugin version (D-01)."""

    def test_marketplace_ref_matches_version(self):
        """marketplace.json source.ref must equal 'v' + plugin version."""
        repo_root = Path(__file__).parent.parent

        marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
        with open(marketplace_path) as f:
            marketplace = json.load(f)

        plugin_path = repo_root / "plugin" / ".claude-plugin" / "plugin.json"
        with open(plugin_path) as f:
            plugin = json.load(f)

        plugin_version = plugin["version"]
        source = marketplace["plugins"][0]["source"]

        assert "ref" in source, "marketplace.json source must contain a 'ref' field"
        assert source["ref"] == f"v{plugin_version}", (
            f"marketplace.json ref '{source['ref']}' does not match "
            f"plugin version 'v{plugin_version}'"
        )
