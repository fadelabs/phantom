"""Shared per-channel true-peak computation (P-02, P-06).

``es.TruePeakDetector`` (x4-oversampled FIR per ITU-R BS.1770-4) is the single
most expensive operation in the analysis pipeline. Both loudness measurement
and inter-sample-peak problem detection need it, and in ``full_diagnostic`` both
run on the same file — previously computing it twice.

``channel_true_peaks`` computes per-channel ``(sample_peak, true_peak)`` once and
memoizes the result on the ``AudioData`` instance so loudness and problem
detection share a single computation (P-02). A single ``TruePeakDetector`` is
constructed and reused across channels (P-06); the detector is stateless across
the two channels here (validated by the numeric-parity test in the suite).

The memo lives in ``audio.__dict__["_true_peaks"]`` — the same mechanism
``functools.cached_property`` uses for ``AudioData.mono`` / ``mono_rms``, and
proven safe with this Pydantic v2 model.
"""

from __future__ import annotations

import numpy as np
import essentia.standard as es

from phantom.audio import AudioData


def channel_true_peaks(audio: AudioData) -> list[tuple[float, float]]:
    """Per-channel ``(sample_peak, true_peak)`` via ITU-R BS.1770-4 x4 oversampling.

    Constructs ONE ``TruePeakDetector`` and reuses it across channels (P-06).
    The result is memoized on the ``AudioData`` instance so loudness and problem
    detection share a single computation (P-02).

    Args:
        audio: AudioData object to analyze.

    Returns:
        A list of ``(sample_peak, true_peak)`` tuples, one per channel, where
        both values are linear (not dB) absolute maxima.
    """
    cached = audio.__dict__.get("_true_peaks")
    if cached is not None:
        return cached

    tp_algo = es.TruePeakDetector(
        version=4, sampleRate=audio.sample_rate, oversamplingFactor=4
    )
    out: list[tuple[float, float]] = []
    for ch in range(audio.num_channels):
        sig = audio.samples[:, ch]
        sample_peak = float(np.max(np.abs(sig))) if len(sig) else 0.0
        _, tp_output = tp_algo(sig)
        true_peak = float(np.max(np.abs(tp_output))) if len(tp_output) else 0.0
        out.append((sample_peak, true_peak))

    audio.__dict__["_true_peaks"] = out
    return out
