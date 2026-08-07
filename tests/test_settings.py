"""Tests for phantom._settings -- tunable analysis thresholds (C.1).

Defaults must reproduce the pre-C.1 constants exactly; env overrides must
resolve per call; the analysis cache must fold settings into its key so a
tuned run never serves a default-settings hit.
"""

from __future__ import annotations

import numpy as np
import pytest

from phantom._cache import _cached_analysis, analysis_cache
from phantom._settings import AnalysisSettings, analysis_settings
from phantom.audio import AudioData
from phantom.dynamics import analyze_dynamics
from phantom.exceptions import AnalysisError
from phantom.phase import analyze_phase


def _audio(left: np.ndarray, right: np.ndarray) -> AudioData:
    sr = 44100
    samples = np.column_stack([left, right]).astype(np.float32)
    return AudioData(
        samples=samples,
        sample_rate=sr,
        num_channels=2,
        duration=len(samples) / sr,
        num_samples=len(samples),
    )


def _tone(freq: float, seconds: float, amp: float = 0.5) -> np.ndarray:
    t = np.arange(int(44100 * seconds)) / 44100
    return amp * np.sin(2 * np.pi * freq * t)


# In-phase stereo: overall L/R correlation is exactly 1.0, so a polarity
# threshold above 1.0 flags every signal (1.0 < threshold), while the default
# -0.5 never does -- a clean threshold flip.
_IN_PHASE = _audio(_tone(220, 0.5), _tone(220, 0.5))


class TestDefaults:
    def test_defaults_match_documented_constants(self) -> None:
        s = AnalysisSettings()
        assert s.polarity_threshold == -0.5
        assert s.phat_window_s == 10.0
        assert s.crest_factor_low_db == 6.0

    def test_env_unset_resolves_to_defaults(self, monkeypatch) -> None:
        monkeypatch.delenv("PHANTOM_POLARITY_THRESHOLD", raising=False)
        monkeypatch.delenv("PHANTOM_CREST_FACTOR_LOW_DB", raising=False)
        assert analysis_settings() == AnalysisSettings()

    def test_env_override_applies(self, monkeypatch) -> None:
        monkeypatch.setenv("PHANTOM_POLARITY_THRESHOLD", "-0.75")
        monkeypatch.setenv("PHANTOM_CREST_FACTOR_LOW_DB", "7.5")
        s = analysis_settings()
        assert s.polarity_threshold == -0.75
        assert s.crest_factor_low_db == 7.5
        # Unset knobs keep their defaults.
        assert s.phat_window_s == 10.0

    def test_malformed_env_raises_analysis_error(self, monkeypatch) -> None:
        monkeypatch.setenv("PHANTOM_POLARITY_THRESHOLD", "loud")
        with pytest.raises(
            AnalysisError, match="PHANTOM_POLARITY_THRESHOLD must be a number"
        ):
            analysis_settings()


class TestFingerprint:
    def test_stable_without_env(self, monkeypatch) -> None:
        monkeypatch.delenv("PHANTOM_POLARITY_THRESHOLD", raising=False)
        assert analysis_settings().fingerprint() == analysis_settings().fingerprint()

    def test_equal_values_equal_fingerprints(self) -> None:
        assert AnalysisSettings().fingerprint() == AnalysisSettings(
            polarity_threshold=-0.5
        ).fingerprint()

    def test_changes_with_env(self, monkeypatch) -> None:
        monkeypatch.delenv("PHANTOM_POLARITY_THRESHOLD", raising=False)
        before = analysis_settings().fingerprint()
        monkeypatch.setenv("PHANTOM_POLARITY_THRESHOLD", "-0.75")
        assert analysis_settings().fingerprint() != before


class TestCacheKeying:
    def test_settings_key_separates_entries(self) -> None:
        audio = _IN_PHASE
        cache = analysis_cache
        key_a = "|fp-a"
        key_b = "|fp-b"
        cache.put(audio, "probe", "result-a", key_a)
        cache.put(audio, "probe", "result-b", key_b)
        assert cache.get(audio, "probe", key_a) == "result-a"
        assert cache.get(audio, "probe", key_b) == "result-b"

    def test_cached_analysis_never_serves_stale_settings(self) -> None:
        audio = _audio(_tone(440, 0.5), _tone(440, 0.5))
        seen: list[AnalysisSettings] = []

        def phase_with(settings: AnalysisSettings | None):
            return analyze_phase(audio, settings)

        def recorder(audio_in, settings):
            seen.append(settings)
            return phase_with(settings)

        tuned = AnalysisSettings(polarity_threshold=1.01)
        strict = _cached_analysis(audio, "settings_probe", recorder, tuned)
        default = _cached_analysis(audio, "settings_probe", recorder, None)
        assert strict.polarity_inverted is True
        assert default.polarity_inverted is False
        # Both runs computed -- the tuned hit was never served for defaults.
        assert len(seen) == 2

    def test_cached_analysis_reuses_same_settings(self) -> None:
        audio = _audio(_tone(880, 0.5), _tone(880, 0.5))
        calls = 0

        def recorder(audio_in, settings):
            nonlocal calls
            calls += 1
            return analyze_phase(audio_in, settings)

        _cached_analysis(audio, "settings_probe2", recorder, None)
        _cached_analysis(audio, "settings_probe2", recorder, None)
        assert calls == 1


class TestAnalyzersHonorSettings:
    def test_polarity_threshold_flips_phase(self) -> None:
        default = analyze_phase(_IN_PHASE)
        assert default.polarity_inverted is False
        strict = analyze_phase(_IN_PHASE, AnalysisSettings(polarity_threshold=1.01))
        assert strict.polarity_inverted is True

    def test_polarity_env_override_flips_phase(self, monkeypatch) -> None:
        assert analyze_phase(_IN_PHASE).polarity_inverted is False
        monkeypatch.setenv("PHANTOM_POLARITY_THRESHOLD", "1.01")
        assert analyze_phase(_IN_PHASE).polarity_inverted is True

    def test_crest_threshold_flips_dynamics(self) -> None:
        # Any finite crest factor compares against the tuned threshold:
        # +1e9 flags everything low-crest, -1e9 nothing.
        assert (
            analyze_dynamics(
                _IN_PHASE, AnalysisSettings(crest_factor_low_db=1e9)
            ).crest_factor_is_low
            is True
        )
        assert (
            analyze_dynamics(
                _IN_PHASE, AnalysisSettings(crest_factor_low_db=-1e9)
            ).crest_factor_is_low
            is False
        )
