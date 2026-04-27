"""Tests for phantom separate CLI command."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import soundfile as sf

from click.testing import CliRunner
from phantom.cli import cli
from phantom.separation import SeparationResult


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
        path = tmp_path / f"separate_test_{_counter[0]}.wav"
        sf.write(str(path), samples, sr)
        return str(path)

    return _make


# ---------------------------------------------------------------------------
# Demucs missing tests
# ---------------------------------------------------------------------------


def test_separate_missing_demucs(runner, mono_sine_440hz, make_wav):
    """Without Demucs installed, shows install instructions and exits non-zero."""
    from phantom.exceptions import DependencyMissingError

    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    with patch(
        "phantom.cli.separate.separate_stems",
        side_effect=DependencyMissingError(package="Demucs", extra="separation"),
    ):
        result = runner.invoke(cli, ["separate", path])
    assert result.exit_code != 0
    output_lower = result.output.lower()
    assert "not installed" in output_lower or "separation" in output_lower


def test_separate_missing_demucs_json(runner, mono_sine_440hz, make_wav):
    """JSON mode with missing Demucs still shows error."""
    from phantom.exceptions import DependencyMissingError

    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    with patch(
        "phantom.cli.separate.separate_stems",
        side_effect=DependencyMissingError(package="Demucs", extra="separation"),
    ):
        result = runner.invoke(cli, ["separate", "--json", path])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Mocked Demucs tests
# ---------------------------------------------------------------------------


def _make_mock_result(tmp_path):
    """Create a mock SeparationResult for testing."""
    return SeparationResult(
        stems={
            "vocals": str(tmp_path / "vocals.wav"),
            "drums": str(tmp_path / "drums.wav"),
            "bass": str(tmp_path / "bass.wav"),
            "other": str(tmp_path / "other.wav"),
        },
    )


def test_separate_with_mock_demucs(runner, mono_sine_440hz, make_wav, tmp_path):
    """Mocked Demucs produces valid JSON output with stems."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    mock_result = _make_mock_result(tmp_path)

    with patch("phantom.cli.separate.separate_stems", return_value=mock_result):
        result = runner.invoke(cli, ["separate", "--json", path])

    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "stems" in data
    assert "vocals" in data["stems"]
    assert "drums" in data["stems"]


def test_separate_with_mock_rich_output(runner, mono_sine_440hz, make_wav, tmp_path):
    """Mocked Demucs produces Rich output with stem names."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    mock_result = _make_mock_result(tmp_path)

    with patch("phantom.cli.separate.separate_stems", return_value=mock_result):
        result = runner.invoke(cli, ["separate", path])

    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    output_lower = result.output.lower()
    assert "vocals" in output_lower
    assert "drums" in output_lower


# ---------------------------------------------------------------------------
# Help and error tests
# ---------------------------------------------------------------------------


def test_separate_help(runner):
    """Help text mentions Demucs and stems."""
    result = runner.invoke(cli, ["separate", "--help"])
    assert result.exit_code == 0
    output_lower = result.output.lower()
    assert "demucs" in output_lower or "stem" in output_lower


def test_separate_invalid_file(runner):
    """A non-existent input file causes an error exit."""
    result = runner.invoke(cli, ["separate", "/nonexistent.wav"])
    assert result.exit_code != 0


def test_separate_custom_output_dir(runner, mono_sine_440hz, make_wav, tmp_path):
    """Custom --output-dir is passed to separate_stems."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    mock_result = _make_mock_result(tmp_path)
    custom_dir = str(tmp_path / "custom_stems")

    with patch(
        "phantom.cli.separate.separate_stems", return_value=mock_result
    ) as mock_fn:
        result = runner.invoke(cli, ["separate", "--output-dir", custom_dir, path])

    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    mock_fn.assert_called_once_with(path, custom_dir)
