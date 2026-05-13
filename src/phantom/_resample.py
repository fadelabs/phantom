"""Audio resampling utility for cross-file comparison.

Provides resample_to_match() which upsamples audio to a target sample rate
using scipy.signal.resample_poly (polyphase FIR filter).  Only upsampling is
allowed — downsampling would discard frequency content above the new Nyquist
limit, which is unacceptable for analysis accuracy.
"""

from __future__ import annotations

import logging
from math import gcd

import numpy as np
from scipy.signal import resample_poly

from phantom.audio import AudioData

logger = logging.getLogger(__name__)


def resample_to_match(audio: AudioData, target_sr: int) -> AudioData:
    """Resample *audio* to *target_sr* Hz (upsample only).

    If *audio.sample_rate* already equals *target_sr*, the original
    :class:`AudioData` is returned unchanged (identity fast-path).

    Args:
        audio: Source audio data to resample.
        target_sr: Desired sample rate in Hz.  Must be >= audio.sample_rate.

    Returns:
        A new :class:`AudioData` with samples resampled to *target_sr*, or
        the original object when no resampling is needed.

    Raises:
        ValueError: If *target_sr* < *audio.sample_rate* (downsampling).
    """
    if target_sr == audio.sample_rate:
        return audio

    if target_sr < audio.sample_rate:
        raise ValueError(
            f"target_sr must be >= audio sample rate "
            f"({target_sr} < {audio.sample_rate})"
        )

    # Compute rational resampling ratio via GCD
    g = gcd(audio.sample_rate, target_sr)
    up = target_sr // g
    down = audio.sample_rate // g

    logger.warning(
        "Resampling audio from %d Hz to %d Hz (up=%d, down=%d)",
        audio.sample_rate,
        target_sr,
        up,
        down,
    )

    # Resample each channel independently
    num_channels = audio.num_channels
    resampled_channels = []
    for ch in range(num_channels):
        channel_data = resample_poly(audio.samples[:, ch], up, down)
        resampled_channels.append(channel_data.astype(np.float32))

    # Stack channels back into [num_samples, num_channels] shape
    resampled = np.column_stack(resampled_channels)
    if resampled.ndim == 1:
        resampled = resampled.reshape(-1, 1)

    num_samples = resampled.shape[0]
    duration = num_samples / target_sr

    return AudioData(
        samples=resampled,
        sample_rate=target_sr,
        num_channels=num_channels,
        duration=duration,
        num_samples=num_samples,
        file_path=audio.file_path,
    )
