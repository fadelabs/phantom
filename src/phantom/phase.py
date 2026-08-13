"""Phase coherence analysis functions.

Provides analyze_phase() for single-file L/R phase coherence and
compare_phase() for cross-file phase comparison (per D-01).

analyze_phase returns a PhaseResult model with overall correlation,
per-band correlation, and polarity inversion detection.
compare_phase returns a PhaseCompareResult model with time delay,
cross-file correlation, and polarity inversion (per D-02).

Uses numpy for correlation, scipy.signal for bandpass filtering,
and scipy.fft for GCC-PHAT delay estimation.
Mono input returns deterministic defaults (per D-03).
Near-silent audio returns None for all values (per D-05).
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import ClassVar, Optional

import numpy as np
import scipy.signal as sig
from scipy.fft import fft, ifft

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom._bands import FlatMapModel
from phantom._resample import align_sample_rates
from phantom._rounding import RoundedModel, round_dict, round_ms, round_ratio
from phantom._settings import AnalysisSettings, analysis_settings
from phantom._utils import guarded_mono, is_near_silent, wrap_errors


class PerBandCorrelation(FlatMapModel):
    """Typed per-band L/R correlation map (C.2).

    Fields mirror ``PHASE_BANDS``; each field's name is already the
    serialized key (``"sub"``, ``"low_mid"``, ...), so model_dump() output
    is byte-identical to the raw dicts this replaces. Bands above Nyquist at
    the file's sample rate are simply absent (fields stay unset).
    """

    sub: Optional[float] = None
    low: Optional[float] = None
    low_mid: Optional[float] = None
    mid: Optional[float] = None
    high: Optional[float] = None
    air: Optional[float] = None


class PhaseResult(RoundedModel):
    """Result of phase coherence analysis."""

    phase_correlation: Optional[float] = None
    per_band_correlation: Optional[PerBandCorrelation] = None
    polarity_inverted: Optional[bool] = None

    _ROUND_FIELDS: ClassVar[dict[str, Callable[[object], object]]] = {
        "phase_correlation": round_ratio,
        # Per-band correlations round to 4dp (4th-order bandpass precision)
        # before the typed map validates them (review F8).
        "per_band_correlation": partial(round_dict, dp=4),
    }


class PhaseCompareResult(RoundedModel):
    """Result of cross-file phase comparison."""

    delay_samples: Optional[int] = None
    delay_ms: Optional[float] = None
    correlation: Optional[float] = None
    polarity_inverted: Optional[bool] = None

    _ROUND_FIELDS: ClassVar[dict[str, Callable[[object], object]]] = {
        "delay_ms": round_ms,
        "correlation": round_ratio,
    }


# Frequency bands for per-band phase correlation (PHAS-02). Keys are also the
# PerBandCorrelation field names, so the serialized keys stay identical.
PHASE_BANDS = {
    "sub": (20, 80),
    "low": (80, 250),
    "low_mid": (250, 500),
    "mid": (500, 2000),
    "high": (2000, 8000),
    "air": (8000, 20000),
}


def _silent_phase_result() -> PhaseResult:
    """Return a phase result with all values set to None."""
    return PhaseResult()


def _silent_compare_result() -> PhaseCompareResult:
    """Return a compare result with all values set to None."""
    return PhaseCompareResult()


def _per_band_correlation(
    left: np.ndarray,
    right: np.ndarray,
    sample_rate: int,
) -> dict:
    """Compute L/R correlation for each frequency band.

    Applies a 4th-order Butterworth bandpass filter per band, then
    computes the Pearson correlation between filtered L and R channels.

    Bands whose lower frequency is above the Nyquist frequency are skipped.
    """
    nyq = sample_rate / 2.0
    results: dict[str, float] = {}

    for name, (lo, hi) in PHASE_BANDS.items():
        if lo >= nyq:
            continue
        hi_clamped = min(hi, nyq * 0.99)
        sos = sig.butter(4, [lo / nyq, hi_clamped / nyq], btype="band", output="sos")
        fl = sig.sosfilt(sos, left)
        fr = sig.sosfilt(sos, right)
        with np.errstate(invalid="ignore"):
            corr_val = np.corrcoef(fl, fr)[0, 1]
        results[name] = 0.0 if np.isnan(corr_val) else float(corr_val)

    return results


def _gcc_phat_delay(
    sig1: np.ndarray,
    sig2: np.ndarray,
    sample_rate: int,
    max_delay_ms: float = 50.0,
    settings: AnalysisSettings | None = None,
) -> tuple[int, float]:
    """Estimate time delay between two signals using GCC-PHAT.

    Returns (delay_samples, delay_ms).
    Positive delay means sig2 lags sig1.
    """
    # Truncate to configurable window (default 10s) -- only 50ms of
    # cross-correlation is used, and full-length FFT would allocate
    # multi-GB arrays for long files. The window is AnalysisSettings-
    # tunable via PHANTOM_PHAT_WINDOW_S (C.1).
    effective = settings if settings is not None else analysis_settings()
    max_samples = int(sample_rate * effective.phat_window_s)
    if len(sig1) > max_samples:
        sig1 = sig1[:max_samples]
    if len(sig2) > max_samples:
        sig2 = sig2[:max_samples]

    n = len(sig1) + len(sig2) - 1
    SIG1 = fft(sig1, n=n)
    SIG2 = fft(sig2, n=n)
    # Cross-spectrum: conj(SIG1) * SIG2 so positive delay = sig2 lags sig1
    R = np.conj(SIG1) * SIG2
    R_phat = R / (np.abs(R) + 1e-10)
    cc = np.real(ifft(R_phat))
    max_shift = int(max_delay_ms / 1000.0 * sample_rate)
    cc_region = np.concatenate([cc[-max_shift:], cc[: max_shift + 1]])
    delay_samples = int(np.argmax(cc_region) - max_shift)
    delay_ms = float(delay_samples / sample_rate * 1000.0)
    return delay_samples, delay_ms


@wrap_errors("Phase analysis failed")
def analyze_phase(
    audio: AudioData, settings: AnalysisSettings | None = None
) -> PhaseResult:
    """Analyze phase coherence of a single audio file.

    For stereo input, computes:
      - phase_correlation: overall L/R Pearson correlation [-1.0, 1.0]
      - per_band_correlation: dict of per-band L/R correlations
      - polarity_inverted: True if overall correlation is below the
        polarity threshold (default -0.5, AnalysisSettings-tunable)

    For mono input, returns deterministic defaults (per D-03):
      - phase_correlation: 1.0
      - per_band_correlation: {all applicable bands: 1.0}
      - polarity_inverted: False

    For near-silent audio, returns None for all values (per D-05).

    Args:
        audio: AudioData object to analyze.

    Returns:
        PhaseResult model with phase_correlation, per_band_correlation,
        polarity_inverted.

    Raises:
        AnalysisError: If audio has 0 samples or analysis fails.
    """
    effective = settings if settings is not None else analysis_settings()

    # Empty-samples guard (the stereo branch below checks channels individually)
    if audio.num_samples == 0:
        raise AnalysisError("Phase analysis failed: audio has 0 samples")

    # Mono guard (D-03): deterministic defaults after the empty/silence guards.
    if audio.num_channels == 1:
        if guarded_mono(audio, "Phase analysis failed") is None:
            return _silent_phase_result()
        nyq = audio.sample_rate / 2.0
        band_defaults = {
            name: 1.0 for name, (lo, _hi) in PHASE_BANDS.items() if lo < nyq
        }
        return PhaseResult(
            phase_correlation=1.0,
            per_band_correlation=band_defaults,
            polarity_inverted=False,
        )

    # Stereo: near-silence guard checks individual channels, not mono mix
    # (out-of-phase stereo has zero mono mix but non-silent channels). The
    # per-channel check cannot use the (mono) memoized is_near_silent.
    left = audio.left
    right = audio.right
    if is_near_silent(left) and is_near_silent(right):
        return _silent_phase_result()

    # Stereo computation
    # PHAS-01: Overall correlation
    # np.corrcoef returns NaN when a channel has zero variance (e.g. one
    # channel is silent).  Suppress the runtime warning and fall back to 0.0.
    with np.errstate(invalid="ignore"):
        corr_val = np.corrcoef(left, right)[0, 1]
    overall_corr = 0.0 if np.isnan(corr_val) else float(corr_val)

    # PHAS-02: Per-band correlation
    band_corr = _per_band_correlation(left, right, audio.sample_rate)

    # PHAS-03: Polarity inversion detection
    polarity_inverted = bool(overall_corr < effective.polarity_threshold)

    return PhaseResult(
        phase_correlation=overall_corr,
        per_band_correlation=band_corr,
        polarity_inverted=polarity_inverted,
    )


@wrap_errors("Phase comparison failed")
def compare_phase(
    audio1: AudioData,
    audio2: AudioData,
    settings: AnalysisSettings | None = None,
) -> PhaseCompareResult:
    """Compare phase between two audio files.

    Computes:
      - delay_samples: time delay in samples (positive = audio2 lags audio1)
      - delay_ms: time delay in milliseconds
      - correlation: cross-file Pearson correlation
      - polarity_inverted: True if correlation is below the polarity
        threshold (default -0.5, AnalysisSettings-tunable)

    If inputs have different sample rates, the lower-rate audio is
    automatically upsampled to the higher rate. Length mismatches are
    handled by truncating to the shorter signal.

    For near-silent audio, returns None for all values (per D-05).

    Args:
        audio1: First AudioData object.
        audio2: Second AudioData object.

    Returns:
        PhaseCompareResult model with delay_samples, delay_ms, correlation,
        polarity_inverted.

    Raises:
        AnalysisError: If audio has 0 samples or analysis fails.
    """
    effective = settings if settings is not None else analysis_settings()

    # Auto-resample on sample rate mismatch
    audio1, audio2 = align_sample_rates(audio1, audio2)

    # Empty/silence guards (B.2): mono per input, or None when near-silent.
    mono1 = guarded_mono(audio1, "Phase comparison failed")
    mono2 = guarded_mono(audio2, "Phase comparison failed")
    if mono1 is None or mono2 is None:
        return _silent_compare_result()

    # Truncate to shorter signal
    min_len = min(len(mono1), len(mono2))
    mono1 = mono1[:min_len]
    mono2 = mono2[:min_len]

    # PHAS-04: GCC-PHAT delay estimation
    delay_samples, delay_ms = _gcc_phat_delay(
        mono1, mono2, audio1.sample_rate, settings=effective
    )

    # PHAS-05: Cross-file correlation
    with np.errstate(invalid="ignore"):
        corr_val = np.corrcoef(mono1, mono2)[0, 1]
    corr = 0.0 if np.isnan(corr_val) else float(corr_val)

    # PHAS-06: Cross-file polarity inversion
    polarity_inverted = bool(corr < effective.polarity_threshold)

    return PhaseCompareResult(
        delay_samples=delay_samples,
        delay_ms=delay_ms,
        correlation=corr,
        polarity_inverted=polarity_inverted,
    )
