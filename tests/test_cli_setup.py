"""Tests for phantom setup CLI command."""

from __future__ import annotations

import json

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
