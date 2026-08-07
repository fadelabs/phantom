"""Octave-band energy primitive shared by spectral and masking analysis (B.6).

``analyze_spectrum`` converts the per-band linear energies to dB for its
``octave_band_energy_db`` field; ``masking`` consumes the linear energies
directly for its overlap scoring. The 4096/2048 Hann + Essentia
``FrequencyBands`` loop lives here so both consumers share one
implementation (P-09), instead of masking reaching into ``spectral`` for
an underscore-prefixed helper.
"""

from __future__ import annotations

import numpy as np
import essentia.standard as es

from phantom._settings import AnalysisSettings

# Standard octave band center frequencies (Hz).
OCTAVE_CENTERS = [31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]

# Band edge frequencies for octave band analysis.
# Lower edge = center / sqrt(2), upper edge = center * sqrt(2).
_SQRT2 = np.sqrt(2)
OCTAVE_EDGES = [OCTAVE_CENTERS[0] / _SQRT2] + [c * _SQRT2 for c in OCTAVE_CENTERS]

# Band label keys for the output dict.
_BAND_LABELS = [f"{int(c)}_hz" if c >= 1 else f"{c}_hz" for c in OCTAVE_CENTERS]


def _octave_band_energies(
    mono: np.ndarray, sample_rate: int, settings: AnalysisSettings
) -> np.ndarray:
    """Average linear energy per octave band via Essentia FrequencyBands (P-09).

    Runs a Hann-windowed FrequencyBands loop over ``OCTAVE_EDGES`` and
    averages the per-frame band energies across all frames. Shared by
    ``spectral.analyze_spectrum`` (which converts the result to dB) and
    ``masking`` (which consumes the linear energies directly) so the identical
    loop is not duplicated.

    Frame/hop sizes are AnalysisSettings-tunable (C.1); defaults 4096/2048
    reproduce the original pass exactly.

    Args:
        mono: 1D float32 numpy array of audio samples.
        sample_rate: Sample rate in Hz.
        settings: Effective analysis settings (the requiring caller resolves
            them).

    Returns:
        1D numpy array of shape ``(len(OCTAVE_CENTERS),)`` with the average
        linear energy per octave band. Returns all-zeros when the signal is
        shorter than one frame (insufficient data to resolve any band -- the
        acoustically correct answer).
    """
    frame_size = settings.octave_frame_size
    hop_size = settings.octave_hop_size

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
