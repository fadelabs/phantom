"""Frequency masking analysis functions.

Provides analyze_masking() for pairwise stem masking analysis (per D-01)
and analyze_masking_matrix() for multi-stem analysis (per D-01).

Uses Essentia FrequencyBands for per-octave-band energy extraction
and numpy for overlap scoring.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import ClassVar

import numpy as np
from pydantic import Field

from phantom.audio import AudioData
from phantom._resample import align_sample_rates, resample_to_match
from phantom._bands import _BAND_LABELS, _octave_band_energies
from phantom._rounding import RoundedModel, round_ratio
from phantom._settings import AnalysisSettings, analysis_settings
from phantom._utils import guarded_mono, wrap_errors

# Severity thresholds for per-band overlap classification now live in
# AnalysisSettings (C.1): severity_high/moderate/low (0.6/0.3/0.1).

# Band weights reflecting musical importance for masking (per D-07).
# Prime masking zone (250-500 Hz) = 1.0, tapering to extremes.
BAND_WEIGHTS = np.array(
    [
        0.2,  # 31.25 Hz - sub
        0.4,  # 62.5 Hz  - sub/low
        0.7,  # 125 Hz   - low
        1.0,  # 250 Hz   - low-mid (prime masking zone)
        1.0,  # 500 Hz   - low-mid (prime masking zone)
        0.8,  # 1 kHz    - mid
        0.7,  # 2 kHz    - upper-mid
        0.5,  # 4 kHz    - high
        0.3,  # 8 kHz    - high
        0.2,  # 16 kHz   - ultra-high
    ]
)

# The masking energy floor (bands more than 40 dB below the pair peak are
# zeroed, per D-06) is AnalysisSettings.masking_floor_db (C.1).


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class MaskingBand(RoundedModel):
    """Per-band masking analysis result."""

    band: str
    severity: str
    overlap_score: float

    _ROUND_FIELDS: ClassVar[dict[str, Callable[[object], object]]] = {
        "overlap_score": round_ratio
    }


class MaskingResult(RoundedModel):
    """Result of pairwise masking analysis."""

    bands: list[MaskingBand] = Field(default_factory=list)
    overall_severity: str = "none"
    overall_score: float = 0.0

    _ROUND_FIELDS: ClassVar[dict[str, Callable[[object], object]]] = {
        "overall_score": round_ratio
    }


class MaskingPair(RoundedModel):
    """A single stem pair in the masking matrix."""

    stem_a: str
    stem_b: str
    overall_severity: str
    overall_score: float
    bands: list[MaskingBand]

    _ROUND_FIELDS: ClassVar[dict[str, Callable[[object], object]]] = {
        "overall_score": round_ratio
    }


class MaskingMatrixResult(RoundedModel):
    """Result of multi-stem masking matrix analysis."""

    pairs: list[MaskingPair] = Field(default_factory=list)
    stem_count: int = 0
    pair_count: int = 0


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------


def _classify_severity(score: float, settings: AnalysisSettings) -> str:
    """Classify an overlap score into a severity label.

    Thresholds (per D-08, AnalysisSettings-tunable C.1):
      high     >= severity_high    (0.6)
      moderate >= severity_moderate (0.3)
      low      >= severity_low     (0.1)
      none     <  severity_low
    """
    if score >= settings.severity_high:
        return "high"
    if score >= settings.severity_moderate:
        return "moderate"
    if score >= settings.severity_low:
        return "low"
    return "none"


def _no_masking_result() -> MaskingResult:
    """Return a masking result with all overlap scores at zero.

    Used when one or both stems are near-silent.
    """
    bands = [
        MaskingBand(band=label, severity="none", overlap_score=0.0)
        for label in _BAND_LABELS
    ]
    return MaskingResult(bands=bands, overall_severity="none", overall_score=0.0)


def _compute_band_energies(
    mono: np.ndarray, sample_rate: int, settings: AnalysisSettings
) -> np.ndarray:
    """Compute average energy per octave band using Essentia FrequencyBands.

    Delegates to the shared ``_bands._octave_band_energies`` helper so the
    Hann + ``FrequencyBands(OCTAVE_EDGES)`` loop lives in one place (P-09,
    promoted to a public module in B.6). Frame/hop sizes come from *settings*
    (C.1); numerically identical to the former inline implementation at
    defaults.

    Args:
        mono: 1D float32 numpy array of audio samples.
        sample_rate: Sample rate in Hz.
        settings: Effective analysis settings (the requiring caller resolves
            them).

    Returns:
        1D numpy array of shape (10,) with average energy per octave band.
    """
    return _octave_band_energies(mono, sample_rate, settings)


def _compute_pairwise_result(
    energies_a: np.ndarray,
    energies_b: np.ndarray,
    settings: AnalysisSettings,
) -> MaskingResult:
    """Compute overlap result from two pre-computed band energy arrays.

    Shared helper used by both ``analyze_masking`` (pairwise) and
    ``analyze_masking_matrix`` (multi-stem loop) to avoid duplication.

    Args:
        energies_a: Band energies for stem A, shape (10,).
        energies_b: Band energies for stem B, shape (10,).

    Returns:
        MaskingResult with bands, overall_severity, overall_score.
    """
    # Per-band overlap: min/max ratio (0 = no overlap, 1 = identical energy)
    overlap_scores = np.minimum(energies_a, energies_b) / (
        np.maximum(energies_a, energies_b) + 1e-10
    )

    # Energy floor guard (per D-06): zero out bands more than
    # masking_floor_db below the peak band energy across both stems.
    peak_energy = max(float(np.max(energies_a)), float(np.max(energies_b)))
    floor = peak_energy * 10 ** (-settings.masking_floor_db / 10)
    for i in range(len(overlap_scores)):
        if max(float(energies_a[i]), float(energies_b[i])) < floor:
            overlap_scores[i] = 0.0

    # Build per-band results
    bands = [
        MaskingBand(
            band=label,
            severity=_classify_severity(float(score), settings),
            overlap_score=float(score),
        )
        for label, score in zip(_BAND_LABELS, overlap_scores)
    ]

    # Weighted overall score
    overall_score = float(np.average(overlap_scores, weights=BAND_WEIGHTS))
    overall_severity = _classify_severity(overall_score, settings)

    return MaskingResult(
        bands=bands,
        overall_severity=overall_severity,
        overall_score=overall_score,
    )


@wrap_errors("Masking analysis failed")
def analyze_masking(
    audio_a: AudioData,
    audio_b: AudioData,
    settings: AnalysisSettings | None = None,
) -> MaskingResult:
    """Analyze frequency masking between two audio stems.

    Computes per-octave-band spectral overlap between two stems and assigns
    severity labels based on the degree of overlap. Returns a MaskingResult
    with band-level and overall scores. Severity splits, the energy floor,
    and the octave-band FFT geometry are AnalysisSettings-tunable (C.1);
    *settings* defaults to the per-call env resolution.

    If inputs have different sample rates, the lower-rate audio is
    automatically upsampled to the higher rate.

    Args:
        audio_a: First audio stem (AudioData object).
        audio_b: Second audio stem (AudioData object).

    Returns:
        MaskingResult with bands, overall_severity, overall_score.

    Raises:
        AnalysisError: If audio is empty or analysis fails.
    """
    effective = settings if settings is not None else analysis_settings()

    # Auto-resample on sample rate mismatch
    audio_a, audio_b = align_sample_rates(audio_a, audio_b)

    # Empty/silence guards (B.2) on both inputs.
    mono_a = guarded_mono(audio_a, "Masking analysis failed")
    mono_b = guarded_mono(audio_b, "Masking analysis failed")
    if mono_a is None or mono_b is None:
        return _no_masking_result()

    # Compute per-band energies for both stems
    energies_a = _compute_band_energies(mono_a, audio_a.sample_rate, effective)
    energies_b = _compute_band_energies(mono_b, audio_b.sample_rate, effective)

    return _compute_pairwise_result(energies_a, energies_b, effective)


@wrap_errors("Masking analysis failed")
def analyze_masking_matrix(
    stems: list[AudioData], settings: AnalysisSettings | None = None
) -> MaskingMatrixResult:
    """Analyze frequency masking across all pairs in a multi-stem set.

    Returns a MaskingMatrixResult with pairs ranked by overall masking
    severity (worst first), plus stem_count and pair_count metadata (per D-05).
    Pre-computes band energies per stem to avoid redundant Essentia calls
    (per RESEARCH.md Pitfall 4). Severity splits, the energy floor, and the
    octave-band FFT geometry are AnalysisSettings-tunable (C.1); *settings*
    defaults to the per-call env resolution.

    If stems have different sample rates, all are automatically upsampled to the
    highest rate. To bound peak memory (P-07), each stem is resampled to the
    target rate one at a time via :func:`resample_to_match` -- the same per-stem
    call :func:`align_sample_rates` makes internally -- and the resampled array
    is dropped as soon as its band energies are computed, so at most one
    resampled copy is held at a time rather than N. Results are identical to
    aligning all stems up front.

    Args:
        stems: List of AudioData objects.

    Returns:
        MaskingMatrixResult with pairs, stem_count, pair_count.

    Raises:
        AnalysisError: If audio is empty or analysis fails.
    """
    effective = settings if settings is not None else analysis_settings()
    n = len(stems)

    # Degenerate case: fewer than 2 stems
    if n < 2:
        return MaskingMatrixResult(pairs=[], stem_count=n, pair_count=0)

    # Target rate: upsample everything to the highest rate (upsample-only, per
    # resample_to_match). Identity when all stems already share a rate.
    target_sr = max(stem.sample_rate for stem in stems)

    # Compute band energies per stem, streaming the resample: each stem is
    # aligned to target_sr just-in-time and the resampled AudioData falls out of
    # scope after its energies are read, so peak memory holds one resampled copy
    # rather than N (P-07). Numerically identical to pre-aligning all stems.
    energies: list[np.ndarray | None] = []
    for stem in stems:
        aligned = resample_to_match(stem, target_sr)  # identity if already at target
        # Empty/silence guards (B.2); the aligned copy is dropped right after.
        mono = guarded_mono(aligned, "Masking analysis failed")
        if mono is None:
            energies.append(None)  # marker for silent stems
        else:
            energies.append(
                _compute_band_energies(mono, aligned.sample_rate, effective)
            )
        del aligned  # drop the resampled copy before the next iteration

    # Iterate all unique pairs
    pairs: list[MaskingPair] = []
    for i, j in itertools.combinations(range(n), 2):
        if energies[i] is None or energies[j] is None:
            # One or both stems are near-silent — no masking
            result = _no_masking_result()
        else:
            result = _compute_pairwise_result(energies[i], energies[j], effective)

        pairs.append(
            MaskingPair(
                stem_a=f"stem_{i}",
                stem_b=f"stem_{j}",
                overall_severity=result.overall_severity,
                overall_score=result.overall_score,
                bands=result.bands,
            )
        )

    # Sort by overall_score descending (worst offenders first, per D-05)
    pairs.sort(key=lambda p: p.overall_score, reverse=True)

    return MaskingMatrixResult(pairs=pairs, stem_count=n, pair_count=len(pairs))
