"""Tests for the analysis facade (phantom.facade).

Covers the dimension registry, cache-key unification through run_analyses,
and the shared stem payload model used by both the server composite tools
and the analyze CLI.
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import BaseModel, ValidationError

from phantom._cache import _MISSING, analysis_cache
from phantom.audio import AudioData
from phantom.facade import (
    ANALYSIS_TYPES,
    BatchDiagnosticResult,
    StemDiagnosticResult,
    analysis_keys,
    run_analyses,
)


def _make_audio(samples_1d: np.ndarray, sr: int) -> AudioData:
    """Wrap a 1D mono signal into an AudioData instance."""
    return AudioData(
        samples=samples_1d.reshape(-1, 1),
        sample_rate=sr,
        num_channels=1,
        duration=len(samples_1d) / sr,
        num_samples=len(samples_1d),
    )


EXPECTED_CACHE_KEYS = {
    "spectral": "analyze_spectrum",
    "loudness": "analyze_loudness",
    "dynamics": "analyze_dynamics",
    "stereo": "analyze_stereo",
    "phase": "analyze_phase",
    "problems": "detect_problems",
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_has_six_dimensions_in_order():
    """Registry exposes exactly the six dimensions, in declaration order."""
    assert list(ANALYSIS_TYPES) == [
        "spectral",
        "loudness",
        "dynamics",
        "stereo",
        "phase",
        "problems",
    ]
    assert analysis_keys() == tuple(ANALYSIS_TYPES)


def test_registry_cache_keys_are_explicit_and_shared():
    """cache_key is explicit (never fn.__name__) and matches the keys the
    server/compare tools and the CLI populates in the shared cache."""
    for key, spec in ANALYSIS_TYPES.items():
        assert spec.key == key
        assert spec.cache_key == EXPECTED_CACHE_KEYS[key], (
            f"{key} cache_key must stay the legacy shared key so composite and "
            "compare tools keep hitting the same cache entries"
        )
        # The key is explicit and decoupled from the analyzer function's name:
        # today they coincide, but renaming the fn must not move the cache key.
        assert spec.fn.__name__ == spec.cache_key
        assert callable(spec.fn)
        assert spec.title
        assert spec.description


# ---------------------------------------------------------------------------
# run_analyses
# ---------------------------------------------------------------------------


def test_run_analyses_all_runs_six_and_populates_shared_cache(
    mono_sine_440hz,
):
    """Default run returns all six Pydantic results and populates the shared
    cache under the canonical cache keys (mirrors the CLI/server twins)."""
    samples, sr = mono_sine_440hz
    audio = _make_audio(samples, sr)

    analysis_cache.clear()
    try:
        results = run_analyses(audio)
        assert set(results) == set(ANALYSIS_TYPES)
        for key, result in results.items():
            assert isinstance(result, BaseModel), f"{key} is not a model"
        # Cache entries keyed under the canonical names.
        assert analysis_cache.get(audio, "analyze_spectrum") is not _MISSING
        assert analysis_cache.get(audio, "detect_problems") is not _MISSING
        # A second call on the same bytes reuses the cache (same object).
        assert run_analyses(audio)["spectral"] is results["spectral"]
    finally:
        analysis_cache.clear()


def test_run_analyses_subset_only_runs_requested(mono_sine_440hz):
    """Explicit keys run only those dimensions, in the requested order."""
    samples, sr = mono_sine_440hz
    audio = _make_audio(samples, sr)

    analysis_cache.clear()
    try:
        results = run_analyses(audio, ["problems", "spectral"])
        assert list(results) == ["problems", "spectral"]
    finally:
        analysis_cache.clear()


def test_run_analyses_unknown_key_raises_key_error(mono_sine_440hz):
    """Bad dimension key fails loudly rather than silently returning a subset."""
    samples, sr = mono_sine_440hz
    audio = _make_audio(samples, sr)
    with pytest.raises(KeyError):
        run_analyses(audio, ["spectral", "nope"])


# ---------------------------------------------------------------------------
# Shared payload model
# ---------------------------------------------------------------------------


def test_stem_result_full_dump(mono_sine_440hz):
    """All-six construction dumps every dimension plus rounded metadata."""
    samples, sr = mono_sine_440hz
    audio = _make_audio(samples, sr)
    results = run_analyses(audio)
    result = StemDiagnosticResult(
        file="test.wav",
        duration_seconds=audio.duration,
        sample_rate=audio.sample_rate,
        channels=audio.num_channels,
        **results,
    )
    data = result.model_dump()
    assert list(data) == [
        "file",
        "duration_seconds",
        "sample_rate",
        "channels",
        "spectral",
        "loudness",
        "dynamics",
        "stereo",
        "phase",
        "problems",
    ]
    assert data["duration_seconds"] == round(audio.duration, 3)


def test_stem_result_requires_all_dimensions(mono_sine_440hz):
    """StemDiagnosticResult is the full-diagnostic payload: a subset cannot be
    constructed, so no caller can accidentally emit a truncated stem."""
    samples, sr = mono_sine_440hz
    audio = _make_audio(samples, sr)
    results = run_analyses(audio, ["spectral"])
    with pytest.raises(ValidationError):
        StemDiagnosticResult(
            file="test.wav",
            duration_seconds=audio.duration,
            sample_rate=audio.sample_rate,
            channels=audio.num_channels,
            **results,
        )


def test_stem_result_forbids_unknown_dimension(mono_sine_440hz):
    """extra='forbid' makes a payload key that is not a model field fail
    loudly instead of being silently dropped (a forgotten registry row would
    otherwise vanish from every stem)."""
    samples, sr = mono_sine_440hz
    audio = _make_audio(samples, sr)
    results = run_analyses(audio)
    with pytest.raises(ValidationError):
        StemDiagnosticResult(
            file="test.wav",
            duration_seconds=audio.duration,
            sample_rate=audio.sample_rate,
            channels=audio.num_channels,
            **results,
            new_dimension=results["spectral"],
        )


def test_batch_keeps_partial_stem_dicts(mono_sine_440hz):
    """BatchDiagnosticResult does not coerce a partial stem dict into a stem
    model -- if it did, the missing dimensions would be re-inserted as nulls
    (the CLI batch --json subset contract)."""
    samples, sr = mono_sine_440hz
    audio = _make_audio(samples, sr)
    # A CLI-style subset stem: metadata + the enabled dimension only.
    partial = {
        "file": "a.wav",
        "duration_seconds": audio.duration,
        "sample_rate": audio.sample_rate,
        "channels": audio.num_channels,
        "spectral": run_analyses(audio, ["spectral"])["spectral"].model_dump(),
    }
    # A dict missing the required dims must pass through (and round-trip)
    # as a plain dict -- no automatic null-filling of "loudness"/... keys.
    batch = BatchDiagnosticResult(
        stems={"a.wav": partial},
        stem_count=1,
    )
    data = batch.model_dump()
    assert data["stems"]["a.wav"] == partial
    assert "loudness" not in data["stems"]["a.wav"]


def test_batch_diagnostic_result_dumps_stems_and_count(mono_sine_440hz):
    """Batch payload holds StemDiagnosticResult values and plain-dict errors."""
    samples, sr = mono_sine_440hz
    audio = _make_audio(samples, sr)
    results = run_analyses(audio)
    good = StemDiagnosticResult(
        file="a.wav",
        duration_seconds=audio.duration,
        sample_rate=audio.sample_rate,
        channels=audio.num_channels,
        **results,
    )
    batch = BatchDiagnosticResult(
        stems={
            "a.wav": good,
            "b.wav": {"error": "boom", "error_type": "AudioLoadError"},
        },
        stem_count=2,
    )
    data = batch.model_dump()
    assert data["stem_count"] == 2
    assert "spectral" in data["stems"]["a.wav"]
    assert data["stems"]["b.wav"] == {"error": "boom", "error_type": "AudioLoadError"}
