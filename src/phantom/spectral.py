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
from pydantic import BaseModel, field_validator

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom._rounding import round_db_dict, round_hz, round_ratio, round_ratio_list
from phantom._utils import wrap_errors

# Standard octave band center frequencies (Hz).
OCTAVE_CENTERS = [31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

# Band edge frequencies for octave band analysis.
# Lower edge = center / sqrt(2), upper edge = center * sqrt(2).
_SQRT2 = np.sqrt(2)
OCTAVE_EDGES = [OCTAVE_CENTERS[0] / _SQRT2] + [c * _SQRT2 for c in OCTAVE_CENTERS]

# Band label keys for the output dict.
_BAND_LABELS = [f"{int(c)}_hz" if c >= 1 else f"{c}_hz" for c in OCTAVE_CENTERS]


def _octave_band_energies(mono: np.ndarray, sample_rate: int) -> np.ndarray:
    """Average linear energy per octave band via Essentia FrequencyBands (P-09).

    Runs a 4096/2048 Hann-windowed FrequencyBands loop over ``OCTAVE_EDGES``
    and averages the per-frame band energies across all frames. Shared by both
    ``analyze_spectrum`` (which converts the result to dB) and
    ``masking._compute_band_energies`` (which consumes the linear energies
    directly) so the identical loop is not duplicated.

    Args:
        mono: 1D float32 numpy array of audio samples.
        sample_rate: Sample rate in Hz.

    Returns:
        1D numpy array of shape ``(len(OCTAVE_CENTERS),)`` with the average
        linear energy per octave band. Returns all-zeros when the signal is
        shorter than one 4096-sample frame (insufficient data to resolve any
        band — the acoustically correct answer).
    """
    frame_size = 4096
    hop_size = 2048

    # Audio shorter than one FFT frame cannot produce meaningful band energies.
    if len(mono) < frame_size:
        return np.zeros(len(OCTAVE_CENTERS))

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
        return np.zeros(len(OCTAVE_CENTERS))

    return np.mean(band_energies_list, axis=0)


class SpectralResult(BaseModel):
    """Result of spectral analysis."""

    spectral_centroid_hz: Optional[float] = None
    spectral_rolloff_hz: Optional[float] = None
    spectral_flatness: Optional[float] = None
    spectral_contrast: Optional[list[float]] = None
    dissonance: Optional[float] = None
    octave_band_energy_db: Optional[dict[str, float]] = None

    @field_validator("spectral_centroid_hz", "spectral_rolloff_hz", mode="before")
    @classmethod
    def _round_hz(cls, v: float | None) -> float | None:
        return round_hz(v)

    @field_validator("spectral_flatness", "dissonance", mode="before")
    @classmethod
    def _round_ratio(cls, v: float | None) -> float | None:
        return round_ratio(v)

    @field_validator("spectral_contrast", mode="before")
    @classmethod
    def _round_contrast(cls, v: list[float] | None) -> list[float] | None:
        return round_ratio_list(v)

    @field_validator("octave_band_energy_db", mode="before")
    @classmethod
    def _round_band_db(cls, v: dict[str, float] | None) -> dict[str, float] | None:
        return round_db_dict(v)


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
    mono = audio.mono
    sample_rate = audio.sample_rate

    # Empty-samples guard
    if len(mono) == 0:
        raise AnalysisError("Spectral analysis failed: audio has 0 samples")

    # Near-silence guard (memoized on AudioData, A.7)
    if audio.is_near_silent:
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
    # resolution. Shared with masking via _octave_band_energies (P-09).
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
