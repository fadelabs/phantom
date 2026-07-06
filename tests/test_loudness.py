"""Tests for the loudness measurement module.

Covers LOUD-01 through LOUD-05 plus D-08 pyloudnorm cross-validation.
All test audio is generated in-memory via conftest fixtures.
"""

import numpy as np
import pyloudnorm as pyln
import pytest

from phantom.audio import AudioData
from phantom.loudness import LoudnessResult, LufsStats, analyze_loudness


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
    """Verify short-term (3s) and momentary (400ms) LUFS are LufsStats."""

    def test_short_term_lufs_is_stats(self, sine_1khz_minus23lufs):
        """Short-term LUFS should be a LufsStats with count > 0."""
        samples, sr = sine_1khz_minus23lufs
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert isinstance(result.short_term_lufs, LufsStats)
        assert result.short_term_lufs.count > 0
        for field in ("min", "max", "mean", "p5", "p25", "p50", "p75", "p95"):
            assert isinstance(getattr(result.short_term_lufs, field), float)

    def test_momentary_lufs_is_stats(self, sine_1khz_minus23lufs):
        """Momentary LUFS should be a LufsStats with count > 0."""
        samples, sr = sine_1khz_minus23lufs
        audio = _make_audio(samples, sr)
        result = analyze_loudness(audio)

        assert isinstance(result.momentary_lufs, LufsStats)
        assert result.momentary_lufs.count > 0
        for field in ("min", "max", "mean", "p5", "p25", "p50", "p75", "p95"):
            assert isinstance(getattr(result.momentary_lufs, field), float)


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

        # short_term_lufs and momentary_lufs should serialize as dicts, not lists
        dumped = result.model_dump()
        assert isinstance(dumped["short_term_lufs"], dict)
        assert "min" in dumped["short_term_lufs"]
        assert "max" in dumped["short_term_lufs"]
        assert "mean" in dumped["short_term_lufs"]
        assert "count" in dumped["short_term_lufs"]
        assert isinstance(dumped["momentary_lufs"], dict)


# ---------------------------------------------------------------------------
# LufsStats unit tests
# ---------------------------------------------------------------------------


class TestLufsStats:
    """Verify LufsStats construction from arrays."""

    def test_from_array_none(self):
        """LufsStats.from_array(None) should return None."""
        assert LufsStats.from_array(None) is None

    def test_from_array_empty(self):
        """LufsStats.from_array([]) should return None."""
        assert LufsStats.from_array([]) is None

    def test_from_array_single(self):
        """Single-element array: min == max == mean, count == 1."""
        stats = LufsStats.from_array([-23.0])
        assert stats is not None
        assert stats.min == -23.0
        assert stats.max == -23.0
        assert stats.mean == -23.0
        assert stats.count == 1

    def test_from_array_percentiles(self):
        """Percentile p50 of range(-30, -20) should be near -25.0."""
        values = list(range(-30, -20))
        stats = LufsStats.from_array([float(v) for v in values])
        assert stats is not None
        assert stats.p50 == pytest.approx(-25.5, abs=1.0)

    def test_values_are_rounded(self):
        """All float fields should have at most 2 decimal places."""
        values = [-23.456789, -22.123456, -21.987654]
        stats = LufsStats.from_array(values)
        assert stats is not None
        for field in ("min", "max", "mean", "p5", "p25", "p50", "p75", "p95"):
            val = getattr(stats, field)
            # Check at most 2 decimal places
            assert val == round(val, 2)


# ---------------------------------------------------------------------------
# Shared true-peak (P-02 + P-06): compute once, byte-identical to legacy
# ---------------------------------------------------------------------------


def _asymmetric_stereo(sr: int = 44100) -> AudioData:
    """Asymmetric stereo fixture: left near full scale, right much quieter.

    Distinct per-channel content proves that reusing a single
    TruePeakDetector across channels stays stateless (parity gate).
    """
    t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
    left = (0.95 * np.sin(2 * np.pi * 14700 * t)).astype(np.float32)
    right = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    stereo = np.column_stack([left, right])
    return AudioData(
        samples=stereo,
        sample_rate=sr,
        num_channels=2,
        duration=len(left) / sr,
        num_samples=len(left),
    )


class TestSharedTruePeak:
    """P-02 + P-06: true peak computed once, byte-identical to per-channel legacy."""

    def test_true_peak_matches_legacy_perchannel(self):
        """dBTP must match a fresh-per-channel detector to <1e-6 on asymmetric stereo.

        This also validates that reusing ONE TruePeakDetector across the two
        channels (P-06) is safe: if Essentia were stateful across calls, the
        shared-detector path would diverge from this per-channel-fresh legacy.
        """
        import essentia.standard as es

        audio = _asymmetric_stereo()
        samples = audio.samples
        sr = audio.sample_rate

        eps = np.finfo(np.float32).eps
        peaks = []
        for ch in range(2):
            tp = es.TruePeakDetector(version=4, sampleRate=sr, oversamplingFactor=4)
            _, o = tp(samples[:, ch])
            peaks.append(float(np.max(np.abs(o))))
        legacy = float(20 * np.log10(max(peaks) + eps))

        result = analyze_loudness(audio)
        # LoudnessResult rounds true_peak_dbtp to 1 decimal via round_db, so
        # compare against the same rounding of the legacy value.
        from phantom._rounding import round_db

        assert abs(result.true_peak_dbtp - round_db(legacy)) < 1e-6

    def test_true_peak_computed_once(self, monkeypatch):
        """analyze_loudness then detect_problems on the SAME AudioData constructs
        es.TruePeakDetector exactly once.

        Spy on the essentia constructor and count instances built across both
        calls. On the shared-memo implementation this is 1; on the legacy code
        (two independent per-channel loops) it is 4 for stereo.
        """
        import essentia.standard as es
        import phantom.problems as problems_mod
        from phantom.loudness import es as loudness_es

        calls = {"n": 0}
        real_ctor = es.TruePeakDetector

        def _counting_ctor(*args, **kwargs):
            calls["n"] += 1
            return real_ctor(*args, **kwargs)

        # Patch the name where each module looks it up (both import es).
        monkeypatch.setattr(loudness_es, "TruePeakDetector", _counting_ctor)
        monkeypatch.setattr(problems_mod.es, "TruePeakDetector", _counting_ctor)

        audio = _asymmetric_stereo()
        analyze_loudness(audio)
        problems_mod.detect_problems(audio)

        assert calls["n"] == 1, (
            f"Expected TruePeakDetector constructed exactly once across "
            f"analyze_loudness + detect_problems on the same AudioData, "
            f"got {calls['n']}"
        )
