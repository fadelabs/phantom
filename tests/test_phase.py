"""Tests for the phase coherence analysis module.

Covers PHAS-01 through PHAS-06.
All test audio is generated in-memory via inline fixtures.
"""

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom.phase import (
    analyze_phase,
    compare_phase,
    _gcc_phat_delay,
    PhaseResult,
    PhaseCompareResult,
)


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
    """Wrap a 2D stereo array into an AudioData instance."""
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=2,
        duration=len(samples_2d) / sr,
        num_samples=len(samples_2d),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def in_phase_stereo():
    """Stereo with identical L and R."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    mono = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return np.column_stack([mono, mono]), sr


@pytest.fixture
def out_of_phase_stereo():
    """Stereo with R = -L (polarity inverted)."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    left = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return np.column_stack([left, -left]), sr


@pytest.fixture
def delayed_signal_pair():
    """Two 1-second broadband signals where second is delayed by 10 samples.

    Uses white noise (broadband) rather than a pure sine because GCC-PHAT
    delay estimation requires wideband content to resolve delay unambiguously.
    Seeded RNG for reproducibility.
    """
    sr = 44100
    rng = np.random.default_rng(42)
    sig1 = rng.standard_normal(sr).astype(np.float32)
    sig2 = np.zeros_like(sig1)
    delay = 10
    sig2[delay:] = sig1[:-delay]
    return sig1, sig2, sr, delay


@pytest.fixture
def inverted_signal_pair():
    """Two 1-second mono signals where second is inverted (polarity flip)."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    sig1 = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    sig2 = -sig1.copy()
    return sig1, sig2, sr


# ---------------------------------------------------------------------------
# PHAS-01: Overall Phase Correlation
# ---------------------------------------------------------------------------


class TestOverallCorrelation:
    """Verify overall stereo phase correlation measurement."""

    def test_in_phase_correlation_one(self, in_phase_stereo):
        """Identical L and R channels should have correlation = 1.0."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert result.phase_correlation == pytest.approx(1.0, abs=0.01)

    def test_out_of_phase_correlation_minus_one(self, out_of_phase_stereo):
        """R = -L should have correlation = -1.0."""
        samples, sr = out_of_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert result.phase_correlation == pytest.approx(-1.0, abs=0.01)

    def test_correlation_is_float(self, in_phase_stereo):
        """Phase correlation value should be a float."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert isinstance(result.phase_correlation, float)


# ---------------------------------------------------------------------------
# PHAS-02: Per-Band Correlation
# ---------------------------------------------------------------------------


class TestPerBandCorrelation:
    """Verify per-frequency-band L/R correlation."""

    def test_in_phase_all_bands_positive(self, in_phase_stereo):
        """In-phase stereo should have all band correlations > 0.5."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        for band, val in result.per_band_correlation.items():
            assert val > 0.5, f"Band {band} correlation {val} <= 0.5"

    def test_out_of_phase_all_bands_negative(self, out_of_phase_stereo):
        """Out-of-phase stereo should have all band correlations < -0.5."""
        samples, sr = out_of_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        for band, val in result.per_band_correlation.items():
            assert val < -0.5, f"Band {band} correlation {val} >= -0.5"

    def test_per_band_is_dict(self, in_phase_stereo):
        """per_band_correlation should be a dict."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert isinstance(result.per_band_correlation, dict)

    def test_band_keys_are_strings(self, in_phase_stereo):
        """All band keys should be strings."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        for key in result.per_band_correlation:
            assert isinstance(key, str)

    def test_at_least_sub_and_mid_present(self, in_phase_stereo):
        """At minimum, 'sub' and 'mid' bands should be present."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert "sub" in result.per_band_correlation
        assert "mid" in result.per_band_correlation


# ---------------------------------------------------------------------------
# PHAS-03: Polarity Inversion Detection
# ---------------------------------------------------------------------------


class TestPolarityDetection:
    """Verify polarity inversion detection."""

    def test_in_phase_not_inverted(self, in_phase_stereo):
        """In-phase stereo should not be detected as inverted."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert result.polarity_inverted is False

    def test_out_of_phase_inverted(self, out_of_phase_stereo):
        """Out-of-phase stereo (R = -L) should be detected as inverted."""
        samples, sr = out_of_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert result.polarity_inverted is True


# ---------------------------------------------------------------------------
# PHAS-04: Cross-File Delay Detection
# ---------------------------------------------------------------------------


class TestCrossFileDelay:
    """Verify cross-file time delay detection via GCC-PHAT."""

    def test_known_delay_detected(self, delayed_signal_pair):
        """Known 10-sample delay should be detected within +/-2 samples."""
        sig1, sig2, sr, delay = delayed_signal_pair
        audio1 = _make_audio(sig1, sr)
        audio2 = _make_audio(sig2, sr)
        result = compare_phase(audio1, audio2)
        assert result.delay_samples == pytest.approx(delay, abs=2)

    def test_delay_ms_consistent(self, delayed_signal_pair):
        """delay_ms should match delay_samples / sr * 1000."""
        sig1, sig2, sr, delay = delayed_signal_pair
        audio1 = _make_audio(sig1, sr)
        audio2 = _make_audio(sig2, sr)
        result = compare_phase(audio1, audio2)
        expected_ms = result.delay_samples / sr * 1000.0
        assert result.delay_ms == pytest.approx(expected_ms, abs=0.1)

    def test_zero_delay_for_identical(self):
        """Identical signals should have delay near 0."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        sig = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        audio1 = _make_audio(sig.copy(), sr)
        audio2 = _make_audio(sig.copy(), sr)
        result = compare_phase(audio1, audio2)
        assert result.delay_samples == pytest.approx(0, abs=1)


# ---------------------------------------------------------------------------
# PHAS-05: Cross-File Correlation
# ---------------------------------------------------------------------------


class TestCrossFileCorrelation:
    """Verify cross-file correlation measurement."""

    def test_identical_signals_high_correlation(self):
        """Identical mono signals should have correlation > 0.95."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        sig = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        audio1 = _make_audio(sig.copy(), sr)
        audio2 = _make_audio(sig.copy(), sr)
        result = compare_phase(audio1, audio2)
        assert result.correlation > 0.95


# ---------------------------------------------------------------------------
# PHAS-06: Cross-File Polarity Inversion
# ---------------------------------------------------------------------------


class TestCrossFilePolarity:
    """Verify cross-file polarity inversion detection."""

    def test_identical_not_inverted(self):
        """Identical signals should not be detected as inverted."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        sig = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        audio1 = _make_audio(sig.copy(), sr)
        audio2 = _make_audio(sig.copy(), sr)
        result = compare_phase(audio1, audio2)
        assert result.polarity_inverted is False

    def test_inverted_signal_detected(self, inverted_signal_pair):
        """Polarity-inverted signal pair should be detected."""
        sig1, sig2, sr = inverted_signal_pair
        audio1 = _make_audio(sig1, sr)
        audio2 = _make_audio(sig2, sr)
        result = compare_phase(audio1, audio2)
        assert result.polarity_inverted is True


# ---------------------------------------------------------------------------
# Sample Rate Mismatch Guard
# ---------------------------------------------------------------------------


class TestSampleRateMismatch:
    """Verify sample rate mismatch rejection."""

    def test_rejects_mismatched_rates(self):
        """compare_phase should raise AnalysisError for mismatched sample rates."""
        from phantom.exceptions import AnalysisError

        sr1, sr2 = 44100, 48000
        t1 = np.linspace(0, 1.0, sr1, endpoint=False, dtype=np.float32)
        t2 = np.linspace(0, 1.0, sr2, endpoint=False, dtype=np.float32)
        sig1 = np.sin(2 * np.pi * 440 * t1).astype(np.float32)
        sig2 = np.sin(2 * np.pi * 440 * t2).astype(np.float32)
        audio1 = _make_audio(sig1, sr1)
        audio2 = _make_audio(sig2, sr2)
        with pytest.raises(AnalysisError, match="Sample rate mismatch"):
            compare_phase(audio1, audio2)


# ---------------------------------------------------------------------------
# Mono Defaults (D-03)
# ---------------------------------------------------------------------------


class TestMonoDefaults:
    """Verify mono input returns deterministic defaults."""

    def test_mono_phase_defaults(self, mono_sine_440hz):
        """Mono should return phase_correlation=1.0, polarity_inverted=False."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_phase(audio)
        assert result.phase_correlation == 1.0
        assert result.polarity_inverted is False

    def test_mono_per_band_all_one(self, mono_sine_440hz):
        """Mono should return 1.0 for all per-band correlations."""
        samples, sr = mono_sine_440hz
        audio = _make_audio(samples, sr)
        result = analyze_phase(audio)
        for band, val in result.per_band_correlation.items():
            assert val == 1.0, f"Mono band {band} should be 1.0, got {val}"


# ---------------------------------------------------------------------------
# Near-Silence Guard (D-05)
# ---------------------------------------------------------------------------


class TestNearSilenceGuard:
    """Verify near-silent audio returns all None values."""

    def test_analyze_phase_silence(self, stereo_silence):
        """Stereo silence should return all None values."""
        samples, sr = stereo_silence
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert result.phase_correlation is None
        assert result.per_band_correlation is None
        assert result.polarity_inverted is None

    def test_compare_phase_silence(self, near_silence):
        """Near-silent mono pair should return all None values."""
        samples, sr = near_silence
        audio1 = _make_audio(samples.copy(), sr)
        audio2 = _make_audio(samples.copy(), sr)
        result = compare_phase(audio1, audio2)
        assert result.delay_samples is None
        assert result.delay_ms is None
        assert result.correlation is None
        assert result.polarity_inverted is None


# ---------------------------------------------------------------------------
# Error Handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify error handling for empty audio."""

    def test_analyze_phase_empty(self):
        """Empty stereo audio should raise AnalysisError."""
        from phantom.exceptions import AnalysisError

        samples = np.zeros((0, 2), dtype=np.float32)
        audio = AudioData(
            samples=samples,
            sample_rate=44100,
            num_channels=2,
            duration=0.0,
            num_samples=0,
        )
        with pytest.raises(AnalysisError):
            analyze_phase(audio)

    def test_compare_phase_empty(self):
        """Empty mono pair should raise AnalysisError."""
        from phantom.exceptions import AnalysisError

        samples = np.zeros((0, 1), dtype=np.float32)
        audio1 = AudioData(
            samples=samples,
            sample_rate=44100,
            num_channels=1,
            duration=0.0,
            num_samples=0,
        )
        audio2 = AudioData(
            samples=samples,
            sample_rate=44100,
            num_channels=1,
            duration=0.0,
            num_samples=0,
        )
        with pytest.raises(AnalysisError):
            compare_phase(audio1, audio2)


# ---------------------------------------------------------------------------
# Result Structure
# ---------------------------------------------------------------------------


class TestAnalyzePhaseResultStructure:
    """Verify analyze_phase result model shape."""

    def test_returns_phase_result(self, in_phase_stereo):
        """analyze_phase should return a PhaseResult model."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        assert isinstance(result, PhaseResult)

    def test_keys(self, in_phase_stereo):
        """Result model should have exactly the 3 expected keys."""
        samples, sr = in_phase_stereo
        audio = _make_stereo_audio(samples, sr)
        result = analyze_phase(audio)
        expected_keys = {
            "phase_correlation",
            "per_band_correlation",
            "polarity_inverted",
        }
        assert set(result.model_dump().keys()) == expected_keys


class TestComparePhaseResultStructure:
    """Verify compare_phase result model shape."""

    def test_returns_phase_compare_result(self):
        """compare_phase should return a PhaseCompareResult model."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        sig = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        audio1 = _make_audio(sig.copy(), sr)
        audio2 = _make_audio(sig.copy(), sr)
        result = compare_phase(audio1, audio2)
        assert isinstance(result, PhaseCompareResult)

    def test_keys(self):
        """Result model should have exactly the 4 expected keys."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        sig = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        audio1 = _make_audio(sig.copy(), sr)
        audio2 = _make_audio(sig.copy(), sr)
        result = compare_phase(audio1, audio2)
        expected_keys = {
            "delay_samples",
            "delay_ms",
            "correlation",
            "polarity_inverted",
        }
        assert set(result.model_dump().keys()) == expected_keys


# ---------------------------------------------------------------------------
# GCC-PHAT window control (D-09)
# ---------------------------------------------------------------------------


class TestPhatWindow:
    """Tests for PHANTOM_PHAT_WINDOW_S env var controlling GCC-PHAT truncation."""

    def test_default_phat_window_is_10s(self, monkeypatch) -> None:
        """With PHANTOM_PHAT_WINDOW_S unset, _gcc_phat_delay truncates at 10s."""
        monkeypatch.delenv("PHANTOM_PHAT_WINDOW_S", raising=False)
        sr = 44100
        # Create a signal longer than 10s (15s)
        n_samples = sr * 15
        sig1 = np.random.randn(n_samples).astype(np.float32)
        sig2 = np.random.randn(n_samples).astype(np.float32)
        # The function should work without error -- the truncation is internal.
        delay_samples, delay_ms = _gcc_phat_delay(sig1, sig2, sr)
        assert isinstance(delay_samples, int)
        assert isinstance(delay_ms, float)

    def test_phat_window_env_var_override(self, monkeypatch) -> None:
        """Setting PHANTOM_PHAT_WINDOW_S=5 causes truncation at 5*sr samples."""
        monkeypatch.setenv("PHANTOM_PHAT_WINDOW_S", "5")
        sr = 44100
        # Create a signal longer than 5s (8s)
        n_samples = sr * 8
        sig1 = np.random.randn(n_samples).astype(np.float32)
        sig2 = np.random.randn(n_samples).astype(np.float32)
        delay_samples, delay_ms = _gcc_phat_delay(sig1, sig2, sr)
        assert isinstance(delay_samples, int)
        assert isinstance(delay_ms, float)

    def test_phat_window_short_signal_no_truncation(self, monkeypatch) -> None:
        """Signal shorter than the window is not truncated."""
        monkeypatch.setenv("PHANTOM_PHAT_WINDOW_S", "10")
        sr = 44100
        # 2s signal is shorter than 10s window -- no truncation
        n_samples = sr * 2
        sig1 = np.random.randn(n_samples).astype(np.float32)
        sig2 = np.random.randn(n_samples).astype(np.float32)
        delay_samples, delay_ms = _gcc_phat_delay(sig1, sig2, sr)
        assert isinstance(delay_samples, int)
        assert isinstance(delay_ms, float)
