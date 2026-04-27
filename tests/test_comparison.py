"""Tests for the reference comparison module.

Covers COMP-01 through COMP-05.
All test audio is generated in-memory via inline fixtures.
"""

import shutil
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from phantom.audio import AudioData
from phantom.comparison import (
    _check_mono_below,
    _normalize_band_energies,
    _rate_deviation,
    _rate_range_deviation,
    compare_to_profile,
    compare_to_reference,
    match_to_reference,
    ProfileComparisonResult,
    ReferenceComparisonResult,
    MatchResult,
    MatchAdjustments,
    MetricDiff,
    DeviationResult,
    RangeDeviationResult,
    LoudnessProfileComparisonSection,
    DynamicsComparisonSection,
    StereoProfileComparisonSection,
    LoudnessReferenceComparisonSection,
)
from phantom.exceptions import (
    AnalysisError,
    AudioLoadError,
    DependencyMissingError,
    PathSecurityError,
)
from phantom._profiles import (
    FrequencyTargets,
    LoudnessTargets,
    ReferenceProfile,
    SpatialConventions,
    StereoConventions,
)
from phantom.spectral import SpectralResult
from phantom.loudness import LoudnessResult
from phantom.dynamics import DynamicsResult
from phantom.stereo import StereoResult


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


def _make_stereo_audio(left: np.ndarray, right: np.ndarray, sr: int) -> AudioData:
    """Wrap left and right channel arrays into a stereo AudioData instance."""
    samples_2d = np.column_stack([left, right])
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=2,
        duration=len(left) / sr,
        num_samples=len(left),
    )


def _make_profile(**overrides) -> ReferenceProfile:
    """Build a ReferenceProfile with known defaults, applying any overrides."""
    defaults = {
        "genre": "test",
        "description": "Test profile for comparison tests",
        "loudness": LoudnessTargets(
            lufs_range=(-14.0, -8.0),
            crest_factor_range=(6.0, 12.0),
            true_peak_max_dbtp=-1.0,
        ),
        "frequency": FrequencyTargets(
            bands={
                "31_hz": 0.0,
                "62_hz": 0.0,
                "125_hz": 0.0,
                "250_hz": 0.0,
                "500_hz": 0.0,
                "1000_hz": 0.0,
                "2000_hz": 0.0,
                "4000_hz": 0.0,
                "8000_hz": 0.0,
                "16000_hz": 0.0,
            }
        ),
        "stereo": StereoConventions(width="moderate", mono_below_hz=120.0),
        "spatial": SpatialConventions(
            reverb_type="room", reverb_amount="moderate", pre_delay_ms="medium"
        ),
        "processing_notes": "Test profile.",
    }
    defaults.update(overrides)
    return ReferenceProfile(**defaults)


# ---------------------------------------------------------------------------
# TestDeviationRating -- unit tests for _rate_deviation and _rate_range_deviation
# ---------------------------------------------------------------------------


class TestDeviationRating:
    """Unit tests for deviation rating helpers."""

    def test_on_target(self):
        """abs deviation 0.2 (<= 1.0) should be 'on_target'."""
        result = _rate_deviation(value=-10.2, target=-10.0)
        assert result.value == -10.2
        assert result.target == -10.0
        assert result.deviation == pytest.approx(-0.2, abs=0.01)
        assert result.rating == "on_target"

    def test_slightly_above(self):
        """abs deviation 3.0 (<= 3.0 threshold) and positive should be 'slightly_above'."""
        result = _rate_deviation(value=-7.0, target=-10.0)
        assert result.rating == "slightly_above"
        assert result.deviation == pytest.approx(3.0, abs=0.01)

    def test_significantly_above(self):
        """abs deviation > 6.0 and positive should be 'significantly_above'."""
        result = _rate_deviation(value=-2.0, target=-10.0)
        assert result.rating == "significantly_above"
        assert result.deviation == pytest.approx(8.0, abs=0.01)

    def test_slightly_below(self):
        """abs deviation 2.0 in negative direction should be 'slightly_below'."""
        result = _rate_deviation(value=-12.0, target=-10.0)
        assert result.rating == "slightly_below"
        assert result.deviation == pytest.approx(-2.0, abs=0.01)

    def test_above_target(self):
        """abs deviation 5.0 should be 'above_target' (3 < abs <= 6)."""
        result = _rate_deviation(value=-5.0, target=-10.0)
        assert result.rating == "above_target"

    def test_below_target(self):
        """abs deviation 5.0 negative should be 'below_target' (3 < abs <= 6)."""
        result = _rate_deviation(value=-15.0, target=-10.0)
        assert result.rating == "below_target"

    def test_significantly_below(self):
        """abs deviation > 6 negative should be 'significantly_below'."""
        result = _rate_deviation(value=-20.0, target=-10.0)
        assert result.rating == "significantly_below"
        assert result.deviation == pytest.approx(-10.0, abs=0.01)

    def test_exact_match(self):
        """Exact match returns deviation 0.0 and 'on_target'."""
        result = _rate_deviation(value=-10.0, target=-10.0)
        assert result.deviation == 0.0
        assert result.rating == "on_target"

    def test_rounding(self):
        """Values should be rounded to 2 decimal places."""
        result = _rate_deviation(value=-10.123456, target=-10.0)
        assert result.value == -10.12
        assert result.deviation == -0.12

    def test_range_on_target(self):
        """Value within range should be 'on_target' with deviation 0.0."""
        result = _rate_range_deviation(value=7.5, target_range=(6.0, 12.0))
        assert result.rating == "on_target"
        assert result.deviation == 0.0
        assert result.value == 7.5
        assert result.target_range == [6.0, 12.0]

    def test_range_below(self):
        """Value below range min should give negative deviation from range min."""
        result = _rate_range_deviation(value=4.0, target_range=(6.0, 12.0))
        assert result.deviation == pytest.approx(-2.0, abs=0.01)
        assert result.rating == "slightly_below"

    def test_range_above(self):
        """Value above range max should give positive deviation from range max."""
        result = _rate_range_deviation(value=15.0, target_range=(6.0, 12.0))
        assert result.deviation == pytest.approx(3.0, abs=0.01)

    def test_range_at_min(self):
        """Value at range min is on target."""
        result = _rate_range_deviation(value=6.0, target_range=(6.0, 12.0))
        assert result.rating == "on_target"
        assert result.deviation == 0.0

    def test_range_at_max(self):
        """Value at range max is on target."""
        result = _rate_range_deviation(value=12.0, target_range=(6.0, 12.0))
        assert result.rating == "on_target"
        assert result.deviation == 0.0


# ---------------------------------------------------------------------------
# TestSpectralNormalization -- unit tests for _normalize_band_energies
# ---------------------------------------------------------------------------


class TestSpectralNormalization:
    """Unit tests for spectral band energy normalization."""

    def test_basic_normalization(self):
        """Normalizes values relative to mean (mean=15.0)."""
        result = _normalize_band_energies({"31_hz": 10.0, "62_hz": 20.0})
        assert result["31_hz"] == pytest.approx(-5.0, abs=0.01)
        assert result["62_hz"] == pytest.approx(5.0, abs=0.01)

    def test_all_equal(self):
        """All equal values should normalize to 0.0."""
        bands = {
            f"{f}_hz": 5.0
            for f in [31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        }
        result = _normalize_band_energies(bands)
        for v in result.values():
            assert v == pytest.approx(0.0, abs=0.01)

    def test_empty_dict(self):
        """Empty dict should return empty dict."""
        result = _normalize_band_energies({})
        assert result == {}

    def test_preserves_keys(self):
        """Output keys should match input keys."""
        bands = {"31_hz": -10.0, "62_hz": -5.0, "125_hz": 0.0}
        result = _normalize_band_energies(bands)
        assert set(result.keys()) == set(bands.keys())


# ---------------------------------------------------------------------------
# TestMonoBelowDetection -- tests for _check_mono_below
# ---------------------------------------------------------------------------


class TestMonoBelowDetection:
    """Tests for stereo bass content detection below a frequency cutoff."""

    def test_mono_audio_returns_correlation_one(self):
        """Mono audio should return correlation=1.0, has_stereo_bass=False."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        mono = _make_audio((0.5 * np.sin(2 * np.pi * 80 * t)).astype(np.float32), sr)
        result = _check_mono_below(mono, 120.0)
        assert result.bass_correlation == 1.0
        assert result.has_stereo_bass is False
        assert result.rating == "on_target"

    def test_correlated_bass_no_stereo(self):
        """Stereo audio with identical bass should have has_stereo_bass=False."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        bass = (0.5 * np.sin(2 * np.pi * 80 * t)).astype(np.float32)
        stereo = _make_stereo_audio(bass, bass, sr)
        result = _check_mono_below(stereo, 120.0)
        assert result.has_stereo_bass is False
        assert result.bass_correlation > 0.95

    def test_uncorrelated_bass_has_stereo(self):
        """Stereo audio with different bass channels should have has_stereo_bass=True."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        left_bass = (0.5 * np.sin(2 * np.pi * 80 * t)).astype(np.float32)
        right_bass = (0.5 * np.sin(2 * np.pi * 60 * t)).astype(np.float32)
        stereo = _make_stereo_audio(left_bass, right_bass, sr)
        result = _check_mono_below(stereo, 120.0)
        assert result.has_stereo_bass is True
        assert result.rating == "below_target"

    def test_near_silent_bass(self):
        """Near-silent bass (RMS < 1e-8) returns correlation=1.0."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        # Very low amplitude bass, should trigger the silence guard
        left = (1e-10 * np.sin(2 * np.pi * 80 * t)).astype(np.float32)
        right = (1e-10 * np.sin(2 * np.pi * 60 * t)).astype(np.float32)
        stereo = _make_stereo_audio(left, right, sr)
        result = _check_mono_below(stereo, 120.0)
        assert result.bass_correlation == 1.0
        assert result.has_stereo_bass is False


# ---------------------------------------------------------------------------
# TestCompareToProfile -- integration tests for compare_to_profile
# ---------------------------------------------------------------------------


class TestCompareToProfile:
    """Integration tests calling compare_to_profile with synthetic audio."""

    @pytest.fixture
    def profile(self):
        return _make_profile()

    @pytest.fixture
    def audio_3s(self):
        """3-second 440Hz sine at 0.5 amplitude, mono, 44100 Hz."""
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        return _make_audio(samples, sr)

    def test_returns_model_with_expected_attrs(self, audio_3s, profile):
        """Should return ProfileComparisonResult with loudness, frequency, dynamics, stereo."""
        result = compare_to_profile(audio_3s, profile)
        assert isinstance(result, ProfileComparisonResult)
        # All four sections should be present as non-None dicts
        assert result.loudness is not None
        assert result.frequency is not None
        assert result.dynamics is not None
        assert result.stereo is not None

    def test_loudness_section_is_typed(self, audio_3s, profile):
        """Loudness section should be a LoudnessProfileComparisonSection with typed fields."""
        result = compare_to_profile(audio_3s, profile)
        assert isinstance(result.loudness, LoudnessProfileComparisonSection)
        assert hasattr(result.loudness, "integrated_lufs")
        assert hasattr(result.loudness, "true_peak_dbtp")

    def test_loudness_deviation_structure(self, audio_3s, profile):
        """Each loudness deviation should be a typed model with value, deviation, rating."""
        result = compare_to_profile(audio_3s, profile)
        lufs = result.loudness.integrated_lufs
        assert isinstance(lufs, RangeDeviationResult)
        assert lufs.value is not None
        assert lufs.deviation is not None
        assert lufs.rating is not None

    def test_frequency_section_has_bands(self, audio_3s, profile):
        """Frequency section should have per-band DeviationResult objects."""
        result = compare_to_profile(audio_3s, profile)
        freq = result.frequency
        assert isinstance(freq, dict)
        # Should have at least some band keys
        assert "1000_hz" in freq

    def test_frequency_uses_normalized_values(self, audio_3s, profile):
        """Frequency comparison should use normalized (relative) band energies."""
        result = compare_to_profile(audio_3s, profile)
        freq = result.frequency
        # Each band entry should be a DeviationResult with value and rating
        for band_key, dev in freq.items():
            assert isinstance(dev, DeviationResult)
            assert dev.value is not None or dev.rating == "unmeasurable"

    def test_dynamics_section_is_typed(self, audio_3s, profile):
        """Dynamics section should be a typed DynamicsComparisonSection."""
        result = compare_to_profile(audio_3s, profile)
        assert isinstance(result.dynamics, DynamicsComparisonSection)
        assert hasattr(result.dynamics, "crest_factor_db")
        assert result.dynamics.crest_factor_db.target_range is not None

    def test_stereo_section_is_typed(self, audio_3s, profile):
        """Stereo section should be a typed StereoProfileComparisonSection."""
        result = compare_to_profile(audio_3s, profile)
        assert isinstance(result.stereo, StereoProfileComparisonSection)
        assert hasattr(result.stereo, "width")
        assert hasattr(result.stereo, "mono_below")

    def test_near_silent_audio(self, profile):
        """Near-silent audio returns result with None-safe handling (no crash)."""
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        silent = _make_audio(
            (1e-6 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        result = compare_to_profile(silent, profile)
        # Should not crash, should return a result model
        assert isinstance(result, ProfileComparisonResult)

    def test_no_score_key(self, audio_3s, profile):
        """No overall match score anywhere in result (per D-03)."""
        result = compare_to_profile(audio_3s, profile)
        result_str = str(result)
        assert "score" not in result_str.lower()

    def test_width_moderate_maps_to_range(self, audio_3s):
        """Width descriptor 'moderate' should map to range (0.3, 0.7)."""
        profile = _make_profile(
            stereo=StereoConventions(width="moderate", mono_below_hz=120.0)
        )
        result = compare_to_profile(audio_3s, profile)
        width = result.stereo.width
        assert width.target_range == [0.3, 0.7]


# ---------------------------------------------------------------------------
# TestCompareToReference -- integration tests for compare_to_reference
# ---------------------------------------------------------------------------


class TestCompareToReference:
    """Integration tests calling compare_to_reference with synthetic AudioData."""

    @pytest.fixture
    def audio_3s(self):
        """3-second 440Hz sine at 0.5 amplitude, mono, 44100 Hz."""
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        return _make_audio(samples, sr)

    @pytest.fixture
    def audio_3s_different(self):
        """3-second 1000Hz sine at 0.3 amplitude, mono, 44100 Hz."""
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        samples = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        return _make_audio(samples, sr)

    def test_returns_model_with_expected_attrs(self, audio_3s):
        """Should return ReferenceComparisonResult with loudness, frequency, dynamics, stereo."""
        result = compare_to_reference(audio_3s, audio_3s)
        assert isinstance(result, ReferenceComparisonResult)
        assert result.loudness is not None
        assert result.frequency is not None
        assert result.dynamics is not None
        assert result.stereo is not None

    def test_frequency_uses_normalized_energies(self, audio_3s):
        """Frequency section should use normalized band energies (COMP-04)."""
        result = compare_to_reference(audio_3s, audio_3s)
        freq = result.frequency
        # Each band should be a DeviationResult
        for band_key, dev in freq.items():
            assert isinstance(dev, DeviationResult)
            assert dev.value is not None or dev.rating == "unmeasurable"
            assert dev.reference is not None or dev.rating == "unmeasurable"

    def test_identical_audio_all_on_target(self, audio_3s):
        """Comparing identical audio should return all deviations as 'on_target'."""
        result = compare_to_reference(audio_3s, audio_3s)
        # All loudness deviations should be on_target (via typed model)
        assert isinstance(result.loudness, LoudnessReferenceComparisonSection)
        for key in ("integrated_lufs", "true_peak_dbtp", "loudness_range_lu"):
            dev = getattr(result.loudness, key)
            assert dev.rating == "on_target", f"loudness.{key} not on_target"
        # All frequency deviations should be on_target
        for key, dev in result.frequency.items():
            assert dev.rating == "on_target", f"frequency.{key} not on_target"

    def test_different_audio_non_zero_deviations(self, audio_3s, audio_3s_different):
        """Comparing different audio should produce non-zero deviations."""
        result = compare_to_reference(audio_3s, audio_3s_different)
        # Check across all sections -- now typed models
        has_nonzero = False
        # Check loudness
        if result.loudness is not None:
            for key in ("integrated_lufs", "true_peak_dbtp", "loudness_range_lu"):
                dev = getattr(result.loudness, key)
                if dev.deviation is not None and dev.deviation != 0.0:
                    has_nonzero = True
                    break
        # Check frequency
        if not has_nonzero and result.frequency is not None:
            for key, dev in result.frequency.items():
                if dev.deviation is not None and dev.deviation != 0.0:
                    has_nonzero = True
                    break
        assert has_nonzero, "Expected at least one non-zero deviation"

    def test_empty_sample_audio_raises(self):
        """Empty-sample audio should raise AnalysisError."""
        sr = 44100
        empty = AudioData(
            samples=np.zeros((0, 1), dtype=np.float32),
            sample_rate=sr,
            num_channels=1,
            duration=0.0,
            num_samples=0,
        )
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        audible = _make_audio(
            (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        with pytest.raises(AnalysisError):
            compare_to_reference(empty, audible)

    def test_no_score_key(self, audio_3s):
        """No overall match score anywhere in result (per D-03)."""
        result = compare_to_reference(audio_3s, audio_3s)
        result_str = str(result)
        assert "score" not in result_str.lower()

    def test_loudness_uses_reference_key(self, audio_3s, audio_3s_different):
        """Reference comparison should use 'reference' field instead of 'target'."""
        result = compare_to_reference(audio_3s, audio_3s_different)
        lufs = result.loudness.integrated_lufs
        assert lufs.reference is not None


# ---------------------------------------------------------------------------
# TestEdgeCases -- edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases: near-silent, empty, mono."""

    def test_empty_samples_profile_raises(self):
        """compare_to_profile with empty samples raises AnalysisError."""
        profile = _make_profile()
        sr = 44100
        empty = AudioData(
            samples=np.zeros((0, 1), dtype=np.float32),
            sample_rate=sr,
            num_channels=1,
            duration=0.0,
            num_samples=0,
        )
        with pytest.raises(AnalysisError):
            compare_to_profile(empty, profile)

    def test_near_silent_profile_no_crash(self):
        """compare_to_profile with near-silent audio should not crash."""
        profile = _make_profile()
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        silent = _make_audio(
            (1e-6 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        result = compare_to_profile(silent, profile)
        assert isinstance(result, ProfileComparisonResult)

    def test_mono_input_profile(self):
        """compare_to_profile with mono input should work without crashing."""
        profile = _make_profile()
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        mono = _make_audio((0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr)
        result = compare_to_profile(mono, profile)
        assert isinstance(result, ProfileComparisonResult)
        assert result.stereo is not None

    def test_near_silent_reference_no_crash(self):
        """compare_to_reference with near-silent audio should not crash."""
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        silent = _make_audio(
            (1e-6 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        audible = _make_audio(
            (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32), sr
        )
        result = compare_to_reference(silent, audible)
        assert isinstance(result, ReferenceComparisonResult)


# ---------------------------------------------------------------------------
# TestMatchToReference -- tests for match_to_reference (COMP-05)
# ---------------------------------------------------------------------------


class TestProfileComparisonUnmeasuredBands:
    """S-WR-05: Profile comparison emits unmeasurable for missing measured bands."""

    def test_profile_comparison_includes_unmeasured_bands(self):
        """Profile has a band not in spectrum -> that band gets 'unmeasurable' rating."""
        from phantom._profiles import FrequencyTargets

        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        audio = _make_audio(samples, sr)

        # Create profile with an extra band "20000_hz" not in standard spectrum output
        bands = {
            "31_hz": 0.0,
            "62_hz": 0.0,
            "125_hz": 0.0,
            "250_hz": 0.0,
            "500_hz": 0.0,
            "1000_hz": 0.0,
            "2000_hz": 0.0,
            "4000_hz": 0.0,
            "8000_hz": 0.0,
            "16000_hz": 0.0,
            "20000_hz": 0.0,
        }
        profile = _make_profile(frequency=FrequencyTargets(bands=bands))
        result = compare_to_profile(audio, profile)
        freq = result.frequency
        assert "20000_hz" in freq
        assert freq["20000_hz"].rating == "unmeasurable"


class TestReferenceComparisonUnionBands:
    """S-WR-06: Reference comparison uses band union."""

    def test_reference_comparison_union_bands(self):
        """When spectrum analysis produces different band sets, all appear in result."""
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        samples_a = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        samples_b = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        audio_a = _make_audio(samples_a, sr)
        audio_b = _make_audio(samples_b, sr)

        # Both should produce the same standard bands, so patch one to have an extra
        with patch("phantom.comparison.analyze_spectrum") as mock_spec:
            bands_a = {"500_hz": -10.0, "1000_hz": -12.0, "extra_hz": -15.0}
            bands_b = {"500_hz": -11.0, "1000_hz": -13.0}
            mock_spec.side_effect = [
                SpectralResult(
                    octave_band_energy_db=bands_a, spectral_centroid_hz=500.0
                ),
                SpectralResult(
                    octave_band_energy_db=bands_b, spectral_centroid_hz=500.0
                ),
            ]
            with (
                patch("phantom.comparison.analyze_loudness") as mock_loud,
                patch("phantom.comparison.analyze_dynamics") as mock_dyn,
                patch("phantom.comparison.analyze_stereo") as mock_st,
            ):
                mock_loud.return_value = LoudnessResult(
                    integrated_lufs=-14.0, true_peak_dbtp=-1.0, loudness_range_lu=6.0
                )
                mock_dyn.return_value = DynamicsResult(
                    rms_dbfs=-18.0, crest_factor_db=10.0, dynamic_range_db=20.0
                )
                mock_st.return_value = StereoResult(correlation=1.0, stereo_width=0.5)
                result = compare_to_reference(audio_a, audio_b)

        freq = result.frequency
        assert "500_hz" in freq
        assert "1000_hz" in freq
        assert "extra_hz" in freq
        assert freq["extra_hz"].rating == "unmeasurable"


class TestMatchToReferenceOverwrite:
    """X-WR-04: match_to_reference rejects existing output file."""

    def test_match_to_reference_rejects_existing_output(
        self, tmp_path, wav_file_factory
    ):
        """Creating output file before calling match_to_reference raises AnalysisError."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        target_path = wav_file_factory(samples.reshape(-1, 1), sr)
        ref_path = wav_file_factory(samples.reshape(-1, 1), sr)
        output_path = str(tmp_path / "already_exists.wav")
        # Create the output file before calling
        with open(output_path, "w") as f:
            f.write("existing")

        mock_mg = MagicMock()
        with patch.dict("sys.modules", {"matchering": mock_mg}):
            with pytest.raises(AnalysisError, match="already exists"):
                match_to_reference(target_path, ref_path, output_path)


class TestMatchToReference:
    """Tests for Matchering-based reference matching (COMP-05)."""

    def test_missing_matchering_raises_dependency_error(self, monkeypatch):
        """When matchering is not installed, DependencyMissingError is raised."""
        import builtins
        import sys

        # Clear cached modules so monkeypatched __import__ is actually called
        monkeypatch.delitem(sys.modules, "matchering", raising=False)

        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "matchering":
                raise ImportError("No module named 'matchering'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _mock_import)

        with pytest.raises(DependencyMissingError) as exc_info:
            match_to_reference("a.wav", "b.wav", "c.wav")
        assert 'pip install "phantom-audio[matching]"' in str(exc_info.value)

    def test_missing_target_raises_file_not_found(self, tmp_path, wav_file_factory):
        """AudioLoadError when target_path does not exist."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        ref_samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        ref_path = wav_file_factory(ref_samples.reshape(-1, 1), sr)
        nonexistent = str(tmp_path / "nonexistent.wav")

        mock_mg = MagicMock()
        with patch.dict("sys.modules", {"matchering": mock_mg}):
            with pytest.raises(AudioLoadError, match="Target file not found"):
                match_to_reference(nonexistent, ref_path, str(tmp_path / "out.wav"))

    def test_missing_reference_raises_file_not_found(self, tmp_path, wav_file_factory):
        """AudioLoadError when reference_path does not exist."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        target_samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        target_path = wav_file_factory(target_samples.reshape(-1, 1), sr)
        nonexistent = str(tmp_path / "nonexistent_ref.wav")

        mock_mg = MagicMock()
        with patch.dict("sys.modules", {"matchering": mock_mg}):
            with pytest.raises(AudioLoadError, match="Reference file not found"):
                match_to_reference(target_path, nonexistent, str(tmp_path / "out.wav"))

    def test_successful_match_returns_adjustment_summary(
        self, tmp_path, wav_file_factory
    ):
        """Successful match returns MatchResult with output_path and adjustments."""
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        target_samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        ref_samples = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)

        target_path = wav_file_factory(target_samples.reshape(-1, 1), sr)
        ref_path = wav_file_factory(ref_samples.reshape(-1, 1), sr)
        output_path = str(tmp_path / "matched_output.wav")

        # Mock matchering: mg.process copies target to output
        mock_mg = MagicMock()

        def _mock_process(target, reference, results, **kwargs):
            shutil.copy(target, output_path)

        mock_mg.process = _mock_process
        mock_mg.pcm24 = MagicMock(return_value="pcm24_result")

        with patch.dict("sys.modules", {"matchering": mock_mg}):
            result = match_to_reference(target_path, ref_path, output_path)

        assert isinstance(result, MatchResult)
        assert result.output_path == output_path
        assert isinstance(result.adjustments, MatchAdjustments)
        lufs = result.adjustments.integrated_lufs
        assert isinstance(lufs, MetricDiff)
        assert lufs.before is not None
        assert lufs.after is not None
        assert lufs.change is not None

    def test_matchering_error_wrapped_in_analysis_error(
        self, tmp_path, wav_file_factory
    ):
        """Matchering errors are wrapped in AnalysisError."""
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        target_samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        ref_samples = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)

        target_path = wav_file_factory(target_samples.reshape(-1, 1), sr)
        ref_path = wav_file_factory(ref_samples.reshape(-1, 1), sr)
        output_path = str(tmp_path / "matched_output.wav")

        # Mock matchering: mg.process raises an exception
        mock_mg = MagicMock()
        mock_mg.process.side_effect = RuntimeError("Matchering internal error")
        mock_mg.pcm24 = MagicMock(return_value="pcm24_result")

        with patch.dict("sys.modules", {"matchering": mock_mg}):
            with pytest.raises(AnalysisError, match="Reference matching failed"):
                match_to_reference(target_path, ref_path, output_path)

    def test_function_signature(self, tmp_path):
        """match_to_reference accepts exactly 3 positional string args."""
        # Calling with keyword args to verify the signature; AudioLoadError
        # is expected -- we're just verifying it accepts these parameter names.
        mock_mg = MagicMock()
        with patch.dict("sys.modules", {"matchering": mock_mg}):
            with pytest.raises(AudioLoadError):
                match_to_reference(
                    target_path=str(tmp_path / "a.wav"),
                    reference_path=str(tmp_path / "b.wav"),
                    output_path=str(tmp_path / "c.wav"),
                )


class TestCompareToProfileSerialization:
    """Verify that compare_to_profile model_dump output produces correct nested structure."""

    @pytest.fixture
    def audio_3s(self):
        sr = 44100
        t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        return _make_audio(samples, sr)

    def test_model_dump_keys_match_previous_structure(self, audio_3s):
        """model_dump() should produce the same key structure as the previous dict output."""
        profile = _make_profile()
        result = compare_to_profile(audio_3s, profile)
        d = result.model_dump()
        # Top-level keys
        assert set(d.keys()) == {"loudness", "frequency", "dynamics", "stereo"}
        # Loudness keys
        assert set(d["loudness"].keys()) == {"integrated_lufs", "true_peak_dbtp"}
        # Loudness sub-entry keys
        assert "value" in d["loudness"]["integrated_lufs"]
        assert "target_range" in d["loudness"]["integrated_lufs"]
        assert "deviation" in d["loudness"]["integrated_lufs"]
        assert "rating" in d["loudness"]["integrated_lufs"]
        # Dynamics
        assert "crest_factor_db" in d["dynamics"]
        # Stereo
        assert "width" in d["stereo"]
        assert "mono_below" in d["stereo"]

    def test_serialization_round_trip(self, audio_3s):
        """model_dump -> reconstruct -> model_dump should be identical."""
        profile = _make_profile()
        result = compare_to_profile(audio_3s, profile)
        d = result.model_dump()
        reconstructed = ProfileComparisonResult(**d)
        assert reconstructed.model_dump() == d


class TestMatchOutputValidation:
    """Tests for PHANTOM_OUTPUT_DIR validation in match_to_reference()."""

    def test_match_output_rejected_when_outside(self, tmp_path, monkeypatch):
        """match_to_reference rejects output_path outside PHANTOM_OUTPUT_DIR."""
        allowed = tmp_path / "allowed"
        allowed.mkdir()
        monkeypatch.setenv("PHANTOM_OUTPUT_DIR", str(allowed))
        target = tmp_path / "target.wav"
        target.write_bytes(b"fake")
        ref = tmp_path / "ref.wav"
        ref.write_bytes(b"fake")
        with pytest.raises(PathSecurityError, match="outside the allowed directory"):
            match_to_reference(
                str(target), str(ref), str(tmp_path / "forbidden" / "out.wav")
            )

    def test_match_output_unrestricted_without_env(self, monkeypatch, tmp_path):
        """match_to_reference does not restrict output when PHANTOM_OUTPUT_DIR unset (D-11)."""
        monkeypatch.delenv("PHANTOM_OUTPUT_DIR", raising=False)
        try:
            match_to_reference(
                "/nonexistent/t.wav", "/nonexistent/r.wav", "/any/out.wav"
            )
        except PathSecurityError:
            pytest.fail("PathSecurityError raised when PHANTOM_OUTPUT_DIR is unset")
        except Exception:
            pass  # Expected: DependencyMissingError or AudioLoadError
