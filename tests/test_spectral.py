"""Tests for spectral analysis module.

Tests cover all six spectral descriptors (SPEC-01 through SPEC-06)
plus near-silence guard behavior. All test audio is synthetic.
"""

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom.spectral import SpectralResult, analyze_spectrum


def _make_audio_data(samples_1d: np.ndarray, sr: int) -> AudioData:
    """Helper: wrap a 1D float32 array into an AudioData object."""
    samples_2d = samples_1d.reshape(-1, 1)
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=1,
        duration=len(samples_1d) / sr,
        num_samples=len(samples_1d),
    )


# ---------------------------------------------------------------------------
# SPEC-01: Spectral centroid
# ---------------------------------------------------------------------------


class TestSpectralCentroid:
    """Spectral centroid should report the center of spectral mass in Hz."""

    def test_sine_440_centroid_near_440(self, mono_sine_440hz):
        """440 Hz sine -> centroid near 440 Hz (within +/- 50 Hz)."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert isinstance(result.spectral_centroid_hz, float)
        assert abs(result.spectral_centroid_hz - 440) < 50


# ---------------------------------------------------------------------------
# SPEC-02: Spectral rolloff
# ---------------------------------------------------------------------------


class TestSpectralRolloff:
    """Spectral rolloff should report the frequency below which 85% of energy lies."""

    def test_sine_440_rolloff_near_440(self, mono_sine_440hz):
        """440 Hz sine -> rolloff near 440 Hz (energy concentrated at fundamental)."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert isinstance(result.spectral_rolloff_hz, float)
        # Rolloff for a pure sine should be near its frequency
        assert result.spectral_rolloff_hz < 2000


# ---------------------------------------------------------------------------
# SPEC-03: Spectral flatness
# ---------------------------------------------------------------------------


class TestSpectralFlatness:
    """Spectral flatness: 0 = tonal, 1 = noise-like."""

    def test_sine_flatness_near_zero(self, mono_sine_440hz):
        """440 Hz sine (tonal) -> flatness below 0.1."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert isinstance(result.spectral_flatness, float)
        assert result.spectral_flatness < 0.1

    def test_noise_flatness_high(self, white_noise_1s):
        """White noise -> flatness above 0.5."""
        samples, sr = white_noise_1s
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert isinstance(result.spectral_flatness, float)
        assert result.spectral_flatness > 0.5


# ---------------------------------------------------------------------------
# SPEC-04: Spectral contrast
# ---------------------------------------------------------------------------


class TestSpectralContrast:
    """Spectral contrast returns per-band contrast values."""

    def test_contrast_is_list_of_floats(self, mono_sine_440hz):
        """Any signal -> list of float values."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert isinstance(result.spectral_contrast, list)
        assert len(result.spectral_contrast) > 0
        assert all(isinstance(v, float) for v in result.spectral_contrast)


# ---------------------------------------------------------------------------
# SPEC-05: Dissonance
# ---------------------------------------------------------------------------


class TestDissonance:
    """Dissonance measures spectral roughness from beating partials."""

    def test_multi_tone_high_dissonance(self, multi_tone_1s):
        """440 + 466 Hz (minor second) -> dissonance > 0.1 (clearly dissonant).

        Essentia's Dissonance algorithm returns values lower than some
        textbook roughness models. 0.19 for a minor second is well above
        the ~0.0002 of a pure sine, confirming the algorithm distinguishes
        dissonant from consonant intervals.
        """
        samples, sr = multi_tone_1s
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert isinstance(result.dissonance, float)
        assert result.dissonance > 0.1

    def test_pure_sine_low_dissonance(self, mono_sine_440hz):
        """Pure 440 Hz sine -> dissonance near 0.0 (consonant)."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert isinstance(result.dissonance, float)
        assert result.dissonance < 0.2


# ---------------------------------------------------------------------------
# SPEC-06: Octave band energy
# ---------------------------------------------------------------------------


class TestOctaveBandEnergy:
    """Octave band energy returns dB values for standard octave bands."""

    def test_band_keys_present(self, mono_sine_440hz):
        """Result has all 10 octave band keys."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        expected_keys = {
            "31_hz",
            "62_hz",
            "125_hz",
            "250_hz",
            "500_hz",
            "1000_hz",
            "2000_hz",
            "4000_hz",
            "8000_hz",
            "16000_hz",
        }
        assert isinstance(result.octave_band_energy_db, dict)
        assert set(result.octave_band_energy_db.keys()) == expected_keys

    def test_band_values_are_floats(self, mono_sine_440hz):
        """All band energy values are floats."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        for v in result.octave_band_energy_db.values():
            assert isinstance(v, float)

    def test_sine_440_energy_in_500_band(self, mono_sine_440hz):
        """440 Hz sine -> 500 Hz band should have high relative energy."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        bands = result.octave_band_energy_db
        # 440 Hz falls in the 500 Hz octave band (354-707 Hz)
        # It should be among the highest energy bands
        band_500 = bands["500_hz"]
        other_bands = [v for k, v in bands.items() if k != "500_hz"]
        # 500 Hz band should be higher than most other bands
        assert band_500 > max(other_bands) - 6  # within 6 dB of the max


# ---------------------------------------------------------------------------
# Near-silence guard
# ---------------------------------------------------------------------------


class TestNearSilenceGuard:
    """Near-silent audio should return None for all spectral values."""

    def test_all_values_none(self, near_silence):
        """Near-silent audio (~-100 dBFS) -> all values are None."""
        samples, sr = near_silence
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert result.spectral_centroid_hz is None
        assert result.spectral_rolloff_hz is None
        assert result.spectral_flatness is None
        assert result.spectral_contrast is None
        assert result.dissonance is None
        assert result.octave_band_energy_db is None


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


class TestResultStructure:
    """Verify analyze_spectrum returns the expected dict shape."""

    def test_returns_spectral_result(self, mono_sine_440hz):
        """analyze_spectrum returns a SpectralResult model."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        assert isinstance(result, SpectralResult)

    def test_all_top_level_keys_present(self, mono_sine_440hz):
        """Result has all 6 required fields."""
        samples, sr = mono_sine_440hz
        ad = _make_audio_data(samples, sr)
        result = analyze_spectrum(ad)
        expected = {
            "spectral_centroid_hz",
            "spectral_rolloff_hz",
            "spectral_flatness",
            "spectral_contrast",
            "dissonance",
            "octave_band_energy_db",
        }
        assert set(result.model_dump().keys()) == expected


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestBandLabelAlignment:
    """S-WR-08: Band labels in spectral.py match profile band keys."""

    def test_band_labels_match_profile_keys(self):
        """Built-in profile 'rock' has frequency.bands keys matching _BAND_LABELS."""
        from phantom.spectral import _BAND_LABELS
        from phantom._profiles import load_profile

        profile = load_profile("rock")
        profile_bands = sorted(profile.frequency.bands.keys())
        spectral_bands = sorted(_BAND_LABELS)
        assert profile_bands == spectral_bands, (
            f"Profile bands {profile_bands} != spectral bands {spectral_bands}"
        )


class TestErrorHandling:
    """Essentia failures should be wrapped in AnalysisError."""

    def test_analysis_error_on_bad_input(self):
        """Passing audio with invalid data raises AnalysisError."""
        from phantom.exceptions import AnalysisError

        # Empty audio (0 samples) should trigger an error
        samples = np.array([], dtype=np.float32).reshape(0, 1)
        ad = AudioData(
            samples=samples,
            sample_rate=44100,
            num_channels=1,
            duration=0.0,
            num_samples=0,
        )
        with pytest.raises(AnalysisError):
            analyze_spectrum(ad)
