"""Integration tests for Phantom MCP server.

Tests verify server module structure, tool registration count and names,
entry point configuration, and subprocess startup over MCP stdio transport.
"""

from __future__ import annotations

import subprocess
import time

import pytest
from fastmcp import Client


@pytest.fixture
async def client():
    """In-memory MCP client connected to phantom server."""
    from phantom.server import mcp

    async with Client(mcp) as c:
        yield c


def test_server_module_import():
    """Server module imports without error and has mcp instance (SRV-07)."""
    from phantom.server import main, mcp

    assert mcp is not None
    assert callable(main)


def test_main_module_import():
    """__main__.py imports correctly for python -m phantom (SRV-08).

    Updated: __main__.py now routes to CLI (phantom.cli.cli) instead of
    the MCP server. The MCP server is available via phantom-mcp entry point.
    """
    from phantom.__main__ import cli

    assert callable(cli)


async def test_server_tool_count(client):
    """Server registers at least 17 tools (SRV-01)."""
    tools = await client.list_tools()
    assert len(tools) >= 17, f"Expected >=17 tools, got {len(tools)}"


async def test_server_tool_names(client):
    """All 17 required tool names are registered (SRV-01)."""
    tools = await client.list_tools()
    tool_names = {t.name for t in tools}
    required = {
        "analyze_spectrum",
        "analyze_loudness",
        "analyze_dynamics",
        "analyze_stereo",
        "analyze_phase",
        "compare_phase",
        "detect_problems",
        "analyze_masking",
        "compare_to_profile",
        "compare_to_reference",
        "list_profiles",
        "load_profile",
        "separate_stems",
        "match_to_reference",
        "full_diagnostic",
        "batch_diagnostic",
        "multi_stem_masking",
    }
    missing = required - tool_names
    assert not missing, f"Missing tools: {missing}"


def test_phantom_mcp_entry_point():
    """phantom-mcp console script is configured in pyproject.toml (SRV-08)."""
    import sys
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        try:
            import tomli as tomllib
        except ImportError:
            pytest.skip("tomllib requires Python 3.11+ or tomli package")
    from pathlib import Path

    pyproject = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject, "rb") as f:
        config = tomllib.load(f)
    scripts = config.get("project", {}).get("scripts", {})
    assert "phantom-mcp" in scripts, "phantom-mcp not in [project.scripts]"
    assert scripts["phantom-mcp"] == "phantom.server:main"


def test_server_subprocess_starts():
    """Server process starts without crashing via python -m phantom.server (SRV-07)."""
    proc = subprocess.Popen(
        ["uv", "run", "--extra", "dev", "python", "-m", "phantom.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # Poll until process has survived at least 0.5s of startup (max 5s)
    start = time.monotonic()
    while time.monotonic() - start < 5.0:
        time.sleep(0.1)
        poll = proc.poll()
        if poll is not None:
            stderr = proc.stderr.read().decode()
            pytest.fail(f"Server exited with code {poll}: {stderr}")
        if time.monotonic() - start >= 0.5:
            break  # survived 0.5s of startup -- good enough
    # Clean up
    proc.terminate()
    proc.wait(timeout=5)
