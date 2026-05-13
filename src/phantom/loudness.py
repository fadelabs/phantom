"""Loudness measurement functions.

Provides analyze_loudness() which accepts an AudioData object and returns
a LoudnessResult Pydantic model with EBU R128 integrated LUFS, ITU-R
BS.1770-4 true peak, loudness range, short-term LUFS, and momentary LUFS.

Uses Essentia's LoudnessEBUR128 as the single loudness engine (per D-07).
Near-silent audio returns None for all values (per LOUD-05).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import essentia.standard as es
from pydantic import BaseModel, field_validator

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom._rounding import round_db
from phantom._utils import is_near_silent, wrap_errors


class LufsStats(BaseModel):
    """Summary statistics for a LUFS time series.

    Replaces unbounded float arrays with a fixed-size payload (9 fields)
    that captures all analytically useful information regardless of audio
    length. Mitigates T-18-01 (denial of service via large JSON payloads).
    """

    min: float
    max: float
    mean: float
    count: int
    p5: float
    p25: float
    p50: float
    p75: float
    p95: float

    @field_validator(
        "min", "max", "mean", "p5", "p25", "p50", "p75", "p95", mode="before"
    )
    @classmethod
    def _round_db(cls, v: float) -> float:
        return round(v, 2) if v is not None else v

    @classmethod
    def from_array(cls, values: list[float] | None) -> LufsStats | None:
        """Build stats from a raw LUFS time series.

        Returns None if *values* is None or empty.
        """
        if values is None or len(values) == 0:
            return None
        arr = np.asarray(values, dtype=np.float64)
        percentiles = np.percentile(arr, [5, 25, 50, 75, 95], method="linear")
        return cls(
            min=float(np.min(arr)),
            max=float(np.max(arr)),
            mean=float(np.mean(arr)),
            count=len(values),
            p5=float(percentiles[0]),
            p25=float(percentiles[1]),
            p50=float(percentiles[2]),
            p75=float(percentiles[3]),
            p95=float(percentiles[4]),
        )


class LoudnessResult(BaseModel):
    """Result of EBU R128 loudness analysis."""

    integrated_lufs: Optional[float] = None
    true_peak_dbtp: Optional[float] = None
    loudness_range_lu: Optional[float] = None
    short_term_lufs: Optional[LufsStats] = None
    momentary_lufs: Optional[LufsStats] = None

    @field_validator(
        "integrated_lufs", "true_peak_dbtp", "loudness_range_lu", mode="before"
    )
    @classmethod
    def _round_db(cls, v: float | None) -> float | None:
        return round_db(v)


def _silent_loudness_result() -> LoudnessResult:
    """Return a loudness result with all values set to None."""
    return LoudnessResult()


@wrap_errors("Loudness analysis failed")
def analyze_loudness(audio: AudioData) -> LoudnessResult:
    """Analyze loudness characteristics of an audio signal.

    Computes five EBU R128 / ITU-R BS.1770-4 loudness descriptors from
    the mono mixdown of the input:
      - integrated_lufs: EBU R128 integrated loudness (LUFS)
      - true_peak_dbtp: ITU-R BS.1770-4 true peak level (dBTP)
      - loudness_range_lu: EBU R128 loudness range (LU)
      - short_term_lufs: short-term loudness summary stats (3s windows, LufsStats)
      - momentary_lufs: momentary loudness summary stats (400ms windows, LufsStats)

    Args:
        audio: AudioData object to analyze.

    Returns:
        LoudnessResult with the five loudness fields. Values are None for
        near-silent audio.

    Raises:
        AnalysisError: If Essentia algorithms fail.
    """
    mono = audio.mono
    sample_rate = audio.sample_rate

    # Empty-samples guard
    if len(mono) == 0:
        raise AnalysisError("Loudness analysis failed: audio has 0 samples")

    # Near-silence guard
    if is_near_silent(mono):
        return _silent_loudness_result()

    # -- EBU R128 loudness (LOUD-01, LOUD-03, LOUD-04) --
    # LoudnessEBUR128 requires stereo input.
    # For mono audio, duplicate to both channels per EBU Tech 3341 s5.
    # This is the correct behavior: mono content measures identically
    # whether played from one or both speakers at the same level.
    if audio.num_channels == 1:
        stereo = np.column_stack([mono, mono])
    else:
        stereo = np.column_stack([audio.samples[:, 0], audio.samples[:, 1]])

    loudness_algo = es.LoudnessEBUR128(
        hopSize=0.1,
        sampleRate=sample_rate,
        startAtZero=True,
    )
    momentary, short_term, integrated, lra = loudness_algo(stereo)

    integrated_lufs = float(integrated)
    loudness_range_lu = float(lra)
    short_term_lufs = LufsStats.from_array([float(v) for v in short_term])
    momentary_lufs = LufsStats.from_array([float(v) for v in momentary])

    # -- True peak (LOUD-02) --
    # Measure true peak per channel and take the maximum.
    # ITU-R BS.1770-4 specifies that true peak is the maximum
    # true peak level across all channels.
    eps = np.finfo(np.float32).eps
    channel_peaks = []
    for ch in range(audio.num_channels):
        tp_algo = es.TruePeakDetector(
            version=4,
            sampleRate=sample_rate,
            oversamplingFactor=4,
        )
        channel_signal = audio.samples[:, ch]
        _, tp_output = tp_algo(channel_signal)
        channel_peaks.append(float(np.max(np.abs(tp_output))))

    max_tp = max(channel_peaks)
    true_peak_dbtp = float(20 * np.log10(max_tp + eps))

    return LoudnessResult(
        integrated_lufs=integrated_lufs,
        true_peak_dbtp=true_peak_dbtp,
        loudness_range_lu=loudness_range_lu,
        short_term_lufs=short_term_lufs,
        momentary_lufs=momentary_lufs,
    )
