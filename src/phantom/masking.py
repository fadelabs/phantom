"""Frequency masking analysis functions.

Provides analyze_masking() for pairwise stem masking analysis (per D-01)
and analyze_masking_matrix() for multi-stem analysis (per D-01).

Uses Essentia FrequencyBands for per-octave-band energy extraction
and numpy for overlap scoring.
"""

from __future__ import annotations

import itertools

import numpy as np
import essentia.standard as es
from pydantic import BaseModel, field_validator

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom._rounding import round_ratio
from phantom._utils import is_near_silent, wrap_errors
from phantom.spectral import OCTAVE_EDGES, _BAND_LABELS

# Severity thresholds for per-band overlap classification.
_SEVERITY_HIGH = 0.6
_SEVERITY_MODERATE = 0.3
_SEVERITY_LOW = 0.1

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

# Energy floor: bands more than 40 dB below peak are zeroed (per D-06).
_FLOOR_DB = 40.0


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class MaskingBand(BaseModel):
    """Per-band masking analysis result."""

    band: str
    severity: str
    overlap_score: float

    @field_validator("overlap_score", mode="before")
    @classmethod
    def _round_score(cls, v: float) -> float | None:
        return round_ratio(v)


class MaskingResult(BaseModel):
    """Result of pairwise masking analysis."""

    bands: list[MaskingBand] = []
    overall_severity: str = "none"
    overall_score: float = 0.0

    @field_validator("overall_score", mode="before")
    @classmethod
    def _round_score(cls, v: float) -> float | None:
        return round_ratio(v)


class MaskingPair(BaseModel):
    """A single stem pair in the masking matrix."""

    stem_a: str
    stem_b: str
    overall_severity: str
    overall_score: float
    bands: list[MaskingBand]

    @field_validator("overall_score", mode="before")
    @classmethod
    def _round_score(cls, v: float) -> float | None:
        return round_ratio(v)


class MaskingMatrixResult(BaseModel):
    """Result of multi-stem masking matrix analysis."""

    pairs: list[MaskingPair] = []
    stem_count: int = 0
    pair_count: int = 0


# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------


def _classify_severity(score: float) -> str:
    """Classify an overlap score into a severity label.

    Thresholds (per D-08):
      high     >= 0.6
      moderate >= 0.3
      low      >= 0.1
      none     <  0.1
    """
    if score >= _SEVERITY_HIGH:
        return "high"
    if score >= _SEVERITY_MODERATE:
        return "moderate"
    if score >= _SEVERITY_LOW:
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


def _compute_band_energies(mono: np.ndarray, sample_rate: int) -> np.ndarray:
    """Compute average energy per octave band using Essentia FrequencyBands.

    Args:
        mono: 1D float32 numpy array of audio samples.
        sample_rate: Sample rate in Hz.

    Returns:
        1D numpy array of shape (10,) with average energy per octave band.
    """
    frame_size = 4096
    hop_size = 2048

    # Audio shorter than one FFT frame cannot produce meaningful band energies.
    # Zero energy is the acoustically correct answer — the signal contains
    # insufficient data to resolve any frequency band.
    if len(mono) < frame_size:
        return np.zeros(len(_BAND_LABELS))

    windowing = es.Windowing(type="hann", size=frame_size)
    spectrum = es.Spectrum(size=frame_size)
    freq_bands = es.FrequencyBands(frequencyBands=OCTAVE_EDGES, sampleRate=sample_rate)

    band_energies_list = []
    for frame in es.FrameGenerator(mono, frameSize=frame_size, hopSize=hop_size):
        win = windowing(frame)
        spec = spectrum(win)
        bands = freq_bands(spec)
        band_energies_list.append(bands)

    if not band_energies_list:
        return np.zeros(len(_BAND_LABELS))

    return np.mean(band_energies_list, axis=0)


def _compute_pairwise_result(
    energies_a: np.ndarray,
    energies_b: np.ndarray,
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

    # Energy floor guard (per D-06): zero out bands more than 40 dB
    # below the peak band energy across both stems.
    peak_energy = max(float(np.max(energies_a)), float(np.max(energies_b)))
    floor = peak_energy * 10 ** (-_FLOOR_DB / 10)
    for i in range(len(overlap_scores)):
        if max(float(energies_a[i]), float(energies_b[i])) < floor:
            overlap_scores[i] = 0.0

    # Build per-band results
    bands = [
        MaskingBand(
            band=label,
            severity=_classify_severity(float(score)),
            overlap_score=float(score),
        )
        for label, score in zip(_BAND_LABELS, overlap_scores)
    ]

    # Weighted overall score
    overall_score = float(np.average(overlap_scores, weights=BAND_WEIGHTS))
    overall_severity = _classify_severity(overall_score)

    return MaskingResult(
        bands=bands,
        overall_severity=overall_severity,
        overall_score=overall_score,
    )


@wrap_errors("Masking analysis failed")
def analyze_masking(audio_a: AudioData, audio_b: AudioData) -> MaskingResult:
    """Analyze frequency masking between two audio stems.

    Computes per-octave-band spectral overlap between two stems and assigns
    severity labels based on the degree of overlap. Returns a MaskingResult
    with band-level and overall scores.

    Args:
        audio_a: First audio stem (AudioData object).
        audio_b: Second audio stem (AudioData object).

    Returns:
        MaskingResult with bands, overall_severity, overall_score.

    Raises:
        AnalysisError: If sample rates mismatch, audio is empty, or analysis fails.
    """
    # Sample rate mismatch guard
    if audio_a.sample_rate != audio_b.sample_rate:
        raise AnalysisError(
            f"Sample rate mismatch: {audio_a.sample_rate} Hz vs "
            f"{audio_b.sample_rate} Hz. Resample to match before comparing."
        )

    # Mono mixdown
    mono_a = audio_a.mono
    mono_b = audio_b.mono

    # Empty samples guard
    if len(mono_a) == 0 or len(mono_b) == 0:
        raise AnalysisError("Masking analysis failed: audio has 0 samples")

    # Near-silence guard
    if is_near_silent(mono_a) or is_near_silent(mono_b):
        return _no_masking_result()

    # Compute per-band energies for both stems
    energies_a = _compute_band_energies(mono_a, audio_a.sample_rate)
    energies_b = _compute_band_energies(mono_b, audio_b.sample_rate)

    return _compute_pairwise_result(energies_a, energies_b)


@wrap_errors("Masking analysis failed")
def analyze_masking_matrix(stems: list[AudioData]) -> MaskingMatrixResult:
    """Analyze frequency masking across all pairs in a multi-stem set.

    Returns a MaskingMatrixResult with pairs ranked by overall masking
    severity (worst first), plus stem_count and pair_count metadata (per D-05).
    Pre-computes band energies per stem to avoid redundant Essentia calls
    (per RESEARCH.md Pitfall 4).

    Args:
        stems: List of AudioData objects (all must share the same sample rate).

    Returns:
        MaskingMatrixResult with pairs, stem_count, pair_count.

    Raises:
        AnalysisError: If sample rates mismatch, audio is empty, or analysis fails.
    """
    n = len(stems)

    # Degenerate case: fewer than 2 stems
    if n < 2:
        return MaskingMatrixResult(pairs=[], stem_count=n, pair_count=0)

    # Sample rate consistency check
    rates = {s.sample_rate for s in stems}
    if len(rates) > 1:
        raise AnalysisError(
            f"Sample rate mismatch: stems have rates {rates}. "
            "All stems must share the same sample rate."
        )

    # Pre-compute band energies for all stems (optimization)
    energies: list[np.ndarray | None] = []
    for stem in stems:
        mono = stem.mono
        if len(mono) == 0:
            raise AnalysisError("Masking analysis failed: audio has 0 samples")
        if is_near_silent(mono):
            energies.append(None)  # marker for silent stems
        else:
            energies.append(_compute_band_energies(mono, stem.sample_rate))

    # Iterate all unique pairs
    pairs: list[MaskingPair] = []
    for i, j in itertools.combinations(range(n), 2):
        if energies[i] is None or energies[j] is None:
            # One or both stems are near-silent — no masking
            result = _no_masking_result()
        else:
            result = _compute_pairwise_result(energies[i], energies[j])

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
