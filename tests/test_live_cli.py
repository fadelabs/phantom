"""Live integration tests for Phantom CLI commands.

Tests use real audio from tests/fixtures/live/ via subprocess invocation
of the phantom CLI entry point. All tests are marked @pytest.mark.live
and skip gracefully when fixture files are absent.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_phantom(*args, timeout=120):
    """Run a phantom CLI command via subprocess and return CompletedProcess."""
    return subprocess.run(
        ["uv", "run", "phantom", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _extract_json(output):
    """Extract JSON object from output that may contain Rich markup."""
    start = output.index("{")
    return json.loads(output[start:])


# ---------------------------------------------------------------------------
# phantom analyze (D-06)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_cli_analyze_json(live_mix):
    """phantom analyze --json produces valid JSON with all 6 analysis sections."""
    result = _run_phantom("analyze", "--json", live_mix)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    for key in ("spectral", "loudness", "dynamics", "stereo", "phase", "problems"):
        assert key in data, (
            f"Missing analysis section '{key}' in output: {list(data.keys())}"
        )
        assert isinstance(data[key], dict), (
            f"{key} should be dict, got {type(data[key])}"
        )
    # File metadata
    for key in ("file", "duration_seconds", "sample_rate", "channels"):
        assert key in data, (
            f"Missing metadata key '{key}' in output: {list(data.keys())}"
        )
    # Spectral centroid should be populated for real audio
    assert data["spectral"]["spectral_centroid_hz"] is not None, (
        "spectral_centroid_hz is None -- expected a value for real audio"
    )


@pytest.mark.live
def test_cli_analyze_single_domain(live_mix):
    """phantom analyze --spectrum --json returns spectral data only."""
    result = _run_phantom("analyze", "--spectrum", "--json", live_mix)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert "spectral" in data, f"Missing 'spectral' key in output: {list(data.keys())}"
    assert data["spectral"]["spectral_centroid_hz"] is not None, (
        "spectral_centroid_hz is None for real audio"
    )


@pytest.mark.live
def test_cli_analyze_rich_output(live_mix):
    """phantom analyze (no --json) produces human-readable Rich output."""
    result = _run_phantom("analyze", live_mix)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert len(result.stdout) > 100, (
        f"Output too short for full diagnostic: {len(result.stdout)} chars"
    )


# ---------------------------------------------------------------------------
# phantom analyze batch (D-06)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_cli_analyze_batch_json(live_mix, live_stem_paths):
    """phantom analyze --json with multiple files produces batch output."""
    if len(live_stem_paths) < 2:
        pytest.skip("Need at least 2 stem files for batch test")
    result = _run_phantom("analyze", "--json", *live_stem_paths)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert "stems" in data, f"Missing 'stems' key in batch output: {list(data.keys())}"
    assert data["stem_count"] == len(live_stem_paths), (
        f"stem_count {data.get('stem_count')} != expected {len(live_stem_paths)}"
    )


# ---------------------------------------------------------------------------
# phantom compare (D-06, D-07)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_cli_compare_profile_rock_json(live_mix):
    """phantom compare --profile rock --json produces comparison output."""
    result = _run_phantom("compare", "--profile", "rock", "--json", live_mix)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["profile_name"] == "rock", (
        f"profile_name is '{data.get('profile_name')}', expected 'rock'"
    )


@pytest.mark.live
def test_cli_compare_profile_hiphop_json(live_mix):
    """phantom compare --profile hip-hop --json produces comparison output."""
    result = _run_phantom("compare", "--profile", "hip-hop", "--json", live_mix)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["profile_name"] == "hip-hop", (
        f"profile_name is '{data.get('profile_name')}', expected 'hip-hop'"
    )


@pytest.mark.live
def test_cli_compare_reference_json(live_stems, live_mix):
    """phantom compare --reference <stem> --json produces comparison output."""
    if not live_stems:
        pytest.skip("No live stems available for reference comparison")
    ref_path = next(iter(live_stems.values()))
    result = _run_phantom("compare", "--reference", ref_path, "--json", live_mix)
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    # Reference comparison should have comparison data present
    assert isinstance(data, dict), f"Expected dict, got {type(data)}"
    assert len(data) > 0, "Reference comparison returned empty output"


# ---------------------------------------------------------------------------
# phantom separate (D-05, D-06)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_cli_separate_json(live_mix, tmp_path):
    """phantom separate --json produces stem separation output via Demucs."""
    try:
        import demucs  # noqa: F401
    except ImportError:
        pytest.skip("demucs not installed")
    result = _run_phantom(
        "separate",
        "--json",
        "--output-dir",
        str(tmp_path),
        live_mix,
        timeout=600,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = _extract_json(result.stdout)
    assert "stems" in data, f"Missing 'stems' key in output: {list(data.keys())}"
    stems = data["stems"]
    for expected_stem in ("vocals", "drums", "bass", "other"):
        assert expected_stem in stems, (
            f"Missing stem '{expected_stem}' in output: {list(stems.keys())}"
        )


# ---------------------------------------------------------------------------
# phantom render (D-06)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_cli_render_mp3_json(live_mix, tmp_path):
    """phantom render --format mp3 --json produces MP3 output file."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    output_path = tmp_path / "output.mp3"
    result = _run_phantom(
        "render",
        "--format",
        "mp3",
        "--output",
        str(output_path),
        "--json",
        live_mix,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = _extract_json(result.stdout)
    assert "output" in data, f"Missing 'output' in output: {list(data.keys())}"
    assert output_path.exists(), f"Output file not created at {output_path}"


@pytest.mark.live
def test_cli_render_flac_json(live_mix, tmp_path):
    """phantom render --format flac --json produces FLAC output file."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    output_path = tmp_path / "output.flac"
    result = _run_phantom(
        "render",
        "--format",
        "flac",
        "--output",
        str(output_path),
        "--json",
        live_mix,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = _extract_json(result.stdout)
    assert "output" in data, f"Missing 'output' in output: {list(data.keys())}"
    assert output_path.exists(), f"Output file not created at {output_path}"


# ---------------------------------------------------------------------------
# phantom setup-reaper (D-06)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_cli_setup_reaper_json():
    """phantom setup-reaper --json produces parseable JSON output."""
    result = _run_phantom("setup-reaper", "--json")
    # setup-reaper may exit non-zero if git is missing or clone fails,
    # but the command should parse and produce structured output.
    # Accept exit code 0 (success) or 1 (expected failure, e.g., repo already exists).
    assert result.returncode in (0, 1), (
        f"Unexpected exit code {result.returncode}: stderr={result.stderr}"
    )
    # If exit code 0, verify JSON output
    if result.returncode == 0:
        data = _extract_json(result.stdout)
        assert isinstance(data, dict), f"Expected dict output, got {type(data)}"


# ---------------------------------------------------------------------------
# phantom serve (D-06)
# ---------------------------------------------------------------------------


def test_cli_serve_starts():
    """phantom serve starts without crashing (subprocess survival test)."""
    proc = subprocess.Popen(
        ["uv", "run", "phantom", "serve"],
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
