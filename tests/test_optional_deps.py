"""Tests for optional dependency integration.

Tests in this file verify both the presence path (import + basic call when
dep is installed) and the absence path (DependencyMissingError when dep is
missing). The CI main job runs absence tests; the optional-deps CI job runs
presence tests.
"""

from __future__ import annotations

import importlib
import importlib.util
import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from phantom.server import mcp


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """In-memory MCP client connected to phantom server."""
    async with Client(mcp) as c:
        yield c


# ---------------------------------------------------------------------------
# Section 1: Presence tests (run when dep IS installed)
# Per D-10: verify import + basic callable attribute, no quality checks.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _has_module("matchering"),
    reason="matchering is not installed -- test requires it",
)
def test_matchering_import_and_basic_call():
    """Matchering import succeeds and matchering.process is callable."""
    import matchering

    assert hasattr(matchering, "process")
    assert callable(matchering.process)


@pytest.mark.skipif(
    not _has_module("demucs"),
    reason="demucs is not installed -- test requires it",
)
def test_demucs_import_and_basic_call():
    """Demucs import succeeds and get_model function is callable."""
    import demucs.pretrained

    assert hasattr(demucs.pretrained, "get_model")
    assert callable(demucs.pretrained.get_model)


@pytest.mark.skipif(
    not _has_module("pedalboard"),
    reason="pedalboard is not installed -- test requires it",
)
def test_pedalboard_import_and_basic_call():
    """Pedalboard import succeeds and Pedalboard() is instantiable."""
    import pedalboard

    board = pedalboard.Pedalboard()
    assert board is not None


# ---------------------------------------------------------------------------
# Section 2: Absence tests (run when dep is NOT installed)
# Per D-11: verify DependencyMissingError with install hint via MCP client.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    _has_module("matchering"),
    reason="matchering is installed -- test requires it to be absent",
)
async def test_match_to_reference_missing_dep(client):
    """match_to_reference raises ToolError with DependencyMissingError when Matchering not installed."""
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool(
            "match_to_reference",
            {
                "target_path": "/tmp/test.wav",
                "reference_path": "/tmp/ref.wav",
                "output_path": "/tmp/out.wav",
            },
        )
    error = json.loads(str(exc_info.value))
    assert error["error_type"] == "DependencyMissingError"
    assert "not installed" in error["message"].lower()


@pytest.mark.skipif(
    _has_module("demucs"),
    reason="demucs is installed -- test requires it to be absent",
)
async def test_separate_stems_missing_dep(client):
    """separate_stems raises ToolError with DependencyMissingError when Demucs not installed."""
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool(
            "separate_stems",
            {"file_path": "/tmp/test.wav", "output_dir": "/tmp"},
        )
    error = json.loads(str(exc_info.value))
    assert error["error_type"] == "DependencyMissingError"
    assert "not installed" in error["message"].lower()


@pytest.mark.skipif(
    _has_module("pedalboard"),
    reason="pedalboard is installed -- test requires it to be absent",
)
async def test_fix_audio_missing_dep(client):
    """fix_audio raises ToolError with DependencyMissingError when Pedalboard not installed."""
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool(
            "fix_audio",
            {"file_path": "/tmp/test.wav"},
        )
    error = json.loads(str(exc_info.value))
    assert error["error_type"] == "DependencyMissingError"
    assert "not installed" in error["message"].lower()
