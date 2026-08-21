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


class TestDynamicComplexityCrossValidation:
    """Cross-validate dynamic_complexity and loudness_db.

    Both fields previously had no value coverage anywhere in the suite -- only
    isinstance(x, float) shape checks. Replacing the Essentia DynamicComplexity
    call with hardcoded constants passed all 1178 tests. There is no independent
    reference implementation to check against, so these assert properties the
    measurement must hold regardless of how it is computed, which constants
    cannot satisfy.
    """

    @staticmethod
    def _tone(amplitude: float, sr: int = 44100, seconds: float = 3.0) -> np.ndarray:
        t = np.linspace(0, seconds, int(sr * seconds), endpoint=False, dtype=np.float32)
        return (amplitude * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    @pytest.mark.parametrize("amplitude", [0.5, 0.25, 0.125])
    def test_loudness_db_tracks_amplitude(self, amplitude):
        """Halving amplitude drops loudness_db by 6.02 dB, the definition of half.

        Anchored at -9.86 dB for amplitude 0.5, so the absolute scale is pinned
        as well as the ratio.
        """
        result = analyze_dynamics(_make_audio(self._tone(amplitude), 44100))
        expected = -9.86 + 20 * np.log10(amplitude / 0.5)
        assert result.loudness_db == pytest.approx(expected, abs=TOLERANCE_DB)

    def test_dynamic_complexity_separates_steady_from_varying(self):
        """A level-varying signal must read far more complex than a steady one.

        This is the property the name describes, and it is the one a constant
        cannot have: a constant returns the same number for both inputs.
        """
        steady = analyze_dynamics(_make_audio(self._tone(0.5), 44100))

        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        envelope = np.where((np.floor(t * 2) % 2) == 0, 1.0, 0.05).astype(np.float32)
        varying = analyze_dynamics(
            _make_audio((self._tone(0.5) * envelope).astype(np.float32), sr)
        )

        assert steady.dynamic_complexity < 0.5
        assert varying.dynamic_complexity > 5.0
        assert varying.dynamic_complexity > steady.dynamic_complexity
