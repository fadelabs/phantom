"""Tests for the loudness measurement module.

Covers LOUD-01 through LOUD-05 plus D-08 pyloudnorm cross-validation.
All test audio is generated in-memory via conftest fixtures.
"""

import numpy as np
import pyloudnorm as pyln
import pytest

from phantom.audio import AudioData
from phantom.loudness import LoudnessResult, analyze_loudness


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_audio(samples_1d: np.ndarray, sr: int) -> AudioData:
    """Wrap a 1D mono signal into an AudioData instance."""
    samples_2d = samples_1d.reshape(-1, 1)
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=1,
        duration=len(samples_1d) / sr,
        num_samples=len(samples_1d),
    )


# ---------------------------------------------------------------------------
# LOUD-01: Integrated LUFS
# ---------------------------------------------------------------------------


class TestIntegratedLUFS:
    """Verify EBU R128 integrated loudness measurement."""

    def test_sine_1khz_integrated_lufs_near_minus23(self, sine_1khz_minus23lufs):
        """1 kHz sine calibrated to -23 LUFS should measure near -23 LUFS."""
        samples, sr = sine_1khz_minus23lufs
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert result.integrated_lufs is not None
        assert isinstance(result.integrated_lufs, float)
        assert result.integrated_lufs == pytest.approx(-23.0, abs=1.0)

    def test_integrated_lufs_is_float(self, mono_sine_440hz):
        """Integrated LUFS should always be a float (when not None)."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert isinstance(result.integrated_lufs, float)


# ---------------------------------------------------------------------------
# LOUD-02: True peak (dBTP)
# ---------------------------------------------------------------------------


class TestTruePeak:
    """Verify ITU-R BS.1770-4 true peak measurement."""

    def test_clipped_sine_true_peak_near_zero(self, clipped_sine):
        """Clipped sine should have true peak near 0 dBTP (full scale)."""
        samples, sr = clipped_sine
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert result.true_peak_dbtp is not None
        assert isinstance(result.true_peak_dbtp, float)
        # Clipped at 1.0 -> should be near 0 dBTP (within 1 dB)
        assert result.true_peak_dbtp == pytest.approx(0.0, abs=1.0)

    def test_sine_440_true_peak_near_zero(self, mono_sine_440hz):
        """440 Hz sine at amplitude ~1.0 -> true peak near 0 dBTP."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert isinstance(result.true_peak_dbtp, float)
        # Amplitude 1.0 -> ~0 dBTP, within 1 dB
        assert result.true_peak_dbtp == pytest.approx(0.0, abs=1.0)


# ---------------------------------------------------------------------------
# LOUD-03: Loudness Range (LRA)
# ---------------------------------------------------------------------------


class TestLoudnessRange:
    """Verify EBU R128 loudness range measurement."""

    def test_constant_sine_lra_near_zero(self, sine_1khz_minus23lufs):
        """Constant-amplitude sine should have LRA near 0 LU."""
        samples, sr = sine_1khz_minus23lufs
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert result.loudness_range_lu is not None
        assert isinstance(result.loudness_range_lu, float)
        # Constant amplitude -> LRA should be low. With startAtZero=True on a
        # 5s signal, the initial ramp-up inflates LRA slightly (up to ~3 LU).
        assert result.loudness_range_lu == pytest.approx(0.0, abs=3.0)


# ---------------------------------------------------------------------------
# LOUD-04: Short-term and momentary LUFS
# ---------------------------------------------------------------------------


class TestShortTermAndMomentary:
    """Verify short-term (3s) and momentary (400ms) LUFS lists."""

    def test_short_term_lufs_is_list(self, sine_1khz_minus23lufs):
        """Short-term LUFS should be a non-empty list of floats."""
        samples, sr = sine_1khz_minus23lufs
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert isinstance(result.short_term_lufs, list)
        assert len(result.short_term_lufs) > 0
        assert all(isinstance(v, float) for v in result.short_term_lufs)

    def test_momentary_lufs_is_list(self, sine_1khz_minus23lufs):
        """Momentary LUFS should be a non-empty list of floats."""
        samples, sr = sine_1khz_minus23lufs
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert isinstance(result.momentary_lufs, list)
        assert len(result.momentary_lufs) > 0
        assert all(isinstance(v, float) for v in result.momentary_lufs)


# ---------------------------------------------------------------------------
# LOUD-05: Near-silence returns None
# ---------------------------------------------------------------------------


class TestNearSilenceGuard:
    """Near-silent audio should return None for all loudness values."""

    def test_all_values_none_for_near_silence(self, near_silence):
        """Near-silent audio (~-100 dBFS) -> all values None."""
        samples, sr = near_silence
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert result.integrated_lufs is None
        assert result.true_peak_dbtp is None
        assert result.loudness_range_lu is None
        assert result.short_term_lufs is None
        assert result.momentary_lufs is None


# ---------------------------------------------------------------------------
# Cross-validation: Essentia vs pyloudnorm (D-08)
# ---------------------------------------------------------------------------


class TestCrossValidation:
    """Essentia and pyloudnorm integrated LUFS should agree within 0.5 dB."""

    def test_1khz_sine_cross_validation(self, sine_1khz_minus23lufs):
        """Cross-validate with 1 kHz sine at -23 LUFS."""
        samples, sr = sine_1khz_minus23lufs
        audio = _make_audio(samples, sr)

        # Essentia result (mono duplicated to both channels internally)
        result = analyze_loudness(audio)
        essentia_lufs = result.integrated_lufs

        # pyloudnorm result -- feed stereo (duplicated) to match Essentia's
        # internal mono handling (EBU Tech 3341 s5: mono on both channels).
        stereo = np.column_stack([samples, samples])
        meter = pyln.Meter(sr)
        pyln_lufs = meter.integrated_loudness(stereo)

        assert essentia_lufs == pytest.approx(pyln_lufs, abs=0.5)

    def test_440hz_sine_cross_validation(self):
        """Cross-validate with 440 Hz sine at default amplitude.

        Uses a 5-second signal because EBU R128 requires at least 3s for
        reliable short-term measurement; 1s signals produce gating artifacts
        that inflate the discrepancy between implementations.
        """
        sr = 44100
        t = np.linspace(0, 5.0, sr * 5, endpoint=False, dtype=np.float32)
        samples = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        audio = _make_audio(samples, sr)

        # Essentia result (mono duplicated to both channels internally)
        result = analyze_loudness(audio)
        essentia_lufs = result.integrated_lufs

        # pyloudnorm result -- feed stereo (duplicated) to match Essentia's
        # internal mono handling (EBU Tech 3341 s5: mono on both channels).
        stereo = np.column_stack([samples, samples])
        meter = pyln.Meter(sr)
        pyln_lufs = meter.integrated_loudness(stereo)

        assert essentia_lufs == pytest.approx(pyln_lufs, abs=0.5)


# ---------------------------------------------------------------------------
# Stereo audio path (WR-03, CR-01)
# ---------------------------------------------------------------------------


class TestStereoLoudness:
    """Verify stereo audio produces valid loudness measurements."""

    def test_stereo_audio_loudness(self):
        """Stereo audio should produce valid loudness measurements."""
        sr = 44100
        t = np.linspace(0, 5.0, sr * 5, endpoint=False, dtype=np.float32)
        left = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        right = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        stereo = np.column_stack([left, right])
        audio = AudioData(
            samples=stereo,
            sample_rate=sr,
            num_channels=2,
            duration=5.0,
            num_samples=len(left),
        )
        result = analyze_loudness(audio)
        assert isinstance(result.integrated_lufs, float)
        assert isinstance(result.true_peak_dbtp, float)
        # True peak should reflect the loudest channel (left at ~0 dBTP)
        assert result.true_peak_dbtp > -1.0

    def test_stereo_true_peak_per_channel(self):
        """True peak should be the max across channels, not the mono mix."""
        sr = 44100
        t = np.linspace(0, 5.0, sr * 5, endpoint=False, dtype=np.float32)
        # Left channel at full scale, right channel much quieter
        left = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        right = (0.01 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        stereo = np.column_stack([left, right])
        audio = AudioData(
            samples=stereo,
            sample_rate=sr,
            num_channels=2,
            duration=5.0,
            num_samples=len(left),
        )
        result = analyze_loudness(audio)
        # Left is at ~0 dBTP; mono mix would attenuate to ~-6 dBTP
        # Per-channel measurement should report close to 0 dBTP
        assert result.true_peak_dbtp > -1.0


# ---------------------------------------------------------------------------
# Result structure (D-01, D-02)
# ---------------------------------------------------------------------------


class TestResultStructure:
    """Verify result dict shape and key naming."""

    def test_returns_loudness_result(self, mono_sine_440hz):
        """analyze_loudness should return a LoudnessResult model."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)
        assert isinstance(result, LoudnessResult)

    def test_all_top_level_keys_present(self, mono_sine_440hz):
        """Result should have exactly the 5 expected fields."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        expected_keys = {
            "integrated_lufs",
            "true_peak_dbtp",
            "loudness_range_lu",
            "short_term_lufs",
            "momentary_lufs",
        }
        assert set(result.model_dump().keys()) == expected_keys
