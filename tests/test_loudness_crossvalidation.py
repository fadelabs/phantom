"""Cross-validate Phantom loudness measurements against pyloudnorm.

Verifies that Phantom's EBU R128 integrated LUFS agrees with pyloudnorm
(a reference implementation) within +-0.5 LU across a panel of synthetic
signals at varying loudness levels.
"""

from __future__ import annotations

import numpy as np
import pytest

try:
    import pyloudnorm as pyln

    HAS_PYLOUDNORM = True
except ImportError:
    HAS_PYLOUDNORM = False

from phantom.audio import AudioData
from phantom.loudness import analyze_loudness

pytestmark = pytest.mark.skipif(not HAS_PYLOUDNORM, reason="pyloudnorm not installed")

TOLERANCE_LU = 0.5


def _make_audio(samples: np.ndarray, sr: int) -> AudioData:
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    return AudioData(
        samples=samples,
        sample_rate=sr,
        num_channels=samples.shape[1],
        duration=len(samples) / sr,
        num_samples=len(samples),
    )


def _pyln_lufs(samples: np.ndarray, sr: int) -> float:
    meter = pyln.Meter(sr)
    if samples.ndim == 1:
        # Match Phantom's behavior: duplicate mono to stereo per EBU Tech 3341 s5
        samples = np.column_stack([samples, samples])
    return meter.integrated_loudness(samples)


class TestIntegratedLUFS:
    """Cross-validate integrated LUFS between Phantom and pyloudnorm."""

    @pytest.mark.parametrize(
        "amplitude,description",
        [
            (0.5, "moderate level sine"),
            (0.1, "quiet sine"),
            (0.01, "very quiet sine"),
            (0.9, "loud sine"),
        ],
    )
    def test_sine_at_varying_levels(self, amplitude, description):
        """Mono 1kHz sine at different amplitudes."""
        sr = 48000
        duration = 5.0
        t = np.linspace(
            0, duration, int(sr * duration), endpoint=False, dtype=np.float32
        )
        samples = (amplitude * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)

        phantom_lufs = analyze_loudness(_make_audio(samples, sr)).integrated_lufs
        reference_lufs = _pyln_lufs(samples, sr)

        assert phantom_lufs == pytest.approx(reference_lufs, abs=TOLERANCE_LU), (
            f"{description}: phantom={phantom_lufs:.2f}, pyloudnorm={reference_lufs:.2f}"
        )

    def test_stereo_sine(self):
        """Stereo 1kHz sine with different channel levels."""
        sr = 48000
        duration = 5.0
        t = np.linspace(
            0, duration, int(sr * duration), endpoint=False, dtype=np.float32
        )
        left = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        right = (0.3 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        samples = np.column_stack([left, right])

        phantom_lufs = analyze_loudness(_make_audio(samples, sr)).integrated_lufs
        reference_lufs = _pyln_lufs(samples, sr)

        assert phantom_lufs == pytest.approx(reference_lufs, abs=TOLERANCE_LU)

    def test_pink_noise(self):
        """Pink-ish noise (filtered white noise)."""
        import scipy.signal as sig

        sr = 48000
        duration = 5.0
        rng = np.random.default_rng(42)
        white = rng.standard_normal(int(sr * duration)).astype(np.float32) * 0.3
        # Simple pink approximation: -3dB/octave slope via first-order filter
        b, a = sig.butter(1, 1000 / (sr / 2), btype="low")
        pink = sig.lfilter(b, a, white).astype(np.float32)

        phantom_lufs = analyze_loudness(_make_audio(pink, sr)).integrated_lufs
        reference_lufs = _pyln_lufs(pink, sr)

        assert phantom_lufs == pytest.approx(reference_lufs, abs=TOLERANCE_LU)

    def test_chord(self):
        """A minor chord — multiple frequencies summed."""
        sr = 48000
        duration = 5.0
        t = np.linspace(
            0, duration, int(sr * duration), endpoint=False, dtype=np.float32
        )
        chord = (
            0.2 * np.sin(2 * np.pi * 220 * t)
            + 0.15 * np.sin(2 * np.pi * 261.63 * t)
            + 0.15 * np.sin(2 * np.pi * 329.63 * t)
        ).astype(np.float32)

        phantom_lufs = analyze_loudness(_make_audio(chord, sr)).integrated_lufs
        reference_lufs = _pyln_lufs(chord, sr)

        assert phantom_lufs == pytest.approx(reference_lufs, abs=TOLERANCE_LU)

    def test_envelope_burst(self):
        """Sine with fade-in/fade-out envelope — tests gating behavior."""
        sr = 48000
        duration = 5.0
        t = np.linspace(
            0, duration, int(sr * duration), endpoint=False, dtype=np.float32
        )
        sine = (0.5 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        envelope = np.clip(np.minimum(t / 0.5, (duration - t) / 0.5), 0, 1).astype(
            np.float32
        )
        samples = sine * envelope

        phantom_lufs = analyze_loudness(_make_audio(samples, sr)).integrated_lufs
        reference_lufs = _pyln_lufs(samples, sr)

        assert phantom_lufs == pytest.approx(reference_lufs, abs=TOLERANCE_LU)

    def test_44100_sample_rate(self):
        """Verify agreement at 44.1kHz (most common for music)."""
        sr = 44100
        duration = 5.0
        t = np.linspace(
            0, duration, int(sr * duration), endpoint=False, dtype=np.float32
        )
        samples = (0.4 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

        phantom_lufs = analyze_loudness(_make_audio(samples, sr)).integrated_lufs
        reference_lufs = _pyln_lufs(samples, sr)

        assert phantom_lufs == pytest.approx(reference_lufs, abs=TOLERANCE_LU)
