"""Tests for resample_to_match utility function.

Validates polyphase FIR resampling behavior: upsample-only policy,
identity passthrough, sample count/duration correctness, dtype
preservation, and warning logging.
"""

from __future__ import annotations

import logging
from math import gcd

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom._resample import resample_to_match


def _make_audio(
    samples_1d: np.ndarray,
    sr: int,
    *,
    num_channels: int = 1,
    file_path: str | None = None,
) -> AudioData:
    """Build an AudioData from a 1D or 2D sample array."""
    if samples_1d.ndim == 1:
        samples_2d = samples_1d.reshape(-1, 1)
        if num_channels == 2:
            samples_2d = np.column_stack([samples_1d, samples_1d])
    else:
        samples_2d = samples_1d
        num_channels = samples_2d.shape[1]
    return AudioData(
        samples=samples_2d.astype(np.float32),
        sample_rate=sr,
        num_channels=num_channels,
        duration=len(samples_2d) / sr,
        num_samples=len(samples_2d),
        file_path=file_path,
    )


def _sine(freq: float, sr: int, duration: float = 0.1) -> np.ndarray:
    """Generate a mono sine wave as float32."""
    t = np.arange(int(sr * duration), dtype=np.float32) / sr
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# --- Identity (same rate) ---


class TestIdentity:
    """When source and target rates match, return input unchanged."""

    def test_same_rate_returns_same_object(self) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        result = resample_to_match(audio, 44100)
        assert result is audio

    def test_same_rate_no_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        audio = _make_audio(_sine(440.0, 48000), 48000)
        with caplog.at_level(logging.WARNING):
            resample_to_match(audio, 48000)
        assert len(caplog.records) == 0


# --- Downsample rejection ---


class TestDownsampleRejection:
    """Attempting to downsample must raise ValueError."""

    def test_downsample_raises(self) -> None:
        audio = _make_audio(_sine(440.0, 48000), 48000)
        with pytest.raises(ValueError, match="target_sr must be >= audio sample rate"):
            resample_to_match(audio, 44100)

    def test_downsample_96k_to_48k_raises(self) -> None:
        audio = _make_audio(_sine(440.0, 96000, duration=0.05), 96000)
        with pytest.raises(ValueError):
            resample_to_match(audio, 48000)


# --- Upsampling correctness ---


class TestUpsampleMono:
    """Mono upsampling: sample count, duration, metadata."""

    def test_44100_to_48000_sample_count(self) -> None:
        sr_in, sr_out = 44100, 48000
        audio = _make_audio(_sine(440.0, sr_in), sr_in)
        result = resample_to_match(audio, sr_out)

        g = gcd(sr_in, sr_out)
        up, down = sr_out // g, sr_in // g
        expected_samples = int(np.ceil(audio.num_samples * up / down))
        # resample_poly may produce exactly expected_samples or +/-1
        assert abs(result.num_samples - expected_samples) <= 1

    def test_44100_to_48000_sample_rate(self) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        result = resample_to_match(audio, 48000)
        assert result.sample_rate == 48000

    def test_22050_to_44100_exact_double(self) -> None:
        sr_in = 22050
        audio = _make_audio(_sine(440.0, sr_in), sr_in)
        result = resample_to_match(audio, 44100)
        # Exact 2x upsample: output should have exactly 2*N samples
        assert result.num_samples == audio.num_samples * 2

    def test_duration_preserved(self) -> None:
        audio = _make_audio(_sine(440.0, 44100, duration=0.5), 44100)
        result = resample_to_match(audio, 48000)
        assert abs(result.duration - audio.duration) < 0.01

    def test_num_channels_mono(self) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        result = resample_to_match(audio, 48000)
        assert result.num_channels == 1

    def test_output_dtype_float32(self) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        result = resample_to_match(audio, 48000)
        assert result.samples.dtype == np.float32


class TestUpsampleStereo:
    """Stereo upsampling: each channel resampled independently."""

    def test_stereo_channel_count(self) -> None:
        left = _sine(440.0, 44100)
        right = _sine(880.0, 44100)
        stereo = np.column_stack([left, right]).astype(np.float32)
        audio = _make_audio(stereo, 44100)
        result = resample_to_match(audio, 48000)
        assert result.num_channels == 2

    def test_stereo_sample_count(self) -> None:
        sr_in, sr_out = 44100, 48000
        left = _sine(440.0, sr_in)
        right = _sine(880.0, sr_in)
        stereo = np.column_stack([left, right]).astype(np.float32)
        audio = _make_audio(stereo, sr_in)
        result = resample_to_match(audio, sr_out)

        g = gcd(sr_in, sr_out)
        up, down = sr_out // g, sr_in // g
        expected = int(np.ceil(audio.num_samples * up / down))
        assert abs(result.num_samples - expected) <= 1

    def test_stereo_shape(self) -> None:
        left = _sine(440.0, 44100)
        right = _sine(880.0, 44100)
        stereo = np.column_stack([left, right]).astype(np.float32)
        audio = _make_audio(stereo, 44100)
        result = resample_to_match(audio, 48000)
        assert result.samples.shape[1] == 2


# --- Metadata preservation ---


class TestMetadata:
    """file_path and computed fields preserved correctly."""

    def test_file_path_preserved(self) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100, file_path="/tmp/test.wav")
        result = resample_to_match(audio, 48000)
        assert result.file_path == "/tmp/test.wav"

    def test_file_path_none_preserved(self) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        result = resample_to_match(audio, 48000)
        assert result.file_path is None

    def test_num_samples_matches_array(self) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        result = resample_to_match(audio, 48000)
        assert result.num_samples == result.samples.shape[0]

    def test_duration_matches_samples_over_rate(self) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        result = resample_to_match(audio, 48000)
        expected_duration = result.num_samples / result.sample_rate
        assert abs(result.duration - expected_duration) < 1e-6


# --- Info logging ---


class TestInfoLogging:
    """Info message logged when resampling occurs."""

    def test_info_logged(self, caplog: pytest.LogCaptureFixture) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        with caplog.at_level(logging.INFO):
            resample_to_match(audio, 48000)
        assert any("resampling" in r.message.lower() for r in caplog.records)

    def test_info_contains_rates(self, caplog: pytest.LogCaptureFixture) -> None:
        audio = _make_audio(_sine(440.0, 44100), 44100)
        with caplog.at_level(logging.INFO):
            resample_to_match(audio, 48000)
        msgs = " ".join(r.message for r in caplog.records)
        assert "44100" in msgs
        assert "48000" in msgs
