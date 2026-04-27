"""Tests for phantom analyze CLI command.

Covers single file full diagnostic, batch mode with sample rate mismatch
detection, JSON output, narrowing flags, error handling, and flag combinations.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
import soundfile as sf

from click.testing import CliRunner
from phantom.cli import cli


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def make_wav(tmp_path):
    counter = [0]

    def _make(samples, sr=44100, name=None):
        counter[0] += 1
        fname = name or f"test_{counter[0]}.wav"
        path = tmp_path / fname
        sf.write(str(path), samples, sr)
        return str(path)

    return _make


# ---------------------------------------------------------------------------
# Single file: full diagnostic
# ---------------------------------------------------------------------------


def test_analyze_full_diagnostic(runner, mono_sine_440hz, make_wav):
    """phantom analyze file.wav runs full diagnostic with Rich output."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    # Full diagnostic renders multiple analysis sections
    # At least some analysis content should appear
    assert len(result.output) > 100, "Output too short for full diagnostic"


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_analyze_json_output(runner, mono_sine_440hz, make_wav):
    """phantom analyze --json outputs valid JSON with all 6 analysis keys."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "--json", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "spectral" in data
    assert "loudness" in data
    assert "dynamics" in data
    assert "stereo" in data
    assert "phase" in data
    assert "problems" in data
    # Each should be a dict (model_dump output)
    for key in ("spectral", "loudness", "dynamics", "stereo", "phase", "problems"):
        assert isinstance(data[key], dict), (
            f"{key} should be a dict, got {type(data[key])}"
        )
    # File metadata
    assert "file" in data
    assert "duration_seconds" in data
    assert "sample_rate" in data
    assert "channels" in data


def test_analyze_json_flag_short(runner, mono_sine_440hz, make_wav):
    """phantom analyze -j uses short flag for JSON output."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "-j", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "spectral" in data
    assert "loudness" in data


# ---------------------------------------------------------------------------
# Narrowing flags
# ---------------------------------------------------------------------------


def test_analyze_spectrum_only(runner, mono_sine_440hz, make_wav):
    """--spectrum narrows to spectral analysis only."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "--spectrum", "--json", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "spectral" in data
    assert "loudness" not in data
    assert "dynamics" not in data
    assert "stereo" not in data
    assert "phase" not in data
    assert "problems" not in data


def test_analyze_loudness_only(runner, mono_sine_440hz, make_wav):
    """--loudness narrows to loudness analysis only."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "--loudness", "--json", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "loudness" in data
    assert "spectral" not in data


def test_analyze_problems_only(runner, mono_sine_440hz, make_wav):
    """--problems narrows to problem detection only."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "--problems", "--json", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "problems" in data
    assert "spectral" not in data
    assert "loudness" not in data


def test_analyze_dynamics_only(runner, mono_sine_440hz, make_wav):
    """--dynamics narrows to dynamics analysis only."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "--dynamics", "--json", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "dynamics" in data
    assert "spectral" not in data
    assert "loudness" not in data
    assert "stereo" not in data
    assert "phase" not in data
    assert "problems" not in data


def test_analyze_stereo_only(runner, mono_sine_440hz, make_wav):
    """--stereo narrows to stereo field analysis only."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "--stereo", "--json", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "stereo" in data
    assert "spectral" not in data
    assert "loudness" not in data
    assert "dynamics" not in data
    assert "phase" not in data
    assert "problems" not in data


def test_analyze_phase_only(runner, mono_sine_440hz, make_wav):
    """--phase narrows to phase coherence analysis only."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "--phase", "--json", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "phase" in data
    assert "spectral" not in data
    assert "loudness" not in data
    assert "dynamics" not in data
    assert "stereo" not in data
    assert "problems" not in data


def test_analyze_multiple_flags(runner, mono_sine_440hz, make_wav):
    """Multiple narrowing flags combine: --spectrum --loudness gives both."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["analyze", "--spectrum", "--loudness", "--json", path])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "spectral" in data
    assert "loudness" in data
    assert "dynamics" not in data
    assert "stereo" not in data
    assert "phase" not in data


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------


def test_analyze_batch_mode(runner, mono_sine_440hz, make_wav):
    """Multiple files trigger batch mode with stems dict."""
    samples, sr = mono_sine_440hz
    path1 = make_wav(samples, sr, name="vocals.wav")
    path2 = make_wav(samples, sr, name="drums.wav")
    result = runner.invoke(cli, ["analyze", "--json", path1, path2])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "stems" in data
    assert "stem_count" in data
    assert data["stem_count"] == 2
    assert len(data["stems"]) == 2
    assert "vocals.wav" in data["stems"]
    assert "drums.wav" in data["stems"]


def test_analyze_batch_sample_rate_mismatch(runner, make_wav):
    """Batch mode detects sample rate mismatch across stems."""
    sr1 = 44100
    sr2 = 48000
    t1 = np.linspace(0, 1.0, sr1, endpoint=False, dtype=np.float32)
    t2 = np.linspace(0, 1.0, sr2, endpoint=False, dtype=np.float32)
    samples1 = np.sin(2 * np.pi * 440 * t1).astype(np.float32)
    samples2 = np.sin(2 * np.pi * 440 * t2).astype(np.float32)

    path1 = make_wav(samples1, sr1, name="track_44k.wav")
    path2 = make_wav(samples2, sr2, name="track_48k.wav")

    result = runner.invoke(cli, ["analyze", path1, path2])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    output_lower = result.output.lower()
    # The mismatch warning should appear
    assert "mismatch" in output_lower or "sample rate" in output_lower, (
        f"Expected sample rate mismatch warning in output:\n{result.output}"
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_analyze_invalid_path(runner):
    """Non-existent file path produces non-zero exit code."""
    result = runner.invoke(cli, ["analyze", "/nonexistent/path/file.wav"])
    assert result.exit_code != 0


def test_analyze_no_files(runner):
    """No files argument produces non-zero exit code (click requires at least one)."""
    result = runner.invoke(cli, ["analyze"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Batch mode JSON mismatch detection
# ---------------------------------------------------------------------------


def test_analyze_batch_json_mismatch(runner, make_wav):
    """Batch JSON output includes mismatch ProblemItem when rates differ."""
    sr1 = 44100
    sr2 = 48000
    t1 = np.linspace(0, 1.0, sr1, endpoint=False, dtype=np.float32)
    t2 = np.linspace(0, 1.0, sr2, endpoint=False, dtype=np.float32)
    samples1 = np.sin(2 * np.pi * 440 * t1).astype(np.float32)
    samples2 = np.sin(2 * np.pi * 440 * t2).astype(np.float32)

    path1 = make_wav(samples1, sr1, name="a.wav")
    path2 = make_wav(samples2, sr2, name="b.wav")

    result = runner.invoke(cli, ["analyze", "--json", path1, path2])
    assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"
    data = json.loads(result.output)

    # At least one stem should have the mismatch problem injected
    found_mismatch = False
    for stem_name, stem_data in data["stems"].items():
        if "problems" in stem_data:
            for problem in stem_data["problems"].get("problems", []):
                if problem.get("type") == "sample_rate_mismatch":
                    found_mismatch = True
                    break
    assert found_mismatch, "Expected sample_rate_mismatch problem in batch JSON output"
