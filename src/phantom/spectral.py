"""Spectral analysis functions.

Provides analyze_spectrum() which accepts an AudioData object and returns
a SpectralResult Pydantic model with spectral centroid, rolloff, flatness,
contrast, dissonance, and octave band energy distribution.

Uses Essentia's standard-mode algorithms for all spectral feature extraction.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import essentia.standard as es

from phantom._bands import (  # re-exported for backward compatibility (B.6)
    OCTAVE_CENTERS,  # noqa: F401 -- tests import it from phantom.spectral
    _BAND_LABELS,
    _octave_band_energies,
)
from phantom.audio import AudioData
from phantom._rounding import (
    RoundedModel,
    round_db_dict,
    round_hz,
    round_ratio,
    round_ratio_list,
)
from phantom._utils import guarded_mono, wrap_errors


class SpectralResult(RoundedModel):
    """Result of spectral analysis."""

    spectral_centroid_hz: Optional[float] = None
    spectral_rolloff_hz: Optional[float] = None
    spectral_flatness: Optional[float] = None
    spectral_contrast: Optional[list[float]] = None
    dissonance: Optional[float] = None
    octave_band_energy_db: Optional[dict[str, float]] = None

    _ROUND_FIELDS = {
        "spectral_centroid_hz": round_hz,
        "spectral_rolloff_hz": round_hz,
        "spectral_flatness": round_ratio,
        "dissonance": round_ratio,
        "spectral_contrast": round_ratio_list,
        "octave_band_energy_db": round_db_dict,
    }


def _silent_spectral_result() -> SpectralResult:
    """Return a spectral result with all values set to None."""
    return SpectralResult()


@wrap_errors("Spectral analysis failed")
def analyze_spectrum(audio: AudioData) -> SpectralResult:
    """Analyze spectral characteristics of an audio signal.

    Computes six spectral descriptors from the mono mixdown of the input:
      - spectral_centroid_hz: center of spectral mass (Hz)
      - spectral_rolloff_hz: frequency below which 85% of energy lies (Hz)
      - spectral_flatness: tonality measure, 0 (tonal) to 1 (noise-like)
      - spectral_contrast: per-band peak-to-valley contrast (list of floats)
      - dissonance: spectral roughness, 0 (consonant) to 1 (dissonant)
      - octave_band_energy_db: energy per octave band in dB (dict)

    Args:
        audio: AudioData object to analyze.

    Returns:
        SpectralResult with the six spectral fields. Values are None for
        near-silent audio.

    Raises:
        AnalysisError: If Essentia algorithms fail.
    """
    sample_rate = audio.sample_rate

    # Empty/silence guards (B.2): mono, or None when near-silent.
    mono = guarded_mono(audio, "Spectral analysis failed")
    if mono is None:
        return _silent_spectral_result()

    # Spectral features: 2048/1024 (~46ms/~23ms at 44.1kHz) per AES standard for tonal analysis
    frame_size = 2048
    hop_size = 1024

    windowing = es.Windowing(type="hann", size=frame_size)
    spectrum = es.Spectrum(size=frame_size)
    centroid = es.Centroid(range=sample_rate / 2)
    rolloff = es.RollOff(cutoff=0.85, sampleRate=sample_rate)  # 85% per Peeters 2004
    flatness = es.Flatness()
    spectral_contrast = es.SpectralContrast(
        sampleRate=sample_rate, frameSize=frame_size
    )
    spectral_peaks = es.SpectralPeaks(
        sampleRate=sample_rate,
        maxPeaks=100,
        orderBy="frequency",  # 100 peaks sufficient for dissonance curve
    )
    dissonance_algo = es.Dissonance()

    centroids = []
    rolloffs = []
    flatnesses = []
    contrasts = []
    dissonances = []

    for frame in es.FrameGenerator(mono, frameSize=frame_size, hopSize=hop_size):
        win = windowing(frame)
        spec = spectrum(win)

        centroids.append(float(centroid(spec)))
        rolloffs.append(float(rolloff(spec)))
        flatnesses.append(float(flatness(spec)))

        sc, _ = spectral_contrast(spec)
        contrasts.append(sc)

        freqs, mags = spectral_peaks(spec)
        if len(freqs) >= 2:
            dissonances.append(float(dissonance_algo(freqs, mags)))

    # Aggregate: mean across frames
    # Centroid with range=sr/2 already returns Hz.
    # RollOff with sampleRate already returns Hz.
    mean_centroid = float(np.mean(centroids))
    mean_rolloff = float(np.mean(rolloffs))
    mean_flatness = float(np.mean(flatnesses))
    mean_dissonance = float(np.mean(dissonances)) if dissonances else 0.0

    # Spectral contrast: transpose and mean each band
    contrast_array = np.array(contrasts)
    mean_contrast = [float(v) for v in np.mean(contrast_array, axis=0)]

    # Octave bands: 4096/2048 (~93ms/~46ms) — longer window for low-frequency
    # resolution. Shared with masking via _bands._octave_band_energies (B.6).
    avg_bands = _octave_band_energies(mono, sample_rate)

    # Convert to dB
    eps = 1e-10  # log-domain floor to avoid -inf on silence
    band_db = 10 * np.log10(avg_bands + eps)

    octave_band_energy = {
        label: float(db_val) for label, db_val in zip(_BAND_LABELS, band_db)
    }

    return SpectralResult(
        spectral_centroid_hz=mean_centroid,
        spectral_rolloff_hz=mean_rolloff,
        spectral_flatness=mean_flatness,
        spectral_contrast=mean_contrast,
        dissonance=mean_dissonance,
        octave_band_energy_db=octave_band_energy,
    )
