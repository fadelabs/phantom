"""Tests for the read_live_metrics tool (Phantom Link feed).

Covers the live_metrics module directly and the MCP tool surface via
FastMCP's in-memory Client. All metrics files are synthetic JSON written
to per-test tmp_path dirs; PHANTOM_METRICS_DIR points at them.
"""

from __future__ import annotations

import json
import os

import pytest

from fastmcp import Client
from fastmcp.exceptions import ToolError

from phantom.exceptions import AnalysisError, PathSecurityError
from phantom.live_metrics import (
    STALE_AFTER_SECONDS,
    get_metrics_dir,
    read_live_metrics,
)
from phantom.server import mcp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """In-memory MCP client connected to phantom server."""
    async with Client(mcp) as c:
        yield c


@pytest.fixture
def metrics_dir(tmp_path, monkeypatch):
    """Per-test metrics dir wired up via PHANTOM_METRICS_DIR."""
    d = tmp_path / "metrics"
    d.mkdir()
    monkeypatch.setenv("PHANTOM_METRICS_DIR", str(d))
    return d


def _write_snapshot(d, name="aaaa-1111", **overrides):
    """Write a minimal Phantom Studio snapshot, return its path."""
    payload = {
        "schema_version": 1,
        "plugin": "Phantom Studio",
        "track": "Mix Bus",
        "sample_rate": 48000,
        "metrics": {
            "lufs_integrated": -14.2,
            "true_peak_dbtp": -1.1,
            "correlation": 0.82,
            "signal_seconds": 12.5,
        },
    }
    payload.update(overrides)
    path = d / f"{name}.json"
    path.write_text(json.dumps(payload))
    return path


# ---------------------------------------------------------------------------
# Module behaviour
# ---------------------------------------------------------------------------


def test_reads_latest_snapshot(metrics_dir):
    """A fresh snapshot is returned with its instance id and not stale."""
    _write_snapshot(metrics_dir)
    result = read_live_metrics()
    assert result.instance_id == "aaaa-1111"
    assert result.snapshot["metrics"]["lufs_integrated"] == -14.2
    assert result.stale is False
    assert result.instance_count == 1
    assert result.age_seconds >= 0.0


def test_newest_instance_wins(metrics_dir):
    """With multiple instances, the most recently written file is chosen."""
    old = _write_snapshot(metrics_dir, name="old-instance", track="Old")
    _write_snapshot(metrics_dir, name="new-instance", track="New")
    past = os.path.getmtime(old) - 60
    os.utime(old, (past, past))
    result = read_live_metrics()
    assert result.instance_id == "new-instance"
    assert result.instance_count == 2


def test_specific_instance(metrics_dir):
    """instance_id selects that instance's file even if another is newer."""
    _write_snapshot(metrics_dir, name="alpha", track="Alpha")
    _write_snapshot(metrics_dir, name="beta", track="Beta")
    result = read_live_metrics("alpha")
    assert result.instance_id == "alpha"
    assert result.snapshot["track"] == "Alpha"


def test_stale_flag(metrics_dir):
    """A snapshot older than the threshold is flagged stale."""
    path = _write_snapshot(metrics_dir)
    past = os.path.getmtime(path) - (STALE_AFTER_SECONDS + 30)
    os.utime(path, (past, past))
    result = read_live_metrics()
    assert result.stale is True
    assert result.age_seconds > STALE_AFTER_SECONDS


def test_missing_dir(tmp_path, monkeypatch):
    """A nonexistent metrics dir yields the musician-friendly error."""
    monkeypatch.setenv("PHANTOM_METRICS_DIR", str(tmp_path / "nope"))
    with pytest.raises(AnalysisError, match="is the Phantom Studio plugin running"):
        read_live_metrics()


def test_empty_dir(metrics_dir):
    """An empty metrics dir yields the musician-friendly error."""
    with pytest.raises(AnalysisError, match="is the Phantom Studio plugin running"):
        read_live_metrics()


def test_unknown_instance(metrics_dir):
    """Asking for an instance that has no file is a friendly error."""
    _write_snapshot(metrics_dir)
    with pytest.raises(AnalysisError, match="is that plugin instance still open"):
        read_live_metrics("zzzz-9999")


def test_traversal_rejected(metrics_dir):
    """Path separators and dots in instance_id are rejected outright."""
    _write_snapshot(metrics_dir)
    for bad in ("../evil", "a/b", "..", ".hidden"):
        with pytest.raises(PathSecurityError):
            read_live_metrics(bad)


def test_symlink_escape_skipped(metrics_dir, tmp_path):
    """A symlink pointing outside the metrics dir is never followed."""
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"secret": True}))
    (metrics_dir / "sneaky.json").symlink_to(outside)
    # Not eligible for newest-file selection...
    with pytest.raises(AnalysisError, match="is the Phantom Studio plugin running"):
        read_live_metrics()
    # ...and not readable by explicit instance id either.
    with pytest.raises((AnalysisError, PathSecurityError)):
        read_live_metrics("sneaky")


def test_corrupt_json(metrics_dir):
    """Unparseable JSON yields a retry-flavoured error, not a traceback."""
    (metrics_dir / "broken.json").write_text("{not json")
    with pytest.raises(AnalysisError, match="try again"):
        read_live_metrics()


def test_non_object_json(metrics_dir):
    """A JSON array/scalar payload is rejected the same way."""
    (metrics_dir / "weird.json").write_text("[1, 2, 3]")
    with pytest.raises(AnalysisError, match="try again"):
        read_live_metrics()


def test_env_override_beats_default(metrics_dir, monkeypatch):
    """PHANTOM_METRICS_DIR takes precedence over the platform default."""
    assert get_metrics_dir() == str(metrics_dir)
    monkeypatch.delenv("PHANTOM_METRICS_DIR")
    assert get_metrics_dir() != str(metrics_dir)


# ---------------------------------------------------------------------------
# MCP tool surface
# ---------------------------------------------------------------------------


async def test_tool_via_client(client, metrics_dir):
    """read_live_metrics is callable over MCP and returns the snapshot."""
    _write_snapshot(metrics_dir)
    result = await client.call_tool("read_live_metrics", {})
    data = result.data
    assert data["instance_id"] == "aaaa-1111"
    assert data["snapshot"]["metrics"]["true_peak_dbtp"] == -1.1
    assert data["stale"] is False


async def test_tool_error_via_client(client, tmp_path, monkeypatch):
    """The no-metrics case surfaces as a structured ToolError."""
    monkeypatch.setenv("PHANTOM_METRICS_DIR", str(tmp_path / "empty-nope"))
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool("read_live_metrics", {})
    error = json.loads(str(exc_info.value))
    assert error["error_type"] == "AnalysisError"
    assert "Phantom Studio plugin" in error["message"]


async def test_tool_listed(client):
    """read_live_metrics appears in the tool listing."""
    tools = await client.list_tools()
    assert "read_live_metrics" in {t.name for t in tools}
