"""Tests for the dynamics analysis module.

Covers DYN-01 through DYN-05.
All test audio is generated in-memory via conftest fixtures.
"""

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom.dynamics import DynamicsResult, analyze_dynamics


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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def varying_amplitude_5s():
    """5-second 440Hz sine with amplitude envelope from 0.1 to 1.0 and back."""
    sr = 44100
    t = np.linspace(0, 5.0, sr * 5, endpoint=False, dtype=np.float32)
    envelope = np.concatenate(
        [
            np.linspace(0.1, 1.0, sr * 2, dtype=np.float32),
            np.ones(sr, dtype=np.float32),
            np.linspace(1.0, 0.1, sr * 2, dtype=np.float32),
        ]
    )
    samples = (envelope * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return samples, sr


@pytest.fixture
def sparse_impulses():
    """1-second signal with sparse impulses (high crest factor)."""
    sr = 44100
    samples = np.zeros(sr, dtype=np.float32)
    samples[::4410] = 0.9  # impulse every 0.1s
    return samples, sr


# ---------------------------------------------------------------------------
# DYN-01: RMS Level
# ---------------------------------------------------------------------------


class TestRMS:
    """Verify RMS level measurement in dBFS."""

    def test_sine_rms_near_minus3(self, mono_sine_440hz):
        """440Hz sine at amplitude 1.0: RMS = 1/sqrt(2) => ~-3.01 dBFS."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert result.rms_dbfs == pytest.approx(-3.01, abs=0.5)

    def test_rms_is_float(self, mono_sine_440hz):
        """RMS dBFS should always be a float (when not None)."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert isinstance(result.rms_dbfs, float)


# ---------------------------------------------------------------------------
# DYN-02: Peak Level
# ---------------------------------------------------------------------------


class TestPeak:
    """Verify peak level measurement in dBFS."""

    def test_sine_peak_near_zero(self, mono_sine_440hz):
        """440Hz sine at amplitude 1.0: peak = 1.0 => 0.0 dBFS."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert result.peak_dbfs == pytest.approx(0.0, abs=0.1)

    def test_peak_is_float(self, mono_sine_440hz):
        """Peak dBFS should always be a float (when not None)."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert isinstance(result.peak_dbfs, float)


# ---------------------------------------------------------------------------
# DYN-03: Crest Factor
# ---------------------------------------------------------------------------


class TestCrestFactor:
    """Verify crest factor calculation and low-crest flag."""

    def test_sine_crest_factor(self, mono_sine_440hz):
        """440Hz sine: crest = peak_db - rms_db = 0.0 - (-3.01) = ~3.01 dB."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert result.crest_factor_db == pytest.approx(3.01, abs=0.5)

    def test_crest_factor_is_low_true_for_sine(self, mono_sine_440hz):
        """Sine wave crest ~3.01 dB is below 6.0 => crest_factor_is_low is True."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert result.crest_factor_is_low is True

    def test_crest_factor_is_low_false_for_impulses(self, sparse_impulses):
        """Sparse impulses have high crest factor => crest_factor_is_low is False."""
        samples, sr = sparse_impulses
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert result.crest_factor_is_low is False


# ---------------------------------------------------------------------------
# DYN-04: Dynamic Range
# ---------------------------------------------------------------------------


class TestDynamicRange:
    """Verify dynamic range as 95th-5th percentile of block RMS."""

    def test_constant_amplitude_range_near_zero(self, mono_sine_440hz):
        """Constant-amplitude sine: dynamic range near 0.0 dB (within 1.0)."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert result.dynamic_range_db == pytest.approx(0.0, abs=1.0)

    def test_varying_amplitude_range_above_10(self, varying_amplitude_5s):
        """Varying-amplitude signal (quiet-to-loud envelope): range > 10.0 dB."""
        samples, sr = varying_amplitude_5s
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert result.dynamic_range_db > 10.0


# ---------------------------------------------------------------------------
# DYN-05: Dynamic Complexity
# ---------------------------------------------------------------------------


class TestDynamicComplexity:
    """Verify Essentia DynamicComplexity integration."""

    def test_complexity_is_float(self, mono_sine_440hz):
        """dynamic_complexity should be a float."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert isinstance(result.dynamic_complexity, float)

    def test_loudness_db_is_float(self, mono_sine_440hz):
        """loudness_db should be a float."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert isinstance(result.loudness_db, float)


# ---------------------------------------------------------------------------
# Near-silence guard
# ---------------------------------------------------------------------------


class TestNearSilenceGuard:
    """Near-silent audio should return None for all dynamics values."""

    def test_all_values_none_for_near_silence(self, near_silence):
        """Near-silent audio (~-100 dBFS) -> all 7 values None."""
        samples, sr = near_silence
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        assert result.rms_dbfs is None
        assert result.peak_dbfs is None
        assert result.crest_factor_db is None
        assert result.crest_factor_is_low is None
        assert result.dynamic_range_db is None
        assert result.dynamic_complexity is None
        assert result.loudness_db is None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Empty audio should raise AnalysisError."""

    def test_analysis_error_on_empty_input(self):
        """Empty audio (0 samples) raises AnalysisError."""
        from phantom.exceptions import AnalysisError

        samples = np.array([], dtype=np.float32)
        audio = AudioData(
            samples=samples.reshape(0, 1),
            sample_rate=44100,
            num_channels=1,
            duration=0.0,
            num_samples=0,
        )

        with pytest.raises(AnalysisError):
            analyze_dynamics(audio)


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


class TestResultStructure:
    """Verify result dict shape and key naming."""

    def test_returns_dynamics_result(self, mono_sine_440hz):
        """analyze_dynamics should return a DynamicsResult model."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)
        assert isinstance(result, DynamicsResult)

    def test_all_keys_present(self, mono_sine_440hz):
        """Result should have exactly the 7 expected fields."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_dynamics(audio)

        expected_keys = {
            "rms_dbfs",
            "peak_dbfs",
            "crest_factor_db",
            "crest_factor_is_low",
            "dynamic_range_db",
            "dynamic_complexity",
            "loudness_db",
        }
        assert set(result.model_dump().keys()) == expected_keys
