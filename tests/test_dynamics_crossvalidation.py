"""Cross-validate Phantom dynamics measurements against hand-rolled references.

Verifies RMS, peak, and crest factor calculations against numpy-based
reference implementations across a panel of synthetic signals.
"""

from __future__ import annotations

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom.dynamics import analyze_dynamics

TOLERANCE_DB = 0.5


def _make_audio(samples: np.ndarray, sr: int) -> AudioData:
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    return AudioData(
        samples=samples,
        sample_rate=sr,
        num_channels=samples.shape[1],
        duration=len(samples) / sr,
        num_samples=len(samples),
    )


def _ref_rms_dbfs(samples: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(samples**2)))
    return float(20 * np.log10(rms + 1e-10))


def _ref_peak_dbfs(samples: np.ndarray) -> float:
    peak = float(np.max(np.abs(samples)))
    return float(20 * np.log10(peak + 1e-10))


class TestRMSCrossValidation:
    """Cross-validate RMS level against numpy reference."""

    @pytest.mark.parametrize(
        "amplitude",
        [1.0, 0.5, 0.1, 0.01],
        ids=["full-scale", "half", "quiet", "very-quiet"],
    )
    def test_sine_rms(self, amplitude):
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        result = analyze_dynamics(_make_audio(samples, sr))
        ref_rms = _ref_rms_dbfs(samples)

        assert result.rms_dbfs == pytest.approx(ref_rms, abs=TOLERANCE_DB)

    def test_white_noise_rms(self):
        sr = 44100
        rng = np.random.default_rng(42)
        samples = rng.standard_normal(sr * 2).astype(np.float32) * 0.3

        result = analyze_dynamics(_make_audio(samples, sr))
        ref_rms = _ref_rms_dbfs(samples)

        assert result.rms_dbfs == pytest.approx(ref_rms, abs=TOLERANCE_DB)


class TestPeakCrossValidation:
    """Cross-validate peak level against numpy reference."""

    @pytest.mark.parametrize("amplitude", [1.0, 0.5, 0.1])
    def test_sine_peak(self, amplitude):
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        result = analyze_dynamics(_make_audio(samples, sr))
        ref_peak = _ref_peak_dbfs(samples)

        assert result.peak_dbfs == pytest.approx(ref_peak, abs=TOLERANCE_DB)

    def test_clipped_peak(self):
        """Clipped signal should have peak at 0 dBFS."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = np.clip(1.5 * np.sin(2 * np.pi * 440 * t), -1.0, 1.0).astype(
            np.float32
        )

        result = analyze_dynamics(_make_audio(samples, sr))
        assert result.peak_dbfs == pytest.approx(0.0, abs=0.1)


class TestCrestFactorCrossValidation:
    """Cross-validate crest factor (peak - RMS in dB)."""

    def test_sine_crest_factor(self):
        """Pure sine crest factor is ~3.01 dB (sqrt(2) ratio)."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        result = analyze_dynamics(_make_audio(samples, sr))
        assert result.crest_factor_db == pytest.approx(3.01, abs=0.2)

    def test_square_wave_crest_factor(self):
        """Square wave has crest factor of ~0 dB (peak == RMS)."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sign(np.sin(2 * np.pi * 440 * t))).astype(np.float32)

        result = analyze_dynamics(_make_audio(samples, sr))
        assert result.crest_factor_db == pytest.approx(0.0, abs=0.5)

    def test_crest_matches_peak_minus_rms(self):
        """Crest factor equals peak_dbfs - rms_dbfs."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)

        result = analyze_dynamics(_make_audio(samples, sr))
        expected = result.peak_dbfs - result.rms_dbfs
        assert result.crest_factor_db == pytest.approx(expected, abs=0.01)
