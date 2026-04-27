"""Tests for the stereo field analysis module.

Covers STER-01 through STER-06: L/R correlation, stereo width, mid/side
energy ratio, L/R energy balance, panorama distribution, and mono defaults.
All test audio is generated in-memory via inline fixtures and conftest.
"""

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom.stereo import analyze_stereo, StereoResult, PanoramaDistribution


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


def _make_stereo_audio(samples_2d: np.ndarray, sr: int) -> AudioData:
    """Wrap a 2D stereo array [N, 2] into an AudioData instance."""
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=2,
        duration=len(samples_2d) / sr,
        num_samples=len(samples_2d),
    )


# ---------------------------------------------------------------------------
# Inline stereo fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def identical_stereo():
    """Stereo with identical L and R (mono-duplicated)."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    mono = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return np.column_stack([mono, mono]), sr


@pytest.fixture
def inverted_stereo():
    """Stereo with R = -L (inverted polarity)."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    left = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return np.column_stack([left, -left]), sr


@pytest.fixture
def hard_left_stereo():
    """Stereo with signal only in left channel."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    left = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    right = np.zeros(sr, dtype=np.float32)
    return np.column_stack([left, right]), sr


@pytest.fixture
def right_louder_stereo():
    """Stereo with right channel 2x amplitude of left."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    left = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    right = (0.6 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return np.column_stack([left, right]), sr


# ---------------------------------------------------------------------------
# STER-01: L/R Correlation
# ---------------------------------------------------------------------------


class TestCorrelation:
    """Verify L/R correlation measurement."""

    def test_identical_channels_correlation_one(self, identical_stereo):
        """Identical L and R channels should have correlation = 1.0."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.correlation == pytest.approx(1.0, abs=0.01)

    def test_inverted_channels_correlation_minus_one(self, inverted_stereo):
        """R = -L should have correlation = -1.0."""
        samples, sr = inverted_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.correlation == pytest.approx(-1.0, abs=0.01)

    def test_correlation_is_float(self, identical_stereo):
        """Correlation value should be a float."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert isinstance(result.correlation, float)


# ---------------------------------------------------------------------------
# STER-02: Stereo Width
# ---------------------------------------------------------------------------


class TestWidth:
    """Verify stereo width (side/mid energy ratio) measurement."""

    def test_identical_channels_width_zero(self, identical_stereo):
        """Identical L and R => no side energy => width = 0.0."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.stereo_width == pytest.approx(0.0, abs=0.01)

    def test_hard_panned_width_above_half(self, hard_left_stereo):
        """Signal only in left channel => width > 0.5."""
        samples, sr = hard_left_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.stereo_width > 0.5

    def test_width_is_float(self, identical_stereo):
        """Width value should be a float."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert isinstance(result.stereo_width, float)


# ---------------------------------------------------------------------------
# STER-03: Mid/Side Energy Ratio
# ---------------------------------------------------------------------------


class TestMidSide:
    """Verify mid/side energy ratio measurement."""

    def test_identical_channels_ratio_none(self, identical_stereo):
        """Identical L and R => no side energy => ratio = None (JSON-safe)."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.mid_side_ratio_db is None

    def test_mid_side_ratio_is_float_or_none(self, hard_left_stereo):
        """Mid/side ratio should be a float or None (JSON-safe)."""
        samples, sr = hard_left_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.mid_side_ratio_db is None or isinstance(
            result.mid_side_ratio_db, float
        )


# ---------------------------------------------------------------------------
# STER-04: L/R Energy Balance
# ---------------------------------------------------------------------------


class TestBalance:
    """Verify L/R energy balance measurement."""

    def test_left_louder_negative_balance(self, stereo_sine_440hz):
        """stereo_sine_440hz has L=full, R=0.5x => balance_db < 0.0 (left louder)."""
        samples, sr = stereo_sine_440hz
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.balance_db < 0.0

    def test_right_louder_positive_balance(self, right_louder_stereo):
        """Right channel 2x amplitude => balance_db > 0.0."""
        samples, sr = right_louder_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.balance_db > 0.0

    def test_balance_is_float(self, identical_stereo):
        """Balance value should be a float."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert isinstance(result.balance_db, float)


# ---------------------------------------------------------------------------
# STER-05: Panorama Distribution
# ---------------------------------------------------------------------------


class TestPanorama:
    """Verify panorama distribution (left/center/right percentages)."""

    def test_centered_signal_mostly_center(self, identical_stereo):
        """Identical L and R => most energy in center."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.panorama_pct.center > 80.0

    def test_hard_left_mostly_left(self, hard_left_stereo):
        """Signal only in left channel => most energy panned left."""
        samples, sr = hard_left_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert result.panorama_pct.left > 80.0

    def test_panorama_keys(self, identical_stereo):
        """Panorama model should have left, center, right fields."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert set(result.panorama_pct.model_dump().keys()) == {
            "left",
            "center",
            "right",
        }

    def test_panorama_sums_near_100(self, identical_stereo):
        """Panorama percentages should sum to ~100."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        total = sum(result.panorama_pct.model_dump().values())
        assert total == pytest.approx(100.0, abs=1.0)


# ---------------------------------------------------------------------------
# STER-06: Mono Defaults (per D-03)
# ---------------------------------------------------------------------------


class TestMonoDefaults:
    """Verify mono input returns exact D-03 defaults without computation."""

    def test_mono_returns_defaults(self, mono_sine_440hz):
        """Mono input should return deterministic D-03 defaults."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_stereo(audio)

        assert result.correlation == 1.0
        assert result.stereo_width == 0.0
        assert result.mid_side_ratio_db is None
        assert result.balance_db == 0.0
        assert result.panorama_pct == PanoramaDistribution(
            left=0.0,
            center=100.0,
            right=0.0,
        )


# ---------------------------------------------------------------------------
# Near-silence guard
# ---------------------------------------------------------------------------


class TestNearSilenceGuard:
    """Near-silent stereo audio should return None for all values."""

    def test_stereo_silence_all_none(self, stereo_silence):
        """Stereo silence => all result values None."""
        samples, sr = stereo_silence
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)

        assert result.correlation is None
        assert result.stereo_width is None
        assert result.mid_side_ratio_db is None
        assert result.balance_db is None
        assert result.panorama_pct is None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify error handling for invalid input."""

    def test_empty_stereo_raises(self):
        """Empty stereo audio should raise AnalysisError."""
        samples = np.zeros((0, 2), dtype=np.float32)
        audio = _make_stereo_audio(samples, sr=44100)
        with pytest.raises(AnalysisError):
            analyze_stereo(audio)


# ---------------------------------------------------------------------------
# Result structure
# ---------------------------------------------------------------------------


class TestResultStructure:
    """Verify result model shape and field naming."""

    def test_returns_stereo_result(self, identical_stereo):
        """analyze_stereo should return a StereoResult model."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        assert isinstance(result, StereoResult)

    def test_all_keys_present(self, identical_stereo):
        """Result model should have exactly the 5 expected keys."""
        samples, sr = identical_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_stereo(audio)
        expected_keys = {
            "correlation",
            "stereo_width",
            "mid_side_ratio_db",
            "balance_db",
            "panorama_pct",
        }
        assert set(result.model_dump().keys()) == expected_keys
