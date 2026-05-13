"""Tests for long audio duration handling.

Verifies analysis modules complete on 60s audio without timeout or crash.
All audio is synthetic (session-scoped fixture from conftest.py).
"""

from __future__ import annotations

import json

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from phantom.audio import load_audio
from phantom.problems import detect_problems
from phantom.server import mcp


@pytest.mark.slow
@pytest.mark.timeout(120)
def test_detect_problems_long_audio(long_stereo_60s, wav_file_factory):
    """detect_problems completes on 60s stereo audio, returns valid ProblemsResult."""
    samples, sr = long_stereo_60s
    path = wav_file_factory(samples, sr)
    audio = load_audio(path)
    result = detect_problems(audio)
    assert result is not None
    assert hasattr(result, "problems")
    assert hasattr(result, "clean")
    assert isinstance(result.problems, list)


@pytest.mark.slow
@pytest.mark.timeout(120)
async def test_full_diagnostic_long_audio(long_stereo_60s, wav_file_factory):
    """full_diagnostic completes on 60s stereo audio via MCP client."""
    samples, sr = long_stereo_60s
    path = wav_file_factory(samples, sr)
    async with Client(mcp) as client:
        result = await client.call_tool("full_diagnostic", {"file_path": path})
    data = result.data
    assert data is not None
    # Verify all 6 analysis sections are present
    for section in ("spectral", "loudness", "dynamics", "stereo", "phase", "problems"):
        assert section in data, f"Missing section: {section}"
