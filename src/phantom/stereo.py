"""Stereo field analysis functions.

Provides analyze_stereo() which accepts an AudioData object and returns
a StereoResult model with L/R correlation, stereo width, mid/side energy
ratio, L/R energy balance, and panorama distribution.

Uses numpy for all calculations (no Essentia needed).
Mono input returns deterministic defaults (per D-03).
Near-silent audio returns None for all values (per D-05).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from pydantic import BaseModel, field_validator

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom._rounding import round_db, round_ratio, round_pct
from phantom._utils import is_near_silent, wrap_errors


class PanoramaDistribution(BaseModel):
    """Stereo panorama distribution percentages."""

    left: float = 0.0
    center: float = 0.0
    right: float = 0.0

    @field_validator("left", "center", "right", mode="before")
    @classmethod
    def _round_pct(cls, v: float) -> float:
        return round_pct(v)


class StereoResult(BaseModel):
    """Result of stereo field analysis."""

    correlation: Optional[float] = None
    stereo_width: Optional[float] = None
    mid_side_ratio_db: Optional[float] = None
    balance_db: Optional[float] = None
    panorama_pct: Optional[PanoramaDistribution] = None

    @field_validator("correlation", "stereo_width", mode="before")
    @classmethod
    def _round_ratio(cls, v: float | None) -> float | None:
        return round_ratio(v)

    @field_validator("mid_side_ratio_db", "balance_db", mode="before")
    @classmethod
    def _round_db(cls, v: float | None) -> float | None:
        return round_db(v)


def _silent_stereo_result() -> StereoResult:
    """Return a stereo result with all values set to None."""
    return StereoResult()


def _panorama_distribution(
    left: np.ndarray,
    right: np.ndarray,
    frame_size: int = 4096,
    hop: int = 2048,
) -> PanoramaDistribution:
    """Compute panorama distribution as left/center/right percentages.

    Iterates over frames, computes per-frame energy for L and R channels,
    and classifies each frame as left, center, or right based on the
    panning coefficient.

    Args:
        left: Left channel samples (1D float array).
        right: Right channel samples (1D float array).
        frame_size: Number of samples per analysis frame.
        hop: Hop size between frames.

    Returns:
        PanoramaDistribution with left, center, right as percentages summing to ~100.
    """
    n_left = 0
    n_center = 0
    n_right = 0
    total = 0
    center_threshold = 0.1

    num_samples = len(left)

    for start in range(0, num_samples - frame_size + 1, hop):
        end = start + frame_size
        fl = left[start:end]
        fr = right[start:end]

        el = float(np.mean(fl**2))
        er = float(np.mean(fr**2))

        # Skip near-silent frames
        if el + er < 1e-10:
            continue

        total += 1
        pan = (er - el) / (el + er)

        if abs(pan) < center_threshold:
            n_center += 1
        elif pan < 0:
            n_left += 1
        else:
            n_right += 1

    # All frames silent: default to center
    if total == 0:
        return PanoramaDistribution(left=0.0, center=100.0, right=0.0)

    return PanoramaDistribution(
        left=100.0 * n_left / total,
        center=100.0 * n_center / total,
        right=100.0 * n_right / total,
    )


@wrap_errors("Stereo analysis failed")
def analyze_stereo(audio: AudioData) -> StereoResult:
    """Analyze stereo field characteristics of an audio signal.

    Computes five stereo descriptors:
      - correlation: L/R Pearson correlation coefficient [-1.0, 1.0]
      - stereo_width: Side/mid RMS energy ratio (>= 0.0)
      - mid_side_ratio_db: Mid-to-side energy ratio in dB (None when infinite)
      - balance_db: L/R energy balance in dB (positive = right louder)
      - panorama_pct: Frame-based panorama distribution (left/center/right %)

    Mono input returns deterministic defaults per D-03.
    Near-silent audio returns None for all values.

    Args:
        audio: AudioData object to analyze.

    Returns:
        StereoResult model. Values are None for near-silent audio.

    Raises:
        AnalysisError: If audio has 0 samples or computation fails.
    """
    mono = audio.mono

    # Empty-samples guard
    if len(mono) == 0:
        raise AnalysisError("Stereo analysis failed: audio has 0 samples")

    # Near-silence guard
    # For stereo, check individual channels -- inverted polarity (R = -L) would
    # cancel in the mono mixdown but each channel carries real energy.
    if audio.num_channels == 1:
        signal_silent = is_near_silent(mono)
    else:
        signal_silent = is_near_silent(audio.left) and is_near_silent(audio.right)

    if signal_silent:
        return _silent_stereo_result()

    # Mono guard (per D-03): return deterministic defaults
    if audio.num_channels == 1:
        return StereoResult(
            correlation=1.0,
            stereo_width=0.0,
            mid_side_ratio_db=None,  # effectively infinite: pure mid, no side
            balance_db=0.0,
            panorama_pct=PanoramaDistribution(left=0.0, center=100.0, right=0.0),
        )

    left = audio.left
    right = audio.right

    # STER-01: L/R correlation
    # np.corrcoef returns NaN when a channel has zero variance (e.g. all
    # zeros).  Suppress the runtime warning and fall back to 0.0.
    with np.errstate(invalid="ignore"):
        corr_val = np.corrcoef(left, right)[0, 1]
    correlation = 0.0 if np.isnan(corr_val) else float(corr_val)

    # Mid/Side decomposition
    mid = (left + right) / 2.0
    side = (left - right) / 2.0
    rms_mid = float(np.sqrt(np.mean(mid**2)))
    rms_side = float(np.sqrt(np.mean(side**2)))

    # STER-02: Stereo width (side/mid energy ratio)
    stereo_width = float(rms_side / (rms_mid + 1e-10))

    # STER-03: Mid/side ratio in dB
    if rms_side < 1e-10:
        mid_side_ratio_db = None  # effectively infinite: pure mid, no side
    elif rms_mid < 1e-10:
        mid_side_ratio_db = None  # effectively infinite: pure side, no mid
    else:
        mid_side_ratio_db = float(20 * np.log10(rms_mid / rms_side))

    # STER-04: L/R energy balance in dB
    rms_left = float(np.sqrt(np.mean(left**2)))
    rms_right = float(np.sqrt(np.mean(right**2)))
    balance_db = float(20 * np.log10((rms_right + 1e-10) / (rms_left + 1e-10)))

    # STER-05: Panorama distribution
    panorama_pct = _panorama_distribution(left, right)

    return StereoResult(
        correlation=correlation,
        stereo_width=stereo_width,
        mid_side_ratio_db=mid_side_ratio_db,
        balance_db=balance_db,
        panorama_pct=panorama_pct,
    )
