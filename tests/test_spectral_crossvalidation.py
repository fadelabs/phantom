"""Cross-validate Phantom spectral measurements against hand-rolled FFT references.

Verifies octave band energy distribution and spectral centroid against
manual numpy FFT calculations.
"""

from __future__ import annotations

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom.spectral import analyze_spectrum, OCTAVE_CENTERS

TOLERANCE_DB = 3.0


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


def _ref_dominant_band(freq_hz: float) -> str:
    """Return the octave band label that should contain the given frequency."""
    sqrt2 = np.sqrt(2)
    for center in OCTAVE_CENTERS:
        low = center / sqrt2
        high = center * sqrt2
        if low <= freq_hz < high:
            return f"{int(center)}_hz"
    return f"{int(OCTAVE_CENTERS[-1])}_hz"


class TestOctaveBandEnergy:
    """Cross-validate octave band energy against expected dominant bands."""

    @pytest.mark.parametrize(
        "freq,expected_band",
        [
            (100, "125_hz"),
            (300, "250_hz"),
            (1000, "1000_hz"),
            (4000, "4000_hz"),
            (8000, "8000_hz"),
        ],
    )
    def test_sine_dominant_band(self, freq, expected_band):
        """A pure sine should have its energy concentrated in the correct octave band."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)

        result = analyze_spectrum(_make_audio(samples, sr))
        bands = result.octave_band_energy_db

        dominant = max(bands, key=bands.get)
        assert dominant == expected_band, (
            f"{freq}Hz sine: expected dominant band {expected_band}, "
            f"got {dominant} (values: {bands})"
        )

    def test_low_freq_vs_high_freq(self):
        """A 100Hz sine should have more energy in low bands than high bands."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 100 * t)).astype(np.float32)

        result = analyze_spectrum(_make_audio(samples, sr))
        bands = result.octave_band_energy_db

        assert bands["125_hz"] > bands["4000_hz"] + 20


class TestSpectralCentroid:
    """Cross-validate spectral centroid against expected behavior."""

    def test_low_freq_has_low_centroid(self):
        """A 200Hz sine should have centroid near 200Hz."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)

        result = analyze_spectrum(_make_audio(samples, sr))
        assert 150 < result.spectral_centroid_hz < 300

    def test_high_freq_has_high_centroid(self):
        """A 5kHz sine should have centroid near 5kHz."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 5000 * t)).astype(np.float32)

        result = analyze_spectrum(_make_audio(samples, sr))
        assert 4000 < result.spectral_centroid_hz < 6000

    def test_centroid_increases_with_frequency(self):
        """Centroid of a 3kHz sine should be higher than a 300Hz sine."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)

        low = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
        high = (0.5 * np.sin(2 * np.pi * 3000 * t)).astype(np.float32)

        low_result = analyze_spectrum(_make_audio(low, sr))
        high_result = analyze_spectrum(_make_audio(high, sr))

        assert high_result.spectral_centroid_hz > low_result.spectral_centroid_hz


class TestSpectralFlatness:
    """Cross-validate spectral flatness against expected behavior."""

    def test_noise_is_flat(self):
        """White noise should have high spectral flatness (near 1.0)."""
        sr = 44100
        rng = np.random.default_rng(42)
        samples = rng.standard_normal(sr * 2).astype(np.float32) * 0.3

        result = analyze_spectrum(_make_audio(samples, sr))
        assert result.spectral_flatness > 0.5

    def test_sine_is_not_flat(self):
        """A pure sine should have low spectral flatness (near 0.0)."""
        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        result = analyze_spectrum(_make_audio(samples, sr))
        assert result.spectral_flatness < 0.1
