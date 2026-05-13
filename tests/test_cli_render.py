"""Tests for phantom render CLI command."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import soundfile as sf
from click.testing import CliRunner

from phantom.cli import cli


def _extract_json(output: str) -> dict:
    """Extract JSON object from output that may contain Rich progress bar text."""
    # Find the first '{' which starts the JSON object
    start = output.index("{")
    return json.loads(output[start:])


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def make_wav(tmp_path, mono_sine_440hz):
    """Write the mono sine fixture to a temporary WAV file and return its path."""
    samples, sr = mono_sine_440hz
    path = tmp_path / "test_input.wav"
    sf.write(str(path), samples, sr)
    return str(path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_render_help(runner):
    """render --help shows format options and exits cleanly."""
    result = runner.invoke(cli, ["render", "--help"])
    assert result.exit_code == 0
    assert "format" in result.output.lower()


def test_render_missing_ffmpeg(runner, make_wav):
    """When ffmpeg is not installed, render shows install instructions."""
    with patch("phantom.cli.render.shutil.which", return_value=None):
        result = runner.invoke(cli, ["render", make_wav, "--format", "mp3"])
    assert result.exit_code != 0
    output_lower = result.output.lower()
    assert "ffmpeg" in output_lower
    assert "brew" in output_lower or "apt" in output_lower


def test_render_missing_file(runner):
    """Render with a nonexistent file path exits with error."""
    with patch("phantom.cli.render.shutil.which", return_value="/usr/bin/ffmpeg"):
        result = runner.invoke(cli, ["render", "/nonexistent.wav", "--format", "mp3"])
    assert result.exit_code != 0


def test_render_format_required(runner, make_wav):
    """Render without --format flag fails (click requires it)."""
    result = runner.invoke(cli, ["render", make_wav])
    assert result.exit_code != 0


def test_render_with_mock_ffmpeg(runner, make_wav, tmp_path):
    """Mocked ffmpeg conversion produces valid JSON output."""
    mock_ff_instance = MagicMock()
    mock_ff_instance.run_command_with_progress.return_value = iter([0, 50, 100])

    mock_ff_cls = MagicMock(return_value=mock_ff_instance)

    with (
        patch("phantom.cli.render.shutil.which", return_value="/usr/bin/ffmpeg"),
        # Patch at the source module -- works because render.py does a lazy
        # `from ffmpeg_progress_yield import FfmpegProgress` inside the function.
        # If the import is ever hoisted to module level, change target to
        # "phantom.cli.render.FfmpegProgress".
        patch("ffmpeg_progress_yield.FfmpegProgress", mock_ff_cls),
    ):
        result = runner.invoke(cli, ["render", make_wav, "--format", "mp3", "--json"])

    assert result.exit_code == 0
    data = _extract_json(result.output)
    assert data["output"].endswith(".mp3")
    assert data["format"] == "mp3"


def test_render_bitrate_option(runner, make_wav):
    """Bitrate option is captured and reported in JSON output."""
    mock_ff_instance = MagicMock()
    mock_ff_instance.run_command_with_progress.return_value = iter([0, 100])

    mock_ff_cls = MagicMock(return_value=mock_ff_instance)

    with (
        patch("phantom.cli.render.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("ffmpeg_progress_yield.FfmpegProgress", mock_ff_cls),
    ):
        result = runner.invoke(
            cli,
            ["render", make_wav, "--format", "mp3", "--bitrate", "320k", "--json"],
        )

    assert result.exit_code == 0
    data = _extract_json(result.output)
    assert data["bitrate"] == "320k"


def test_render_custom_output(runner, make_wav, tmp_path):
    """Custom --output path is used and reported in JSON."""
    custom_out = str(tmp_path / "custom.mp3")

    mock_ff_instance = MagicMock()
    mock_ff_instance.run_command_with_progress.return_value = iter([0, 100])

    mock_ff_cls = MagicMock(return_value=mock_ff_instance)

    with (
        patch("phantom.cli.render.shutil.which", return_value="/usr/bin/ffmpeg"),
        patch("ffmpeg_progress_yield.FfmpegProgress", mock_ff_cls),
    ):
        result = runner.invoke(
            cli,
            [
                "render",
                make_wav,
                "--format",
                "mp3",
                "--output",
                custom_out,
                "--json",
            ],
        )

    assert result.exit_code == 0
    data = _extract_json(result.output)
    assert "custom.mp3" in data["output"]


# ---------------------------------------------------------------------------
# Path security integration tests (D-08, D-09)
# ---------------------------------------------------------------------------


class TestRenderPathSecurity:
    """Integration tests for render command path security enforcement."""

    def test_render_input_path_security_rejected(
        self, runner, tmp_path, mono_sine_440hz, monkeypatch
    ):
        """Input file outside PHANTOM_AUDIO_DIR is rejected with non-zero exit."""
        # Set up allowed directory
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(allowed))

        # Create WAV outside the allowed directory
        forbidden = tmp_path / "forbidden"
        forbidden.mkdir()
        wav_path = forbidden / "test.wav"
        samples, sr = mono_sine_440hz
        sf.write(str(wav_path), samples, sr)

        with patch("phantom.cli.render.shutil.which", return_value="/usr/bin/ffmpeg"):
            result = runner.invoke(
                cli, ["render", str(wav_path), "--format", "mp3"]
            )

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "denied" in output_lower or "outside" in output_lower

    def test_render_output_path_security_rejected(
        self, runner, tmp_path, mono_sine_440hz, monkeypatch
    ):
        """Output path outside PHANTOM_OUTPUT_DIR is rejected with non-zero exit."""
        # Create a WAV inside tmp_path (no input restriction)
        monkeypatch.delenv("PHANTOM_AUDIO_DIR", raising=False)
        wav_path = tmp_path / "test.wav"
        samples, sr = mono_sine_440hz
        sf.write(str(wav_path), samples, sr)

        # Set up allowed output directory
        allowed_out = tmp_path / "allowed_out"
        allowed_out.mkdir()
        monkeypatch.setenv("PHANTOM_OUTPUT_DIR", str(allowed_out))

        # Output path outside the allowed output directory
        forbidden_out = tmp_path / "forbidden_out" / "output.mp3"

        with patch("phantom.cli.render.shutil.which", return_value="/usr/bin/ffmpeg"):
            result = runner.invoke(
                cli,
                [
                    "render",
                    str(wav_path),
                    "--format",
                    "mp3",
                    "--output",
                    str(forbidden_out),
                ],
            )

        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "denied" in output_lower or "outside" in output_lower

    def test_render_input_inside_allowed_dir_passes_validation(
        self, runner, tmp_path, mono_sine_440hz, monkeypatch
    ):
        """Input inside PHANTOM_AUDIO_DIR passes path validation (fails on ffmpeg)."""
        monkeypatch.setenv("PHANTOM_AUDIO_DIR", str(tmp_path))
        monkeypatch.delenv("PHANTOM_OUTPUT_DIR", raising=False)

        wav_path = tmp_path / "test.wav"
        samples, sr = mono_sine_440hz
        sf.write(str(wav_path), samples, sr)

        # Mock ffmpeg as missing so it fails on ffmpeg check, not path security
        with patch("phantom.cli.render.shutil.which", return_value=None):
            result = runner.invoke(
                cli, ["render", str(wav_path), "--format", "mp3"]
            )

        # Should fail because ffmpeg is not found, NOT because of path security
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "denied" not in output_lower and "outside" not in output_lower
        assert "ffmpeg" in output_lower

    def test_render_no_restriction_when_env_unset(
        self, runner, tmp_path, mono_sine_440hz, monkeypatch
    ):
        """Without PHANTOM_AUDIO_DIR or PHANTOM_OUTPUT_DIR, no path restriction."""
        monkeypatch.delenv("PHANTOM_AUDIO_DIR", raising=False)
        monkeypatch.delenv("PHANTOM_OUTPUT_DIR", raising=False)

        wav_path = tmp_path / "anywhere" / "test.wav"
        wav_path.parent.mkdir(parents=True)
        samples, sr = mono_sine_440hz
        sf.write(str(wav_path), samples, sr)

        # Mock ffmpeg as missing so it fails on ffmpeg check, not path security
        with patch("phantom.cli.render.shutil.which", return_value=None):
            result = runner.invoke(
                cli, ["render", str(wav_path), "--format", "mp3"]
            )

        # Should fail because ffmpeg is not found, NOT path restriction
        assert result.exit_code != 0
        output_lower = result.output.lower()
        assert "denied" not in output_lower and "outside" not in output_lower
        assert "ffmpeg" in output_lower
