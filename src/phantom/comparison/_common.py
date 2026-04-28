"""Shared models and helpers for comparison modules."""

from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel, field_validator

from phantom._rounding import round_db, round_hz, round_ratio

_THRESHOLD_ON_TARGET = 1.0
_THRESHOLD_SLIGHT = 3.0
_THRESHOLD_MODERATE = 6.0

_WIDTH_RANGES: dict[str, tuple[float, float]] = {
    "narrow": (0.0, 0.3),
    "moderate": (0.3, 0.7),
    "wide": (0.7, 1.2),
}

_BASS_MONO_THRESHOLD = 0.95


class DeviationResult(BaseModel):
    """Deviation of a measured value from a target or reference."""

    value: Optional[float] = None
    target: Optional[float] = None
    reference: Optional[float] = None
    deviation: Optional[float] = None
    rating: str = "unmeasurable"


class RangeDeviationResult(BaseModel):
    """Deviation of a measured value from a target range."""

    value: Optional[float] = None
    target_range: Optional[list[float]] = None
    deviation: Optional[float] = None
    rating: str = "unmeasurable"

    @field_validator("target_range", mode="before")
    @classmethod
    def _round_range(cls, v):
        if v is None:
            return v
        return [round(x, 2) for x in v]


class MonoBelowResult(BaseModel):
    """Result of mono-below frequency check."""

    mono_below_hz: float
    bass_correlation: float
    has_stereo_bass: bool
    rating: str

    @field_validator("mono_below_hz", mode="before")
    @classmethod
    def _round_hz(cls, v):
        return round_hz(v)

    @field_validator("bass_correlation", mode="before")
    @classmethod
    def _round_corr(cls, v):
        return round_ratio(v)


class LoudnessProfileComparisonSection(BaseModel):
    integrated_lufs: RangeDeviationResult
    true_peak_dbtp: DeviationResult


class DynamicsComparisonSection(BaseModel):
    crest_factor_db: RangeDeviationResult | DeviationResult


class StereoProfileComparisonSection(BaseModel):
    width: RangeDeviationResult
    mono_below: MonoBelowResult


class LoudnessReferenceComparisonSection(BaseModel):
    integrated_lufs: DeviationResult
    true_peak_dbtp: DeviationResult
    loudness_range_lu: DeviationResult


class DynamicsReferenceComparisonSection(BaseModel):
    rms_dbfs: DeviationResult
    crest_factor_db: DeviationResult
    dynamic_range_db: DeviationResult


class StereoReferenceComparisonSection(BaseModel):
    correlation: DeviationResult
    stereo_width: DeviationResult


class MetricDiff(BaseModel):
    before: Optional[float] = None
    after: Optional[float] = None
    change: Optional[float] = None

    @field_validator("before", "after", "change", mode="before")
    @classmethod
    def _round(cls, v):
        return round_db(v)


class MatchAdjustments(BaseModel):
    integrated_lufs: MetricDiff
    true_peak_dbtp: MetricDiff
    spectral_change_db: dict[str, MetricDiff]


class ProfileComparisonResult(BaseModel):
    loudness: Optional[LoudnessProfileComparisonSection] = None
    frequency: Optional[dict[str, DeviationResult]] = None
    dynamics: Optional[DynamicsComparisonSection] = None
    stereo: Optional[StereoProfileComparisonSection] = None


class ReferenceComparisonResult(BaseModel):
    loudness: Optional[LoudnessReferenceComparisonSection] = None
    frequency: Optional[dict[str, DeviationResult]] = None
    dynamics: Optional[DynamicsReferenceComparisonSection] = None
    stereo: Optional[StereoReferenceComparisonSection] = None


class MatchResult(BaseModel):
    output_path: str
    adjustments: MatchAdjustments


def _classify_deviation(
    abs_dev: float,
    deviation: float,
    thresholds: tuple[float, float, float] | None = None,
) -> str:
    """Classify a deviation magnitude into a rating string."""
    if thresholds is None:
        t_on, t_slight, t_mod = (
            _THRESHOLD_ON_TARGET,
            _THRESHOLD_SLIGHT,
            _THRESHOLD_MODERATE,
        )
    else:
        t_on, t_slight, t_mod = thresholds

    if abs_dev <= t_on:
        return "on_target"
    elif abs_dev <= t_slight:
        return "slightly_above" if deviation > 0 else "slightly_below"
    elif abs_dev <= t_mod:
        return "above_target" if deviation > 0 else "below_target"
    else:
        return "significantly_above" if deviation > 0 else "significantly_below"


def _rate_deviation(
    value: float,
    target: float,
    thresholds: tuple[float, float, float] | None = None,
    round_fn=round_db,
) -> DeviationResult:
    deviation = value - target
    rating = _classify_deviation(abs(deviation), deviation, thresholds)
    return DeviationResult(
        value=round_fn(value),
        target=round_fn(target),
        deviation=round_fn(deviation),
        rating=rating,
    )


def _rate_deviation_ref(
    value: float,
    reference: float,
    thresholds: tuple[float, float, float] | None = None,
    round_fn=round_db,
) -> DeviationResult:
    dev = _rate_deviation(value, reference, thresholds, round_fn=round_fn)
    return DeviationResult(
        value=dev.value,
        reference=dev.target,
        target=None,
        deviation=dev.deviation,
        rating=dev.rating,
    )


def _rate_range_deviation(
    value: float,
    target_range: tuple[float, float],
    thresholds: tuple[float, float, float] | None = None,
    round_fn=round_db,
) -> RangeDeviationResult:
    range_min, range_max = target_range

    if range_min <= value <= range_max:
        deviation = 0.0
        rating = "on_target"
    elif value < range_min:
        deviation = value - range_min
        rating = _classify_deviation(abs(deviation), deviation, thresholds)
    else:
        deviation = value - range_max
        rating = _classify_deviation(abs(deviation), deviation, thresholds)

    return RangeDeviationResult(
        value=round_fn(value),
        target_range=[range_min, range_max],
        deviation=round_fn(deviation),
        rating=rating,
    )


def _normalize_band_energies(band_db: dict[str, float]) -> dict[str, float]:
    if not band_db:
        return {}
    values = list(band_db.values())
    mean_db = float(np.mean(values))
    return {k: round(v - mean_db, 2) for k, v in band_db.items()}


def _check_mono_below(audio, cutoff_hz: float) -> MonoBelowResult:
    from scipy.signal import butter, sosfilt

    if audio.num_channels == 1:
        return MonoBelowResult(
            mono_below_hz=cutoff_hz,
            bass_correlation=1.0,
            has_stereo_bass=False,
            rating="on_target",
        )

    nyquist = audio.sample_rate / 2.0
    if cutoff_hz >= nyquist:
        bass_left = audio.left
        bass_right = audio.right
    else:
        sos = butter(4, cutoff_hz / nyquist, btype="low", output="sos")
        bass_left = sosfilt(sos, audio.left)
        bass_right = sosfilt(sos, audio.right)

    rms_left = float(np.sqrt(np.mean(bass_left**2)))
    rms_right = float(np.sqrt(np.mean(bass_right**2)))
    if rms_left < 1e-8 or rms_right < 1e-8:
        return MonoBelowResult(
            mono_below_hz=cutoff_hz,
            bass_correlation=1.0,
            has_stereo_bass=False,
            rating="on_target",
        )

    with np.errstate(invalid="ignore"):
        corr = np.corrcoef(bass_left, bass_right)[0, 1]
    if np.isnan(corr):
        corr = 1.0
    correlation = float(corr)

    has_stereo_bass = correlation < _BASS_MONO_THRESHOLD
    rating = "below_target" if has_stereo_bass else "on_target"

    return MonoBelowResult(
        mono_below_hz=cutoff_hz,
        bass_correlation=correlation,
        has_stereo_bass=has_stereo_bass,
        rating=rating,
    )


def _map_width_to_range(descriptor: str) -> tuple[float, float]:
    return _WIDTH_RANGES.get(descriptor, (0.0, 2.0))


def _unmeasurable_deviation(key_name: str = "target") -> DeviationResult:
    return DeviationResult(rating="unmeasurable")
