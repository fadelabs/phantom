"""Live integration tests for Phantom MCP server tools.

Tests use real audio from tests/fixtures/live/ via FastMCP's in-memory
Client. All tests are marked @pytest.mark.live and skip gracefully
when fixture files are absent.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from fastmcp import Client
from phantom.server import mcp


# ---------------------------------------------------------------------------
# Plausible ranges for real audio (D-08)
# ---------------------------------------------------------------------------

PLAUSIBLE = {
    # Spectral
    "spectral_centroid_hz": (100, 12000),
    "spectral_rolloff_hz": (200, 22050),
    "spectral_flatness": (0.0, 1.0),
    "dissonance": (0.0, 1.0),
    # Loudness
    "integrated_lufs": (-60, 0),
    "true_peak_dbtp": (-60, 3),
    "loudness_range_lu": (0, 30),
    # Dynamics
    "rms_dbfs": (-60, 0),
    "peak_dbfs": (-60, 0),
    "crest_factor_db": (0, 40),
    "dynamic_range_db": (0, 60),
    # Stereo (for stereo files)
    "correlation": (-1.0, 1.0),
    "stereo_width": (0.0, 5.0),
    "balance_db": (-20, 20),
    # Phase
    "phase_correlation": (-1.0, 1.0),
}


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


def _data(result):
    """Extract the data dict from a CallToolResult."""
    return result.data


def _assert_in_range(value, key):
    """Assert a value is within the plausible range for its key."""
    if key in PLAUSIBLE and value is not None:
        lo, hi = PLAUSIBLE[key]
        assert lo <= value <= hi, f"{key}={value} outside plausible range [{lo}, {hi}]"


# ---------------------------------------------------------------------------
# Individual tool plausibility tests (D-04, D-08)
# ---------------------------------------------------------------------------


@pytest.mark.live
async def test_analyze_spectrum_live(client, live_mix):
    """analyze_spectrum returns plausible spectral results for real audio."""
    result = await client.call_tool("analyze_spectrum", {"file_path": live_mix})
    data = _data(result)
    assert data["spectral_centroid_hz"] is not None
    assert data["spectral_rolloff_hz"] is not None
    assert data["spectral_flatness"] is not None
    assert data["dissonance"] is not None
    assert data["octave_band_energy_db"] is not None
    _assert_in_range(data["spectral_centroid_hz"], "spectral_centroid_hz")
    _assert_in_range(data["spectral_rolloff_hz"], "spectral_rolloff_hz")
    _assert_in_range(data["spectral_flatness"], "spectral_flatness")
    _assert_in_range(data["dissonance"], "dissonance")


@pytest.mark.live
async def test_analyze_loudness_live(client, live_mix):
    """analyze_loudness returns plausible EBU R128 measurements for real audio."""
    result = await client.call_tool("analyze_loudness", {"file_path": live_mix})
    data = _data(result)
    assert data["integrated_lufs"] is not None
    assert data["true_peak_dbtp"] is not None
    assert data["loudness_range_lu"] is not None
    assert isinstance(data["short_term_lufs"], list)
    assert len(data["short_term_lufs"]) > 0
    _assert_in_range(data["integrated_lufs"], "integrated_lufs")
    _assert_in_range(data["true_peak_dbtp"], "true_peak_dbtp")
    _assert_in_range(data["loudness_range_lu"], "loudness_range_lu")


@pytest.mark.live
async def test_analyze_dynamics_live(client, live_mix):
    """analyze_dynamics returns plausible dynamics for real audio."""
    result = await client.call_tool("analyze_dynamics", {"file_path": live_mix})
    data = _data(result)
    assert data["rms_dbfs"] is not None
    assert data["peak_dbfs"] is not None
    assert data["crest_factor_db"] is not None
    assert data["dynamic_range_db"] is not None
    _assert_in_range(data["rms_dbfs"], "rms_dbfs")
    _assert_in_range(data["peak_dbfs"], "peak_dbfs")
    _assert_in_range(data["crest_factor_db"], "crest_factor_db")
    _assert_in_range(data["dynamic_range_db"], "dynamic_range_db")


@pytest.mark.live
async def test_analyze_stereo_live(client, live_mix):
    """analyze_stereo returns plausible stereo field data for real audio."""
    result = await client.call_tool("analyze_stereo", {"file_path": live_mix})
    data = _data(result)
    assert data["correlation"] is not None
    assert data["stereo_width"] is not None
    assert data["balance_db"] is not None
    _assert_in_range(data["correlation"], "correlation")
    _assert_in_range(data["stereo_width"], "stereo_width")
    _assert_in_range(data["balance_db"], "balance_db")


@pytest.mark.live
async def test_analyze_phase_live(client, live_mix):
    """analyze_phase returns plausible phase coherence for real audio."""
    result = await client.call_tool("analyze_phase", {"file_path": live_mix})
    data = _data(result)
    assert data["phase_correlation"] is not None
    assert isinstance(data["per_band_correlation"], dict)
    assert len(data["per_band_correlation"]) > 0
    _assert_in_range(data["phase_correlation"], "phase_correlation")


@pytest.mark.live
async def test_detect_problems_live(client, live_mix):
    """detect_problems returns structured results for real audio."""
    result = await client.call_tool("detect_problems", {"file_path": live_mix})
    data = _data(result)
    assert "problems" in data
    assert isinstance(data["problems"], list)
    assert "clean" in data
    assert isinstance(data["clean"], bool)
    assert "summary" in data
    assert isinstance(data["summary"], dict)


# ---------------------------------------------------------------------------
# Composite tool plausibility tests (D-08)
# ---------------------------------------------------------------------------


@pytest.mark.live
async def test_full_diagnostic_live(client, live_mix):
    """full_diagnostic returns all 6 sections and metadata for real audio."""
    result = await client.call_tool("full_diagnostic", {"file_path": live_mix})
    data = _data(result)
    # Metadata
    assert "file" in data
    assert "sample_rate" in data
    assert "channels" in data
    assert "duration_seconds" in data
    assert data["duration_seconds"] > 0
    # All 6 analysis sections present
    for section in ("spectral", "loudness", "dynamics", "stereo", "phase", "problems"):
        assert section in data, f"Missing section: {section}"
    # Plausibility check on spectral centroid
    assert data["spectral"]["spectral_centroid_hz"] is not None
    _assert_in_range(data["spectral"]["spectral_centroid_hz"], "spectral_centroid_hz")


@pytest.mark.live
async def test_batch_diagnostic_live(client, live_stem_paths):
    """batch_diagnostic returns per-stem results for all available stems."""
    if len(live_stem_paths) == 0:
        pytest.skip("No live stems available")
    result = await client.call_tool("batch_diagnostic", {"file_paths": live_stem_paths})
    data = _data(result)
    assert "stems" in data
    assert data["stem_count"] == len(live_stem_paths)
    stems = data["stems"]
    assert len(stems) == len(live_stem_paths)
    for stem_key, stem_data in stems.items():
        # Each stem should have all 6 sections (unless it errored)
        if "error" not in stem_data:
            for section in (
                "spectral",
                "loudness",
                "dynamics",
                "stereo",
                "phase",
                "problems",
            ):
                assert section in stem_data, (
                    f"Stem {stem_key} missing section: {section}"
                )


@pytest.mark.live
async def test_multi_stem_masking_live(client, live_stem_paths):
    """multi_stem_masking returns masking pairs for real stems."""
    if len(live_stem_paths) < 2:
        pytest.skip("Need at least 2 live stems for masking analysis")
    result = await client.call_tool(
        "multi_stem_masking", {"file_paths": live_stem_paths}
    )
    data = _data(result)
    assert "pairs" in data
    assert isinstance(data["pairs"], list)
    assert len(data["pairs"]) > 0
    for pair in data["pairs"]:
        assert "overall_severity" in pair
        assert "bands" in pair


# ---------------------------------------------------------------------------
# Cross-tool consistency tests (D-09) -- HIGHEST VALUE
# ---------------------------------------------------------------------------


@pytest.mark.live
async def test_full_diagnostic_matches_individual_tools(client, live_mix):
    """full_diagnostic sections must match running each tool individually."""
    full = _data(await client.call_tool("full_diagnostic", {"file_path": live_mix}))

    # Run each tool individually on the same file
    spectrum = _data(
        await client.call_tool("analyze_spectrum", {"file_path": live_mix})
    )
    loudness = _data(
        await client.call_tool("analyze_loudness", {"file_path": live_mix})
    )
    dynamics = _data(
        await client.call_tool("analyze_dynamics", {"file_path": live_mix})
    )
    stereo = _data(await client.call_tool("analyze_stereo", {"file_path": live_mix}))
    phase = _data(await client.call_tool("analyze_phase", {"file_path": live_mix}))
    problems = _data(await client.call_tool("detect_problems", {"file_path": live_mix}))

    # Strict equality -- Pydantic models round values deterministically
    assert full["spectral"] == spectrum, "spectral section mismatch"
    assert full["loudness"] == loudness, "loudness section mismatch"
    assert full["dynamics"] == dynamics, "dynamics section mismatch"
    assert full["stereo"] == stereo, "stereo section mismatch"
    assert full["phase"] == phase, "phase section mismatch"
    assert full["problems"] == problems, "problems section mismatch"


@pytest.mark.live
async def test_batch_diagnostic_matches_single_file(client, live_stem_paths):
    """batch_diagnostic per-stem result must match full_diagnostic on the same file."""
    if len(live_stem_paths) == 0:
        pytest.skip("No live stems available")

    # Use the first available stem
    stem_path = live_stem_paths[0]

    batch = _data(
        await client.call_tool("batch_diagnostic", {"file_paths": [stem_path]})
    )
    full = _data(await client.call_tool("full_diagnostic", {"file_path": stem_path}))

    # The batch result stores results keyed by file path
    stem_result = batch["stems"][stem_path]

    # Compare each analysis section
    for section in ("spectral", "loudness", "dynamics", "stereo", "phase", "problems"):
        assert stem_result[section] == full[section], (
            f"batch_diagnostic[{section}] != full_diagnostic[{section}]"
        )


# ---------------------------------------------------------------------------
# Optional dependency tools (D-05)
# ---------------------------------------------------------------------------


@pytest.mark.live
async def test_separate_stems_live(client, live_mix, tmp_path):
    """separate_stems produces stem files from real audio via Demucs."""
    try:
        import demucs  # noqa: F401
    except ImportError:
        pytest.skip("demucs not installed")

    output_dir = str(tmp_path / "stems")
    os.makedirs(output_dir, exist_ok=True)
    result = await client.call_tool(
        "separate_stems",
        {"file_path": live_mix, "output_dir": output_dir},
    )
    data = _data(result)
    assert "stems" in data
    stems = data["stems"]
    # Demucs htdemucs model produces at least these 4 stems
    for expected in ("vocals", "drums", "bass", "other"):
        assert expected in stems, f"Missing stem: {expected}"
        assert isinstance(stems[expected], str)
        assert Path(stems[expected]).exists(), f"Stem file not found: {stems[expected]}"


@pytest.mark.live
async def test_match_to_reference_live(client, live_mix, live_stems, tmp_path):
    """match_to_reference produces matched output from real audio via Matchering."""
    try:
        import matchering  # noqa: F401
    except ImportError:
        pytest.skip("matchering not installed")

    if not live_stems:
        pytest.skip("No live stems available for reference matching")

    # Use the first available stem as target, mix as reference
    target_path = list(live_stems.values())[0]
    output_path = str(tmp_path / "matched.wav")

    result = await client.call_tool(
        "match_to_reference",
        {
            "target_path": target_path,
            "reference_path": live_mix,
            "output_path": output_path,
        },
    )
    data = _data(result)
    assert "output_path" in data
    assert Path(data["output_path"]).exists(), "Matched output file not created"


# ---------------------------------------------------------------------------
# Profile comparison tests (D-07)
# ---------------------------------------------------------------------------


@pytest.mark.live
async def test_compare_to_profile_rock(client, live_mix):
    """compare_to_profile returns deviation data against rock profile."""
    result = await client.call_tool(
        "compare_to_profile", {"file_path": live_mix, "profile_name": "rock"}
    )
    data = _data(result)
    assert "loudness" in data
    assert "frequency" in data
    assert "dynamics" in data
    assert "stereo" in data


@pytest.mark.live
async def test_compare_to_profile_hiphop(client, live_mix):
    """compare_to_profile returns deviation data against hip-hop profile."""
    result = await client.call_tool(
        "compare_to_profile", {"file_path": live_mix, "profile_name": "hip-hop"}
    )
    data = _data(result)
    assert "loudness" in data
    assert "frequency" in data
    assert "dynamics" in data
    assert "stereo" in data


@pytest.mark.live
async def test_compare_to_profile_ambient(client, live_mix):
    """compare_to_profile returns deviation data against ambient profile."""
    result = await client.call_tool(
        "compare_to_profile", {"file_path": live_mix, "profile_name": "ambient"}
    )
    data = _data(result)
    assert "loudness" in data
    assert "frequency" in data
    assert "dynamics" in data
    assert "stereo" in data


@pytest.mark.live
async def test_compare_to_reference_live(client, live_mix, live_stems):
    """compare_to_reference returns deviation data against a real stem."""
    if not live_stems:
        pytest.skip("No live stems available for reference comparison")

    reference_path = list(live_stems.values())[0]
    result = await client.call_tool(
        "compare_to_reference",
        {"file_path": live_mix, "reference_path": reference_path},
    )
    data = _data(result)
    assert "loudness" in data
    assert "frequency" in data
    assert "dynamics" in data
    assert "stereo" in data
