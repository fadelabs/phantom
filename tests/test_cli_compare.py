"""Tests for phantom compare CLI command."""

from __future__ import annotations

import json

import pytest
import soundfile as sf

from click.testing import CliRunner
from phantom.cli import cli


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def make_wav(tmp_path):
    """Factory: write numpy array to a temporary WAV file and return path string."""
    _counter = [0]

    def _make(samples, sr=44100):
        _counter[0] += 1
        path = tmp_path / f"compare_test_{_counter[0]}.wav"
        sf.write(str(path), samples, sr)
        return str(path)

    return _make


# ---------------------------------------------------------------------------
# Profile comparison tests
# ---------------------------------------------------------------------------


def test_compare_profile(runner, comparison_stereo_audio, make_wav):
    """Compare with --profile rock --json produces JSON with profile_name."""
    samples, sr = comparison_stereo_audio
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["compare", "--profile", "rock", "--json", path])
    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "profile_name" in data
    assert data["profile_name"] == "rock"


def test_compare_profile_short_flag(runner, comparison_stereo_audio, make_wav):
    """Short flags -p and -j work the same as long flags."""
    samples, sr = comparison_stereo_audio
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["compare", "-p", "rock", "-j", path])
    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "profile_name" in data


# ---------------------------------------------------------------------------
# Reference comparison tests
# ---------------------------------------------------------------------------


def test_compare_reference(runner, comparison_stereo_audio, make_wav):
    """Compare with --reference produces JSON with loudness section."""
    samples, sr = comparison_stereo_audio
    path1 = make_wav(samples, sr)
    path2 = make_wav(samples, sr)
    result = runner.invoke(cli, ["compare", "--reference", path2, "--json", path1])
    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "loudness" in data


# ---------------------------------------------------------------------------
# Mutual exclusivity tests
# ---------------------------------------------------------------------------


def test_compare_mutual_exclusion(runner, comparison_stereo_audio, make_wav):
    """Passing both --profile and --reference raises a UsageError."""
    samples, sr = comparison_stereo_audio
    path = make_wav(samples, sr)
    result = runner.invoke(
        cli, ["compare", "--profile", "rock", "--reference", path, path]
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower()


# ---------------------------------------------------------------------------
# Non-TTY / picker tests
# ---------------------------------------------------------------------------


def test_compare_no_mode_non_tty(runner, comparison_stereo_audio, make_wav):
    """In non-TTY (CliRunner default), omitting --profile/--reference errors."""
    samples, sr = comparison_stereo_audio
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["compare", path])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


def test_compare_invalid_profile(runner, comparison_stereo_audio, make_wav):
    """A non-existent profile name causes an error exit."""
    samples, sr = comparison_stereo_audio
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["compare", "--profile", "nonexistent_genre_xyz", path])
    assert result.exit_code != 0


def test_compare_invalid_file(runner):
    """A non-existent input file causes an error exit."""
    result = runner.invoke(cli, ["compare", "--profile", "rock", "/nonexistent.wav"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Rich output tests
# ---------------------------------------------------------------------------


def test_compare_rich_output(runner, comparison_stereo_audio, make_wav):
    """Rich output (no --json) includes the profile name."""
    samples, sr = comparison_stereo_audio
    path = make_wav(samples, sr)
    result = runner.invoke(cli, ["compare", "--profile", "rock", path])
    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    # Profile name should appear somewhere in the rich output
    assert "rock" in result.output.lower()
