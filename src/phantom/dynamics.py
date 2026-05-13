"""Dynamics measurement functions.

Provides analyze_dynamics() which accepts an AudioData object and returns
a DynamicsResult Pydantic model with RMS level, peak level, crest factor,
dynamic range, and dynamic complexity.

Uses numpy for RMS/peak/crest/range calculations and Essentia's
DynamicComplexity for loudness variation measurement.
Near-silent audio returns None for all values (per D-05).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import essentia.standard as es
from pydantic import BaseModel, field_validator

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom._rounding import round_db, round_ratio
from phantom._utils import is_near_silent, _block_rms_db, wrap_errors


class DynamicsResult(BaseModel):
    """Result of dynamics analysis."""

    rms_dbfs: Optional[float] = None
    peak_dbfs: Optional[float] = None
    crest_factor_db: Optional[float] = None
    crest_factor_is_low: Optional[bool] = None
    dynamic_range_db: Optional[float] = None
    dynamic_complexity: Optional[float] = None
    loudness_db: Optional[float] = None

    @field_validator(
        "rms_dbfs",
        "peak_dbfs",
        "crest_factor_db",
        "dynamic_range_db",
        "loudness_db",
        mode="before",
    )
    @classmethod
    def _round_db(cls, v: float | None) -> float | None:
        return round_db(v)

    @field_validator("dynamic_complexity", mode="before")
    @classmethod
    def _round_ratio(cls, v: float | None) -> float | None:
        return round_ratio(v)


def _silent_dynamics_result() -> DynamicsResult:
    """Return a dynamics result with all values set to None."""
    return DynamicsResult()


@wrap_errors("Dynamics analysis failed")
def analyze_dynamics(audio: AudioData) -> DynamicsResult:
    """Analyze dynamics characteristics of an audio signal.

    Computes seven dynamics descriptors from the mono mixdown of the input:
      - rms_dbfs: RMS level in dBFS
      - peak_dbfs: Peak level in dBFS
      - crest_factor_db: Crest factor in dB (peak_dbfs - rms_dbfs)
      - crest_factor_is_low: True if crest_factor_db < 6.0
      - dynamic_range_db: 95th-5th percentile of block RMS in dB
      - dynamic_complexity: Essentia DynamicComplexity descriptor
      - loudness_db: Average loudness from DynamicComplexity

    Args:
        audio: AudioData object to analyze.

    Returns:
        DynamicsResult with seven dynamics fields. Values are None for
        near-silent audio.

    Raises:
        AnalysisError: If analysis fails or audio has 0 samples.
    """
    mono = audio.mono

    # Empty-samples guard
    if len(mono) == 0:
        raise AnalysisError("Dynamics analysis failed: audio has 0 samples")

    # Near-silence guard
    if is_near_silent(mono):
        return _silent_dynamics_result()

    # -- RMS level (DYN-01) --
    rms = float(np.sqrt(np.mean(mono**2)))
    rms_dbfs = float(20 * np.log10(rms + 1e-10))

    # -- Peak level (DYN-02) --
    peak = float(np.max(np.abs(mono)))
    peak_dbfs = float(20 * np.log10(peak + 1e-10))

    # -- Crest factor (DYN-03) --
    crest_factor_db = float(peak_dbfs - rms_dbfs)
    crest_factor_is_low = bool(crest_factor_db < 6.0)

    # -- Dynamic range (DYN-04) --
    block_rms_db = _block_rms_db(mono)
    if len(block_rms_db) >= 2:
        dynamic_range_db = float(
            np.percentile(block_rms_db, 95) - np.percentile(block_rms_db, 5)
        )
    else:
        dynamic_range_db = 0.0

    # -- Dynamic complexity (DYN-05) --
    dc = es.DynamicComplexity(sampleRate=audio.sample_rate, frameSize=0.2)
    complexity, loudness = dc(mono)
    dynamic_complexity = float(complexity)
    if not np.isfinite(dynamic_complexity):
        dynamic_complexity = None
    loudness_db_val = float(loudness)
    if not np.isfinite(loudness_db_val):
        loudness_db_val = None

    return DynamicsResult(
        rms_dbfs=rms_dbfs,
        peak_dbfs=peak_dbfs,
        crest_factor_db=crest_factor_db,
        crest_factor_is_low=crest_factor_is_low,
        dynamic_range_db=dynamic_range_db,
        dynamic_complexity=dynamic_complexity,
        loudness_db=loudness_db_val,
    )
