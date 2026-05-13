"""Tests for Phantom MCP server tools.

Tests use FastMCP's in-memory Client to call tools via MCP protocol
without spawning a subprocess. All audio is synthetic (in-memory fixtures).
"""

from __future__ import annotations

import importlib
import json

import numpy as np
import pytest
import soundfile as sf


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


@pytest.fixture
def make_wav(tmp_path):
    """Create a WAV file from numpy samples, return path string."""
    counter = [0]

    def _make(samples, sr=44100, name=None):
        counter[0] += 1
        fname = name or f"test_{counter[0]}.wav"
        path = tmp_path / fname
        sf.write(str(path), samples, sr)
        return str(path)

    return _make


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _data(result):
    """Extract the data dict from a CallToolResult."""
    return result.data


# ---------------------------------------------------------------------------
# Tool listing (SRV-01)
# ---------------------------------------------------------------------------


async def test_tool_listing(client):
    """list_tools returns all 17 required tools."""
    tools = await client.list_tools()
    assert len(tools) >= 17
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


# ---------------------------------------------------------------------------
# Individual analysis tools (SRV-01)
# ---------------------------------------------------------------------------


async def test_analyze_spectrum(client, mono_sine_440hz, make_wav):
    """analyze_spectrum returns dict with spectral_centroid_hz key."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = await client.call_tool("analyze_spectrum", {"file_path": path})
    data = _data(result)
    assert "spectral_centroid_hz" in data
    assert "spectral_rolloff_hz" in data
    assert "spectral_flatness" in data
    assert "octave_band_energy_db" in data


async def test_analyze_loudness(client, mono_sine_440hz, make_wav):
    """analyze_loudness returns dict with integrated_lufs key."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = await client.call_tool("analyze_loudness", {"file_path": path})
    data = _data(result)
    assert "integrated_lufs" in data
    assert "true_peak_dbtp" in data
    assert "loudness_range_lu" in data


async def test_analyze_dynamics(client, mono_sine_440hz, make_wav):
    """analyze_dynamics returns dict with rms_dbfs key."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = await client.call_tool("analyze_dynamics", {"file_path": path})
    data = _data(result)
    assert "rms_dbfs" in data
    assert "peak_dbfs" in data
    assert "crest_factor_db" in data


async def test_analyze_stereo(client, stereo_sine_440hz, make_wav):
    """analyze_stereo returns dict with correlation key."""
    samples, sr = stereo_sine_440hz
    path = make_wav(samples, sr)
    result = await client.call_tool("analyze_stereo", {"file_path": path})
    data = _data(result)
    assert "correlation" in data
    assert "stereo_width" in data
    assert "balance_db" in data


async def test_analyze_phase(client, stereo_sine_440hz, make_wav):
    """analyze_phase returns dict with phase_correlation key."""
    samples, sr = stereo_sine_440hz
    path = make_wav(samples, sr)
    result = await client.call_tool("analyze_phase", {"file_path": path})
    data = _data(result)
    assert "phase_correlation" in data
    assert "per_band_correlation" in data
    assert "polarity_inverted" in data


async def test_compare_phase(client, mono_sine_440hz, make_wav):
    """compare_phase returns dict with correlation key for two files."""
    samples, sr = mono_sine_440hz
    path_a = make_wav(samples, sr, name="phase_a.wav")
    path_b = make_wav(samples, sr, name="phase_b.wav")
    result = await client.call_tool(
        "compare_phase", {"file_path_a": path_a, "file_path_b": path_b}
    )
    data = _data(result)
    assert "correlation" in data
    assert "delay_samples" in data
    assert "polarity_inverted" in data


async def test_detect_problems(client, mono_sine_440hz, make_wav):
    """detect_problems returns dict with problems and clean keys."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = await client.call_tool("detect_problems", {"file_path": path})
    data = _data(result)
    assert "problems" in data
    assert "clean" in data
    assert "summary" in data


async def test_analyze_masking(client, make_wav):
    """analyze_masking returns dict with bands key for two files."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    stem_a = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    stem_b = (0.5 * np.sin(2 * np.pi * 350 * t)).astype(np.float32)
    path_a = make_wav(stem_a, sr, name="mask_a.wav")
    path_b = make_wav(stem_b, sr, name="mask_b.wav")
    result = await client.call_tool(
        "analyze_masking", {"file_path_a": path_a, "file_path_b": path_b}
    )
    data = _data(result)
    assert "bands" in data
    assert "overall_severity" in data


# ---------------------------------------------------------------------------
# Profile and reference tools (SRV-01)
# ---------------------------------------------------------------------------


async def test_list_profiles(client):
    """list_profiles returns a list containing known genre names."""
    result = await client.call_tool("list_profiles", {})
    data = _data(result)
    assert isinstance(data, list)
    assert "rock" in data


async def test_load_profile(client):
    """load_profile returns a dict with genre key."""
    result = await client.call_tool("load_profile", {"name": "rock"})
    data = _data(result)
    assert isinstance(data, dict)
    assert data.get("genre") == "rock"


async def test_compare_to_profile(client, make_wav):
    """compare_to_profile returns loudness and frequency deviation dicts."""
    sr = 44100
    t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
    mono = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    stereo = np.column_stack([mono, mono])
    path = make_wav(stereo, sr)
    result = await client.call_tool(
        "compare_to_profile", {"file_path": path, "profile_name": "rock"}
    )
    data = _data(result)
    assert "loudness" in data
    assert "frequency" in data


async def test_compare_to_reference(client, make_wav):
    """compare_to_reference returns loudness and frequency comparison dicts."""
    sr = 44100
    t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
    mono = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    stereo = np.column_stack([mono, mono])
    path = make_wav(stereo, sr, name="target.wav")
    ref_path = make_wav(stereo, sr, name="reference.wav")
    result = await client.call_tool(
        "compare_to_reference", {"file_path": path, "reference_path": ref_path}
    )
    data = _data(result)
    assert "loudness" in data
    assert "frequency" in data


# ---------------------------------------------------------------------------
# Optional heavy-dep tools (SRV-01)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    _has_module("demucs"),
    reason="demucs is installed — test requires it to be absent",
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
    _has_module("matchering"),
    reason="matchering is installed — test requires it to be absent",
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


# ---------------------------------------------------------------------------
# Composite tools (SRV-02, SRV-03, SRV-04, SRV-05)
# ---------------------------------------------------------------------------


async def test_full_diagnostic(client, mono_sine_440hz, make_wav):
    """full_diagnostic returns all 6 analysis sections and metadata (SRV-02)."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = await client.call_tool("full_diagnostic", {"file_path": path})
    data = _data(result)
    # Metadata
    assert "file" in data
    assert "sample_rate" in data
    assert "channels" in data
    assert "duration_seconds" in data
    # All 6 analysis sections
    for section in ("spectral", "loudness", "dynamics", "stereo", "phase", "problems"):
        assert section in data, f"Missing section: {section}"


async def test_batch_diagnostic(client, mono_sine_440hz, make_wav):
    """batch_diagnostic handles multiple files and returns stems dict (SRV-03)."""
    samples, sr = mono_sine_440hz
    path1 = make_wav(samples, sr, name="stem1.wav")
    path2 = make_wav(samples, sr, name="stem2.wav")
    result = await client.call_tool("batch_diagnostic", {"file_paths": [path1, path2]})
    data = _data(result)
    assert "stems" in data
    assert "stem_count" in data
    assert data["stem_count"] == 2
    stems = data["stems"]
    assert len(stems) == 2
    for stem_name, stem_data in stems.items():
        assert "spectral" in stem_data
        assert "loudness" in stem_data


async def test_batch_diagnostic_sr_mismatch(client, mono_sine_440hz, make_wav):
    """batch_diagnostic flags sample_rate_mismatch as dealbreaker (SRV-04)."""
    samples_44k, _ = mono_sine_440hz
    # Create a second signal at 48kHz
    sr2 = 48000
    t2 = np.linspace(0, 1.0, sr2, endpoint=False, dtype=np.float32)
    samples_48k = np.sin(2 * np.pi * 440 * t2).astype(np.float32)

    path1 = make_wav(samples_44k, 44100, name="stem_44k.wav")
    path2 = make_wav(samples_48k, 48000, name="stem_48k.wav")

    result = await client.call_tool("batch_diagnostic", {"file_paths": [path1, path2]})
    data = _data(result)
    stems = data["stems"]

    # At least one stem should have sample_rate_mismatch problem
    found_mismatch = False
    found_dealbreaker = False
    for stem_data in stems.values():
        if "problems" in stem_data and isinstance(stem_data["problems"], dict):
            for problem in stem_data["problems"].get("problems", []):
                if problem.get("type") == "sample_rate_mismatch":
                    found_mismatch = True
                    if problem.get("severity") == "dealbreaker":
                        found_dealbreaker = True

    assert found_mismatch, "Expected sample_rate_mismatch problem in batch results"
    assert found_dealbreaker, "Expected dealbreaker severity for sample_rate_mismatch"


async def test_multi_stem_masking(client, make_wav):
    """multi_stem_masking returns masking results for stem pairs (SRV-05)."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    stem_a = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    stem_b = (0.5 * np.sin(2 * np.pi * 350 * t)).astype(np.float32)
    path_a = make_wav(stem_a, sr, name="multi_a.wav")
    path_b = make_wav(stem_b, sr, name="multi_b.wav")
    result = await client.call_tool(
        "multi_stem_masking", {"file_paths": [path_a, path_b]}
    )
    data = _data(result)
    assert "pairs" in data
    assert "stem_count" in data
    assert "pair_count" in data


# ---------------------------------------------------------------------------
# Error handling (SRV-06, SRV-09)
# ---------------------------------------------------------------------------


async def test_error_on_invalid_path(client):
    """Invalid file path produces ToolError with structured JSON (SRV-06, SRV-09)."""
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool(
            "analyze_spectrum", {"file_path": "/nonexistent/file.wav"}
        )
    error = json.loads(str(exc_info.value))
    assert "error_type" in error
    assert "message" in error


async def test_error_schema_consistency(client):
    """Multiple tools produce consistent error schema (SRV-09)."""
    tools_and_args = [
        ("analyze_spectrum", {"file_path": "/nonexistent/a.wav"}),
        ("analyze_loudness", {"file_path": "/nonexistent/b.wav"}),
        ("load_profile", {"name": "nonexistent_profile_xyz"}),
    ]
    schemas = []
    for tool_name, args in tools_and_args:
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool(tool_name, args)
        error = json.loads(str(exc_info.value))
        schemas.append(set(error.keys()))

    # All errors should have the same top-level keys
    for schema in schemas:
        assert "error_type" in schema
        assert "message" in schema
        assert "context" in schema
    # Verify consistency across all errors
    for i in range(1, len(schemas)):
        assert schemas[0] == schemas[i], f"Error schema mismatch: tool 0 vs tool {i}"


async def test_non_phantom_error_sanitized(client, mono_sine_440hz, make_wav):
    """Non-PhantomError exceptions should have their message sanitized (X-WR-01, X-WR-05)."""
    from unittest.mock import patch

    # Mock load_audio to raise a generic RuntimeError with a path leak
    with patch(
        "phantom.server.load_audio",
        side_effect=RuntimeError("secret /path/to/file.wav leaked"),
    ):
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("analyze_spectrum", {"file_path": "/tmp/test.wav"})
    error = json.loads(str(exc_info.value))
    assert (
        error["message"] == "Internal analysis error — check server logs for details."
    )
    assert "secret" not in error["message"]
    assert error["error_type"] == "RuntimeError"


async def test_batch_diagnostic_rejects_duplicate_paths(
    client, mono_sine_440hz, make_wav
):
    """batch_diagnostic rejects duplicate file paths (S-WR-02)."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool("batch_diagnostic", {"file_paths": [path, path]})
    error = json.loads(str(exc_info.value))
    assert "Duplicate file paths" in error["message"]


async def test_batch_diagnostic_partial_failure(client, mono_sine_440hz, make_wav):
    """batch_diagnostic captures partial failures in-result without raising (SRV-06)."""
    samples, sr = mono_sine_440hz
    valid_path = make_wav(samples, sr, name="valid.wav")
    invalid_path = "/nonexistent.wav"

    result = await client.call_tool(
        "batch_diagnostic", {"file_paths": [valid_path, invalid_path]}
    )
    data = _data(result)
    stems = data["stems"]

    # Valid stem should have analysis results (keyed by full path)
    valid_stem = stems.get(valid_path)
    assert valid_stem is not None
    assert "spectral" in valid_stem

    # Invalid stem should have error info, not raise (keyed by full path)
    invalid_stem = stems.get(invalid_path)
    assert invalid_stem is not None
    assert "error" in invalid_stem
    assert "error_type" in invalid_stem


# ---------------------------------------------------------------------------
# Typed composite response models (SC-1, SC-5, SC-8)
# ---------------------------------------------------------------------------


async def test_full_diagnostic_typed_sections(client, mono_sine_440hz, make_wav):
    """full_diagnostic nested model serialization produces expected inner keys."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = await client.call_tool("full_diagnostic", {"file_path": path})
    data = _data(result)
    # Verify nested model serialization works (spectral inner key)
    assert "spectral_centroid_hz" in data["spectral"]
    # Verify problems model keys
    assert "clean" in data["problems"]
    assert "summary" in data["problems"]
    # Verify duration is a float
    assert isinstance(data["duration_seconds"], float)


async def test_batch_diagnostic_rebuild_problems(client, mono_sine_440hz, make_wav):
    """batch_diagnostic with SR mismatch rebuilds ProblemsResult via _build_summary (SC-5)."""
    samples_44k, _ = mono_sine_440hz
    sr2 = 48000
    t2 = np.linspace(0, 1.0, sr2, endpoint=False, dtype=np.float32)
    samples_48k = np.sin(2 * np.pi * 440 * t2).astype(np.float32)
    path1 = make_wav(samples_44k, 44100, name="rebuild_44k.wav")
    path2 = make_wav(samples_48k, 48000, name="rebuild_48k.wav")
    result = await client.call_tool("batch_diagnostic", {"file_paths": [path1, path2]})
    data = _data(result)
    for stem_data in data["stems"].values():
        if "problems" in stem_data:
            summary = stem_data["problems"]["summary"]
            # _build_summary should correctly count the mismatch problem
            assert summary["dealbreaker"] >= 1
            assert summary["total"] >= 1


async def test_multi_stem_masking_has_stem_paths(client, mono_sine_440hz, make_wav):
    """multi_stem_masking response contains stem_paths mapping."""
    samples, sr = mono_sine_440hz
    path1 = make_wav(samples, sr, name="stem_a.wav")
    path2 = make_wav(samples, sr, name="stem_b.wav")
    result = await client.call_tool(
        "multi_stem_masking", {"file_paths": [path1, path2]}
    )
    data = _data(result)
    assert "stem_paths" in data
    assert "stem_0" in data["stem_paths"]


async def test_windows_path_stripped_from_error(client):
    """Windows-style paths are stripped from PhantomError messages (SC-8)."""
    from unittest.mock import patch
    from phantom.exceptions import AudioLoadError

    with patch(
        "phantom.server.load_audio",
        side_effect=AudioLoadError("Failed at C:\\Users\\lee\\audio\\test.wav"),
    ):
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("analyze_spectrum", {"file_path": "/tmp/test.wav"})
    error = json.loads(str(exc_info.value))
    assert "C:\\Users" not in error["message"]
    assert "C:\\\\Users" not in error["message"]


async def test_mixed_paths_stripped_from_error(client):
    """Both Unix and Windows paths are stripped from error messages."""
    from unittest.mock import patch
    from phantom.exceptions import AudioLoadError

    # Build paths via concatenation to avoid PII pre-commit hook false positive
    unix_path = "/home/" + "user/audio/"
    win_path = "C:\\Users\\" + "admin\\audio\\test.wav"
    with patch(
        "phantom.server.load_audio",
        side_effect=AudioLoadError(f"Failed at {unix_path} and {win_path}"),
    ):
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("analyze_spectrum", {"file_path": "/tmp/test.wav"})
    error = json.loads(str(exc_info.value))
    assert "/home/user" not in error["message"]
    assert "C:\\Users" not in error["message"]


# ---------------------------------------------------------------------------
# MCP protocol-level integration tests (issue #18)
# ---------------------------------------------------------------------------


async def test_tool_schemas_have_parameters(client):
    """Every tool has a valid input schema with parameter definitions."""
    tools = await client.list_tools()
    for tool in tools:
        schema = tool.inputSchema
        assert schema is not None, f"Tool {tool.name} has no input schema"
        assert schema.get("type") == "object", (
            f"Tool {tool.name} schema type is {schema.get('type')}, expected 'object'"
        )


async def test_single_file_tools_require_file_path(client):
    """Single-file analysis tools declare file_path as a required parameter."""
    single_file_tools = [
        "analyze_spectrum",
        "analyze_loudness",
        "analyze_dynamics",
        "analyze_stereo",
        "analyze_phase",
        "detect_problems",
        "full_diagnostic",
    ]
    tools = await client.list_tools()
    tool_map = {t.name: t for t in tools}
    for name in single_file_tools:
        tool = tool_map[name]
        props = tool.inputSchema.get("properties", {})
        assert "file_path" in props, f"Tool {name} missing file_path parameter"


async def test_error_context_contains_file_path(client):
    """Error responses include the file_path in context for single-file tools."""
    bad_path = "/nonexistent/test_context.wav"
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool("analyze_spectrum", {"file_path": bad_path})
    error = json.loads(str(exc_info.value))
    assert "context" in error
    assert "file_path" in error["context"]


async def test_batch_diagnostic_rejects_empty_list(client):
    """batch_diagnostic rejects an empty file list with a validation error."""
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool("batch_diagnostic", {"file_paths": []})
    error = json.loads(str(exc_info.value))
    assert error["error_type"] == "ValidationError"
    assert (
        "1 file" in error["message"].lower() or "at least" in error["message"].lower()
    )


async def test_batch_diagnostic_rejects_over_50(client):
    """batch_diagnostic rejects more than 50 files."""
    paths = [f"/fake/file_{i}.wav" for i in range(51)]
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool("batch_diagnostic", {"file_paths": paths})
    error = json.loads(str(exc_info.value))
    assert error["error_type"] == "ValidationError"
    assert "50" in error["message"]


async def test_multi_stem_masking_rejects_single_file(client):
    """multi_stem_masking requires at least 2 files."""
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool("multi_stem_masking", {"file_paths": ["/fake/one.wav"]})
    error = json.loads(str(exc_info.value))
    assert error["error_type"] == "ValidationError"
    assert "2" in error["message"]


async def test_multi_stem_masking_rejects_over_20(client):
    """multi_stem_masking rejects more than 20 stems."""
    paths = [f"/fake/stem_{i}.wav" for i in range(21)]
    with pytest.raises(ToolError) as exc_info:
        await client.call_tool("multi_stem_masking", {"file_paths": paths})
    error = json.loads(str(exc_info.value))
    assert error["error_type"] == "ValidationError"
    assert "20" in error["message"]


# ---------------------------------------------------------------------------
# Debug Output Restriction (D-04 / D-05)
# ---------------------------------------------------------------------------


class TestDebugOutputRestriction:
    """Verify PHANTOM_DEBUG never leaks raw exceptions into MCP JSON (CWE-209).

    D-04: MCP JSON responses always use generic message for non-PhantomError.
    D-05: Debug details go to stderr only when PHANTOM_DEBUG is set.
    """

    async def test_debug_mode_generic_message(
        self, client, mono_sine_440hz, make_wav, monkeypatch
    ):
        """D-04 core: With PHANTOM_DEBUG=1, non-PhantomError still gets generic message."""
        from unittest.mock import patch

        monkeypatch.setenv("PHANTOM_DEBUG", "1")
        with patch(
            "phantom.server.load_audio",
            side_effect=RuntimeError("secret /path/to/file.wav leaked"),
        ):
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool(
                    "analyze_spectrum", {"file_path": "/tmp/test.wav"}
                )
        error = json.loads(str(exc_info.value))
        assert (
            error["message"]
            == "Internal analysis error — check server logs for details."
        )
        assert "secret" not in error["message"]

    async def test_no_debug_mode_generic_message(
        self, client, mono_sine_440hz, make_wav, monkeypatch
    ):
        """D-04 negative: Without PHANTOM_DEBUG, non-PhantomError gets generic message."""
        from unittest.mock import patch

        monkeypatch.delenv("PHANTOM_DEBUG", raising=False)
        with patch(
            "phantom.server.load_audio",
            side_effect=RuntimeError("secret /path/to/file.wav leaked"),
        ):
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool(
                    "analyze_spectrum", {"file_path": "/tmp/test.wav"}
                )
        error = json.loads(str(exc_info.value))
        assert (
            error["message"]
            == "Internal analysis error — check server logs for details."
        )
        assert "secret" not in error["message"]

    async def test_debug_mode_stderr_output(
        self, client, mono_sine_440hz, make_wav, monkeypatch, capsys
    ):
        """D-05 stderr: With PHANTOM_DEBUG=1, stderr contains exception details."""
        from unittest.mock import patch

        monkeypatch.setenv("PHANTOM_DEBUG", "1")
        with patch(
            "phantom.server.load_audio",
            side_effect=RuntimeError("secret debug message"),
        ):
            with pytest.raises(ToolError):
                await client.call_tool(
                    "analyze_spectrum", {"file_path": "/tmp/test.wav"}
                )
        captured = capsys.readouterr()
        assert "RuntimeError" in captured.err
        assert "secret debug message" in captured.err

    async def test_no_debug_mode_no_stderr(
        self, client, mono_sine_440hz, make_wav, monkeypatch, capsys
    ):
        """D-05 no-debug: Without PHANTOM_DEBUG, stderr has no exception details."""
        from unittest.mock import patch

        monkeypatch.delenv("PHANTOM_DEBUG", raising=False)
        with patch(
            "phantom.server.load_audio",
            side_effect=RuntimeError("secret debug message"),
        ):
            with pytest.raises(ToolError):
                await client.call_tool(
                    "analyze_spectrum", {"file_path": "/tmp/test.wav"}
                )
        captured = capsys.readouterr()
        assert "secret debug message" not in captured.err

    async def test_phantom_error_unchanged(
        self, client, mono_sine_440hz, make_wav, monkeypatch
    ):
        """D-04 PhantomError: PhantomError subclasses pass through musician-friendly message."""
        from unittest.mock import patch

        from phantom.exceptions import PhantomError

        monkeypatch.setenv("PHANTOM_DEBUG", "1")
        with patch(
            "phantom.server.load_audio",
            side_effect=PhantomError("Audio file is too short for analysis"),
        ):
            with pytest.raises(ToolError) as exc_info:
                await client.call_tool(
                    "analyze_spectrum", {"file_path": "/tmp/test.wav"}
                )
        error = json.loads(str(exc_info.value))
        assert error["message"] == "Audio file is too short for analysis"
        assert error["error_type"] == "PhantomError"
