"""Tests for phantom doctor CLI command."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from phantom.cli import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


def test_doctor_help(runner):
    """doctor --help shows diagnostic info and exits cleanly."""
    result = runner.invoke(cli, ["doctor", "--help"])
    assert result.exit_code == 0
    assert "Diagnose" in result.output


def test_doctor_healthy(runner):
    """doctor exits 0 when all core deps import successfully."""
    result = runner.invoke(cli, ["doctor"])
    # All core deps should be importable in the test environment
    assert result.exit_code == 0
    assert "Core Dependencies" in result.output


def test_doctor_json_output(runner):
    """doctor --json produces valid JSON on stdout."""
    import json

    result = runner.invoke(cli, ["doctor", "--json"])
    data = json.loads(result.output)
    assert "phantom" in data
    assert "core_deps" in data
    assert "optional_deps" in data
    assert data["phantom"]["version"]


def test_doctor_broken_core_dep(runner):
    """doctor exits 1 when a core dependency fails to import."""

    def fake_try_import(name):
        if name == "numpy":
            return False, "fake missing numpy"
        # Fall through to real import for everything else
        try:
            mod = __import__(name)
            version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
            return True, str(version)
        except Exception as exc:
            return False, str(exc)

    with patch("phantom.cli.doctor._try_import", side_effect=fake_try_import):
        result = runner.invoke(cli, ["doctor"])

    assert result.exit_code == 1


def test_doctor_json_broken_core_dep(runner):
    """doctor --json returns ok=false when a core dep is missing."""
    import json

    def fake_try_import(name):
        if name == "numpy":
            return False, "fake missing numpy"
        try:
            mod = __import__(name)
            version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
            return True, str(version)
        except Exception as exc:
            return False, str(exc)

    with patch("phantom.cli.doctor._try_import", side_effect=fake_try_import):
        result = runner.invoke(cli, ["doctor", "--json"])

    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["core_deps"]["numpy"]["ok"] is False
