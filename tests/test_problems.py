"""Tests for the problem detection module.

Covers PROB-01 through PROB-06, PROB-11, PROB-12.
All test audio is generated in-memory via conftest fixtures.
"""

import numpy as np
import pytest

from phantom.audio import AudioData
from phantom.problems import detect_problems, ProblemsResult, _detect_hum


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
    """Wrap a 2D stereo signal into an AudioData instance."""
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=samples_2d.shape[1],
        duration=samples_2d.shape[0] / sr,
        num_samples=samples_2d.shape[0],
    )


# ---------------------------------------------------------------------------
# Result Structure (D-03, D-04, D-05)
# ---------------------------------------------------------------------------


class TestResultStructure:
    """Verify result model shape and key naming."""

    def test_returns_model(self, mono_sine_440hz):
        """detect_problems should return a ProblemsResult model."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        assert isinstance(result, ProblemsResult)

    def test_all_top_level_keys_present(self, mono_sine_440hz):
        """Result should have exactly the 3 expected fields."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        assert set(result.model_dump().keys()) == {"problems", "clean", "summary"}

    def test_summary_keys_present(self, mono_sine_440hz):
        """Summary should have severity tier counts plus total."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        expected = {"dealbreaker", "significant", "moderate", "minor", "total"}
        assert set(result.summary.model_dump().keys()) == expected

    def test_problem_item_fields(self, clipped_sine):
        """Each problem should have type, severity, message, details fields."""
        samples, sr = clipped_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        assert len(result.problems) > 0
        for problem in result.problems:
            assert set(problem.model_dump().keys()) == {
                "type",
                "severity",
                "message",
                "details",
            }

    def test_severity_is_valid_tier(self, clipped_sine):
        """Severity must be one of the 4 valid tiers."""
        samples, sr = clipped_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        valid_severities = {"dealbreaker", "significant", "moderate", "minor"}
        for problem in result.problems:
            assert problem.severity in valid_severities


# ---------------------------------------------------------------------------
# PROB-01: Clipping Detection
# ---------------------------------------------------------------------------


class TestClipping:
    """Verify clipping detection at +/-1.0."""

    def test_clipped_signal_detected(self, clipped_sine):
        """Clipped sine (amp 1.2 clipped to [-1,1]) -> clipping problem found."""
        samples, sr = clipped_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        clipping_problems = [p for p in result.problems if p.type == "clipping"]
        assert len(clipping_problems) == 1

    def test_clipping_severity_is_dealbreaker(self, clipped_sine):
        """Clipping should always be severity=dealbreaker."""
        samples, sr = clipped_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        clipping = [p for p in result.problems if p.type == "clipping"][0]
        assert clipping.severity == "dealbreaker"

    def test_clipping_details_has_count_and_percent(self, clipped_sine):
        """Clipping details should include clipped_samples and clipped_percent."""
        samples, sr = clipped_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        clipping = [p for p in result.problems if p.type == "clipping"][0]
        assert clipping.details["clipped_samples"] > 0
        assert clipping.details["clipped_percent"] > 0

    def test_clean_signal_no_clipping(self, mono_sine_440hz):
        """Clean sine at amp 0.5 -> no clipping problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        clipping_problems = [p for p in result.problems if p.type == "clipping"]
        assert len(clipping_problems) == 0


# ---------------------------------------------------------------------------
# PROB-02: DC Offset Detection
# ---------------------------------------------------------------------------


class TestDCOffset:
    """Verify DC offset detection."""

    def test_dc_offset_detected(self, dc_offset_sine):
        """440Hz + 0.05 DC offset -> dc_offset problem found."""
        samples, sr = dc_offset_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        dc_problems = [p for p in result.problems if p.type == "dc_offset"]
        assert len(dc_problems) == 1

    def test_dc_offset_severity_is_minor(self, dc_offset_sine):
        """DC offset should be severity=minor."""
        samples, sr = dc_offset_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        dc = [p for p in result.problems if p.type == "dc_offset"][0]
        assert dc.severity == "minor"

    def test_dc_offset_value_approx_correct(self, dc_offset_sine):
        """DC offset detail should be approximately 0.05."""
        samples, sr = dc_offset_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        dc = [p for p in result.problems if p.type == "dc_offset"][0]
        assert dc.details["dc_offset"] == pytest.approx(0.05, abs=0.01)

    def test_dc_offset_below_threshold_no_detection(self):
        """DC offset of 1e-4 (below 5e-4 threshold) -> no dc_offset problem (S-WR-03)."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        # DC offset of 1e-4 is below the 5e-4 threshold
        samples = (0.5 * np.sin(2 * np.pi * 440 * t) + 1e-4).astype(np.float32)
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        dc_problems = [p for p in result.problems if p.type == "dc_offset"]
        assert len(dc_problems) == 0

    def test_dc_offset_above_threshold_detected(self):
        """DC offset of 0.001 (above 5e-4 threshold) -> dc_offset problem found (S-WR-03)."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t) + 0.001).astype(np.float32)
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        dc_problems = [p for p in result.problems if p.type == "dc_offset"]
        assert len(dc_problems) == 1

    def test_clean_signal_no_dc_offset(self, mono_sine_440hz):
        """Clean sine at amp 0.5 centered at zero -> no dc_offset problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        dc_problems = [p for p in result.problems if p.type == "dc_offset"]
        assert len(dc_problems) == 0


# ---------------------------------------------------------------------------
# PROB-03: Inter-Sample Peak Detection
# ---------------------------------------------------------------------------


class TestInterSamplePeaks:
    """Verify inter-sample peak detection."""

    def test_clean_low_amplitude_no_isp(self, mono_sine_440hz):
        """Clean low-amplitude sine -> no inter_sample_peak problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.3
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        isp_problems = [p for p in result.problems if p.type == "inter_sample_peak"]
        assert len(isp_problems) == 0

    def test_isp_has_expected_details(self):
        """High-frequency near-peak sine triggers ISP; details contain expected keys."""
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        # 14700Hz at full amplitude — overshoot ~1.7 dB, well above 0.5 dB threshold
        samples = (1.0 * np.sin(2 * np.pi * 14700 * t)).astype(np.float32)
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        isp_problems = [p for p in result.problems if p.type == "inter_sample_peak"]
        assert len(isp_problems) > 0, "Expected ISP detection on 15kHz near-peak sine"
        details = isp_problems[0].details
        assert "true_peak_dbtp" in details
        assert "sample_peak_dbfs" in details
        assert "overshoot_db" in details


# ---------------------------------------------------------------------------
# PROB-04: Noise Floor Detection
# ---------------------------------------------------------------------------


class TestNoiseFloor:
    """Verify noise floor detection from quietest signal blocks."""

    def test_noisy_signal_noise_floor_detected(self, noisy_signal):
        """Noisy signal (high noise) -> noise_floor problem found."""
        samples, sr = noisy_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        nf_problems = [p for p in result.problems if p.type == "noise_floor"]
        assert len(nf_problems) == 1

    def test_noise_floor_has_dbfs(self, noisy_signal):
        """Noise floor detail should include noise_floor_dbfs."""
        samples, sr = noisy_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        nf = [p for p in result.problems if p.type == "noise_floor"][0]
        assert "noise_floor_dbfs" in nf.details

    def test_clean_sine_no_noise_floor_problem(self, mono_sine_440hz):
        """Clean sine has uniform block RMS -> no noise_floor problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        nf_problems = [p for p in result.problems if p.type == "noise_floor"]
        assert len(nf_problems) == 0


# ---------------------------------------------------------------------------
# PROB-05: SNR Assessment
# ---------------------------------------------------------------------------


class TestSNR:
    """Verify signal-to-noise ratio assessment."""

    def test_noisy_signal_snr_detected(self, noisy_signal):
        """Noisy signal -> snr problem found."""
        samples, sr = noisy_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        snr_problems = [p for p in result.problems if p.type == "snr"]
        assert len(snr_problems) == 1

    def test_snr_has_details(self, noisy_signal):
        """SNR detail should include snr_db and quality."""
        samples, sr = noisy_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        snr = [p for p in result.problems if p.type == "snr"][0]
        assert "snr_db" in snr.details
        assert "quality" in snr.details

    def test_clean_sine_no_snr_problem(self, mono_sine_440hz):
        """Clean sine (high SNR) -> no snr problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        snr_problems = [p for p in result.problems if p.type == "snr"]
        assert len(snr_problems) == 0


# ---------------------------------------------------------------------------
# PROB-06: Hum Detection
# ---------------------------------------------------------------------------


class TestHum:
    """Verify 50/60Hz mains hum detection."""

    def test_hum_detected_in_humming_signal(self, signal_with_hum):
        """Signal with 60Hz component -> hum problem found."""
        samples, sr = signal_with_hum
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        hum_problems = [p for p in result.problems if p.type == "hum"]
        assert len(hum_problems) == 1

    def test_hum_severity_is_significant(self, signal_with_hum):
        """Hum should be severity=significant."""
        samples, sr = signal_with_hum
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        hum = [p for p in result.problems if p.type == "hum"][0]
        assert hum.severity == "significant"

    def test_hum_details_has_frequency(self, signal_with_hum):
        """Hum details should include primary_frequency_hz near 60."""
        samples, sr = signal_with_hum
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        hum = [p for p in result.problems if p.type == "hum"][0]
        assert "primary_frequency_hz" in hum.details
        assert hum.details["primary_frequency_hz"] == pytest.approx(60.0, abs=5.0)

    def test_clean_sine_no_hum(self, mono_sine_440hz):
        """Clean 440Hz sine -> no hum problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        hum_problems = [p for p in result.problems if p.type == "hum"]
        assert len(hum_problems) == 0


# ---------------------------------------------------------------------------
# PROB-06b: Hum Detection Edge Cases (< 2 seconds)
# ---------------------------------------------------------------------------


class TestHumEdgeCases:
    """Audio shorter than 2 seconds should return empty hum results."""

    @staticmethod
    def _make_hum_signal(duration: float, sr: int = 44100) -> np.ndarray:
        """Create a mono float32 signal with a strong 60Hz hum component."""
        n_samples = int(sr * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False, dtype=np.float32)
        return (
            0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 60 * t)
        ).astype(np.float32)

    def test_half_second_returns_empty(self):
        """0.5-second audio with 60Hz hum -> empty list."""
        sr = 44100
        samples = self._make_hum_signal(0.5, sr)
        result = _detect_hum(samples, sr)
        assert result == []

    def test_one_second_returns_empty(self):
        """1.0-second audio with 60Hz hum -> empty list."""
        sr = 44100
        samples = self._make_hum_signal(1.0, sr)
        result = _detect_hum(samples, sr)
        assert result == []

    def test_one_point_five_seconds_returns_empty(self):
        """1.5-second audio with 60Hz hum -> empty list."""
        sr = 44100
        samples = self._make_hum_signal(1.5, sr)
        result = _detect_hum(samples, sr)
        assert result == []

    def test_one_point_nine_seconds_returns_empty(self):
        """1.9-second audio with 60Hz hum -> empty list."""
        sr = 44100
        samples = self._make_hum_signal(1.9, sr)
        result = _detect_hum(samples, sr)
        assert result == []

    def test_two_seconds_returns_nonempty(self, signal_with_hum):
        """2.0-second audio with 60Hz hum -> non-empty list (boundary preserved)."""
        samples, sr = signal_with_hum
        result = _detect_hum(samples, sr)
        assert len(result) > 0

    def test_detect_problems_short_audio_no_exception(self):
        """detect_problems with 1-second audio does not raise (integration guard)."""
        sr = 44100
        samples = self._make_hum_signal(1.0, sr)
        audio = _make_audio(samples, sr)
        # Should not raise any exception
        result = detect_problems(audio)
        assert isinstance(result, ProblemsResult)


# ---------------------------------------------------------------------------
# PROB-11: Clean Signal
# ---------------------------------------------------------------------------


class TestCleanSignal:
    """Clean signal should report zero problems."""

    def test_clean_signal_reports_zero_problems(self, mono_sine_440hz):
        """Clean sine at 0.5 amplitude -> clean=True, problems=[], total=0."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5  # Scale below any threshold
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        assert result.clean is True
        assert result.problems == []
        assert result.summary.total == 0


# ---------------------------------------------------------------------------
# PROB-12: Severity Tiers
# ---------------------------------------------------------------------------


class TestSeverityTiers:
    """Verify severity tier summary and sorting order."""

    def test_summary_has_all_tier_keys(self, mono_sine_440hz):
        """Summary has dealbreaker, significant, moderate, minor, total."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        expected = {"dealbreaker", "significant", "moderate", "minor", "total"}
        assert set(result.summary.model_dump().keys()) == expected

    def test_clipped_signal_has_dealbreaker(self, clipped_sine):
        """Clipped signal -> summary has dealbreaker >= 1, total >= 1."""
        samples, sr = clipped_sine
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        assert result.summary.dealbreaker >= 1
        assert result.summary.total >= 1

    def test_problems_sorted_by_severity(self):
        """Problems should be sorted by severity order: dealbreaker first."""
        # Combine clipping (dealbreaker) + DC offset (significant) to guarantee >=2 problems
        sr = 44100
        t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
        samples = np.clip(1.2 * np.sin(2 * np.pi * 440 * t), -1.0, 1.0).astype(
            np.float32
        ) + np.float32(0.05)
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        assert len(result.problems) >= 2, (
            f"Expected >=2 problems but got {len(result.problems)}"
        )
        severity_order = {"dealbreaker": 0, "significant": 1, "moderate": 2, "minor": 3}
        for i in range(len(result.problems) - 1):
            current = severity_order[result.problems[i].severity]
            next_sev = severity_order[result.problems[i + 1].severity]
            assert current <= next_sev


# ---------------------------------------------------------------------------
# Near-silence guard
# ---------------------------------------------------------------------------


class TestNearSilenceGuard:
    """Near-silent audio should return clean=True with empty problems."""

    def test_near_silence_returns_clean(self, near_silence):
        """Near-silent audio (~-100 dBFS) -> clean=True, problems=[]."""
        samples, sr = near_silence
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        assert result.clean is True
        assert result.problems == []


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
            detect_problems(audio)


# ---------------------------------------------------------------------------
# PROB-07: Sibilance Detection
# ---------------------------------------------------------------------------


class TestSibilance:
    """Verify excessive 5-10kHz energy detection."""

    def test_detects_sibilance_in_boosted_signal(self, sibilant_signal):
        """Sibilant signal (7kHz boost) -> sibilance problem found."""
        samples, sr = sibilant_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        sib = [p for p in result.problems if p.type == "sibilance"]
        assert len(sib) == 1
        assert sib[0].severity == "moderate"
        assert "band_energy_db" in sib[0].details
        assert "excess_db" in sib[0].details

    def test_no_sibilance_on_clean_sine(self, mono_sine_440hz):
        """Clean 440Hz sine -> no sibilance problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        sib = [p for p in result.problems if p.type == "sibilance"]
        assert len(sib) == 0


# ---------------------------------------------------------------------------
# PROB-08: Mud Detection
# ---------------------------------------------------------------------------


class TestMud:
    """Verify excessive 200-500Hz energy detection."""

    def test_detects_mud_in_low_heavy_signal(self, muddy_signal):
        """Muddy signal (300Hz boost) -> mud problem found."""
        samples, sr = muddy_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        mud = [p for p in result.problems if p.type == "mud"]
        assert len(mud) == 1
        assert mud[0].severity == "moderate"
        assert "band_energy_db" in mud[0].details
        assert "excess_db" in mud[0].details

    def test_no_mud_on_clean_sine(self, mono_sine_440hz):
        """Clean 440Hz sine -> no mud problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        mud = [p for p in result.problems if p.type == "mud"]
        assert len(mud) == 0


# ---------------------------------------------------------------------------
# PROB-09: Harshness Detection
# ---------------------------------------------------------------------------


class TestHarshness:
    """Verify excessive 2-4kHz energy detection."""

    def test_detects_harshness_in_boosted_signal(self, harsh_signal):
        """Harsh signal (3kHz boost) -> harshness problem found."""
        samples, sr = harsh_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        harsh = [p for p in result.problems if p.type == "harshness"]
        assert len(harsh) == 1
        assert harsh[0].severity == "moderate"
        assert "band_energy_db" in harsh[0].details
        assert "excess_db" in harsh[0].details

    def test_no_harshness_on_clean_sine(self, mono_sine_440hz):
        """Clean 440Hz sine -> no harshness problem."""
        samples, sr = mono_sine_440hz
        samples = samples * 0.5
        audio = _make_audio(samples.astype(np.float32), sr)
        result = detect_problems(audio)
        harsh = [p for p in result.problems if p.type == "harshness"]
        assert len(harsh) == 0


# ---------------------------------------------------------------------------
# PROB-10: Resonant Peak Detection
# ---------------------------------------------------------------------------


class TestResonantPeaks:
    """Verify narrow resonant peak (room mode) detection."""

    def test_detects_resonance_in_narrow_peak(self, resonant_signal):
        """Resonant signal (120Hz tone) -> resonant_peak problem found."""
        samples, sr = resonant_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        res = [p for p in result.problems if p.type == "resonant_peak"]
        assert len(res) == 1
        assert res[0].severity == "significant"
        assert res[0].details["num_resonances"] >= 1
        resonances = res[0].details["resonances"]
        assert len(resonances) >= 1
        # First resonance should be near 120 Hz
        assert abs(resonances[0]["frequency_hz"] - 120) < 20

    def test_no_resonance_on_white_noise(self, white_noise_1s):
        """White noise (flat spectrum) -> no resonant_peak problem."""
        samples, sr = white_noise_1s
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        res = [p for p in result.problems if p.type == "resonant_peak"]
        assert len(res) == 0


# ---------------------------------------------------------------------------
# PROB-13: Lossy Codec Detection
# ---------------------------------------------------------------------------


class TestSpectralFlatnessFramed:
    """S-WR-07: _spectral_flatness uses windowed framing."""

    def test_spectral_flatness_framed_white_noise(self):
        """White noise -> framed spectral flatness > 0.5 (broadband)."""
        from phantom.problems import _spectral_flatness

        rng = np.random.default_rng(200)
        noise = rng.standard_normal(44100 * 2).astype(np.float32) * 0.3
        flatness = _spectral_flatness(noise)
        assert flatness > 0.5, f"White noise flatness {flatness:.3f} should be > 0.5"

    def test_spectral_flatness_framed_sine(self):
        """Pure 440Hz sine -> framed spectral flatness < 0.01 (tonal)."""
        from phantom.problems import _spectral_flatness

        sr = 44100
        t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
        sine = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        flatness = _spectral_flatness(sine)
        assert flatness < 0.01, f"Pure sine flatness {flatness:.6f} should be < 0.01"


class TestLossyCodec:
    """Verify lossy codec spectral shelf detection."""

    def test_detects_lossy_shelf(self, lossy_sim_signal):
        """Lowpassed noise at 16kHz -> lossy_codec problem found."""
        samples, sr = lossy_sim_signal
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        lossy = [p for p in result.problems if p.type == "lossy_codec"]
        assert len(lossy) == 1
        assert lossy[0].severity == "dealbreaker"
        assert lossy[0].details["shelf_drop_db"] >= 15

    def test_no_lossy_on_full_bandwidth(self, white_noise_1s):
        """Full-bandwidth white noise -> no lossy_codec problem."""
        samples, sr = white_noise_1s
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        lossy = [p for p in result.problems if p.type == "lossy_codec"]
        assert len(lossy) == 0

    def test_skips_lossy_check_on_low_sample_rate(self):
        """Signal at 22050 Hz -> no lossy_codec problem (skipped)."""
        sr = 22050
        rng = np.random.default_rng(106)
        samples = rng.standard_normal(sr * 2).astype(np.float32) * 0.3
        audio = _make_audio(samples, sr)
        result = detect_problems(audio)
        lossy = [p for p in result.problems if p.type == "lossy_codec"]
        assert len(lossy) == 0
