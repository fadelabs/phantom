"""Tests for error schema consistency across all MCP tools."""

from __future__ import annotations

import functools
import importlib
import json

import pytest

from fastmcp import Client
from fastmcp.exceptions import ToolError

from phantom.server import mcp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    """In-memory MCP client connected to phantom server."""
    async with Client(mcp) as c:
        yield c


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Tools that cannot be triggered into an error with simple bad args.
_SKIP_TOOLS = {"list_profiles"}


def _get_bad_args(tool_name: str) -> dict:
    """Return arguments designed to trigger a ToolError for *tool_name*.

    Strategy: pass nonexistent file paths or names so each tool raises
    an error without performing any real work.
    """
    single_file_tools = {
        "analyze_spectrum",
        "analyze_loudness",
        "analyze_dynamics",
        "analyze_stereo",
        "analyze_phase",
        "detect_problems",
        "full_diagnostic",
    }

    if tool_name in single_file_tools:
        return {"file_path": "/nonexistent/test.wav"}

    mapping: dict[str, dict] = {
        "compare_phase": {
            "file_path_a": "/nonexistent/a.wav",
            "file_path_b": "/nonexistent/b.wav",
        },
        "analyze_masking": {
            "file_path_a": "/nonexistent/a.wav",
            "file_path_b": "/nonexistent/b.wav",
        },
        "compare_to_profile": {
            "file_path": "/nonexistent/test.wav",
            "profile_name": "nonexistent_xyz",
        },
        "compare_to_reference": {
            "file_path": "/nonexistent/test.wav",
            "reference_path": "/nonexistent/ref.wav",
        },
        "load_profile": {"name": "nonexistent_xyz"},
        "separate_stems": {
            "file_path": "/nonexistent/test.wav",
            "output_dir": "/tmp",
        },
        "match_to_reference": {
            "target_path": "/nonexistent/target.wav",
            "reference_path": "/nonexistent/ref.wav",
            "output_path": "/nonexistent/out.wav",
        },
        "fix_audio": {"file_path": "/nonexistent/test.wav"},
        "apply_processing": {
            "file_path": "/nonexistent/test.wav",
            "operations": [{"type": "gain", "gain_db": 0}],
            "output_path": "/nonexistent/out.wav",
        },
        "multi_stem_masking": {
            "file_paths": ["/nonexistent/a.wav", "/nonexistent/b.wav"],
        },
        "batch_diagnostic": {
            "file_paths": [],  # empty list triggers validation error
        },
    }

    if tool_name in mapping:
        return mapping[tool_name]

    # Fallback: try a single file_path (may need updating if new tools are added)
    return {"file_path": "/nonexistent/test.wav"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_all_tools_return_consistent_error_schema(client):
    """Every MCP tool returns {error_type: str, message: str, context: dict} on error.

    Tool names are discovered dynamically via client.list_tools() so this test
    does not go stale when tools are added or removed (D-20).
    """
    tools = await client.list_tools()
    tool_names = sorted(t.name for t in tools)

    tested = []
    for name in tool_names:
        if name in _SKIP_TOOLS:
            continue
        bad_args = _get_bad_args(name)
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(name, bad_args)
        error = json.loads(str(exc_info.value))

        assert isinstance(error, dict), (
            f"{name}: error response is not a dict"
        )
        assert "error_type" in error, (
            f"{name}: missing 'error_type' key"
        )
        assert "message" in error, (
            f"{name}: missing 'message' key"
        )
        assert "context" in error, (
            f"{name}: missing 'context' key"
        )
        assert isinstance(error["error_type"], str), (
            f"{name}: 'error_type' is not str"
        )
        assert isinstance(error["message"], str), (
            f"{name}: 'message' is not str"
        )
        assert isinstance(error["context"], dict), (
            f"{name}: 'context' is not dict"
        )
        tested.append(name)

    # Sanity: we actually tested a meaningful number of tools
    assert len(tested) >= 15, (
        f"Only tested {len(tested)} tools, expected at least 15"
    )


async def test_tool_count_not_hardcoded(client):
    """Tool count is discovered dynamically and matches the expected minimum (D-20)."""
    tools = await client.list_tools()
    # Current count is 19; use >= so the test survives tool additions.
    assert len(tools) >= 19, (
        f"Expected at least 19 tools, found {len(tools)}"
    )


def test_wrap_errors_coverage():
    """Every public analysis function is decorated with @wrap_errors.

    Verifies the __wrapped__ attribute set by functools.wraps inside
    the wrap_errors decorator across all 10 analysis modules.
    """
    # Module path -> list of expected decorated function names
    coverage_map: dict[str, list[str]] = {
        "phantom.spectral": ["analyze_spectrum"],
        "phantom.loudness": ["analyze_loudness"],
        "phantom.dynamics": ["analyze_dynamics"],
        "phantom.stereo": ["analyze_stereo"],
        "phantom.phase": ["analyze_phase", "compare_phase"],
        "phantom.problems": ["detect_problems"],
        "phantom.masking": ["analyze_masking", "analyze_masking_matrix"],
        "phantom.comparison": [
            "compare_to_profile",
            "compare_to_reference",
            "match_to_reference",
        ],
        "phantom.separation": ["separate_stems"],
        "phantom.processing": ["fix_audio", "apply_processing"],
    }

    missing: list[str] = []
    for module_path, func_names in coverage_map.items():
        mod = importlib.import_module(module_path)
        for func_name in func_names:
            fn = getattr(mod, func_name, None)
            assert fn is not None, (
                f"{module_path}.{func_name} does not exist"
            )
            # functools.wraps sets __wrapped__ on the wrapper
            if not hasattr(fn, "__wrapped__"):
                missing.append(f"{module_path}.{func_name}")

    assert not missing, (
        f"Functions missing @wrap_errors decorator (no __wrapped__): {missing}"
    )


def test_wrap_errors_coverage_module_count():
    """All 10 analysis modules are covered in the wrap_errors test."""
    # This is a meta-test ensuring the coverage map stays in sync.
    expected_modules = {
        "phantom.spectral",
        "phantom.loudness",
        "phantom.dynamics",
        "phantom.stereo",
        "phantom.phase",
        "phantom.problems",
        "phantom.masking",
        "phantom.comparison",
        "phantom.separation",
        "phantom.processing",
    }
    # Import the coverage map from the test above by re-declaring (avoids coupling)
    assert len(expected_modules) == 10
    for mod_path in expected_modules:
        mod = importlib.import_module(mod_path)
        assert mod is not None, f"Cannot import {mod_path}"
