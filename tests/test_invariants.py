"""Property-based invariant tests for the analysis modules (issue #17).

Uses hypothesis to verify algorithmic invariants that must hold for *any*
valid input, complementing the example-based tests elsewhere in the suite:

- Amplitude scaling shifts integrated LUFS by exactly 20*log10(scale).
- Mono duplicated to stereo: correlation == 1.0, width == 0, balance == 0.
- Polarity-flipped right channel: correlation == -1.0, polarity flag set.
- Time reversal leaves the magnitude spectrum (and stereo correlation)
  unchanged within measurement precision.
- A DC-offset signal is always flagged by detect_problems.
- Leading silence is excluded by EBU R128 gating, so integrated LUFS and
  true peak are unchanged.

Hypothesis profiles are registered in conftest.py: the default "ci"
profile is derandomized (deterministic, reproducible in CI); set
HYPOTHESIS_PROFILE=nightly for randomized, broader coverage.

All signals are generated in-memory (no audio files committed) and stay
well above the -80 dBFS near-silence guard.
"""

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from phantom.audio import AudioData
from phantom.loudness import analyze_loudness
from phantom.phase import analyze_phase
from phantom.problems import detect_problems
from phantom.spectral import analyze_spectrum
from phantom.stereo import analyze_stereo

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mono(samples_1d: np.ndarray, sr: int) -> AudioData:
    """Wrap a 1D mono signal into an AudioData instance."""
    samples_2d = samples_1d.reshape(-1, 1).astype(np.float32)
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=1,
        duration=len(samples_1d) / sr,
        num_samples=len(samples_1d),
    )


def _make_stereo(left: np.ndarray, right: np.ndarray, sr: int) -> AudioData:
    """Wrap two 1D channel signals into a stereo AudioData instance."""
    samples_2d = np.column_stack([left, right]).astype(np.float32)
    return AudioData(
        samples=samples_2d,
        sample_rate=sr,
        num_channels=2,
        duration=len(left) / sr,
        num_samples=len(left),
    )


def _sine(freq: float, amp: float, duration: float = 1.0, sr: int = 44100):
    """Generate a mono sine wave as a float32 array."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.float32), sr


# ---------------------------------------------------------------------------
# Loudness: amplitude scaling is exactly logarithmic
# ---------------------------------------------------------------------------


@given(scale=st.floats(min_value=0.1, max_value=0.9))
def test_loudness_scales_logarithmically(scale, sine_1khz_minus23lufs):
    """Scaling a signal by s shifts integrated LUFS by 20*log10(s)."""
    samples, sr = sine_1khz_minus23lufs
    base = analyze_loudness(_make_mono(samples, sr))
    scaled = analyze_loudness(_make_mono(samples * scale, sr))

    assert base.integrated_lufs is not None
    assert scaled.integrated_lufs is not None
    expected_delta = 20 * np.log10(scale)
    measured_delta = scaled.integrated_lufs - base.integrated_lufs
    assert abs(measured_delta - expected_delta) < 0.1


# ---------------------------------------------------------------------------
# Stereo / phase: identical channels
# ---------------------------------------------------------------------------


@given(
    freq=st.floats(min_value=50.0, max_value=8000.0),
    amp=st.floats(min_value=0.05, max_value=0.9),
)
def test_identical_channels_full_correlation(freq, amp):
    """Mono duplicated to stereo: correlation 1.0, width 0, balance 0."""
    mono, sr = _sine(freq, amp)
    audio = _make_stereo(mono, mono.copy(), sr)

    stereo = analyze_stereo(audio)
    assert stereo.correlation == 1.0
    assert stereo.stereo_width == 0.0
    assert stereo.balance_db == 0.0

    phase = analyze_phase(audio)
    assert phase.phase_correlation == 1.0
    assert phase.polarity_inverted is False


@given(
    freq=st.floats(min_value=50.0, max_value=8000.0),
    amp=st.floats(min_value=0.05, max_value=0.9),
)
def test_polarity_flip_inverts_correlation(freq, amp):
    """R = -L: correlation -1.0 and the polarity flag is set."""
    mono, sr = _sine(freq, amp)
    audio = _make_stereo(mono, -mono, sr)

    stereo = analyze_stereo(audio)
    assert stereo.correlation == -1.0

    phase = analyze_phase(audio)
    assert phase.phase_correlation == pytest.approx(-1.0, abs=1e-3)
    assert phase.polarity_inverted is True


# ---------------------------------------------------------------------------
# Time reversal: magnitude spectrum and correlation are invariant
# ---------------------------------------------------------------------------


@given(
    seed=st.integers(min_value=0, max_value=2**32 - 1),
    freq=st.floats(min_value=100.0, max_value=5000.0),
)
def test_time_reversal_preserves_spectrum(seed, freq):
    """Reversing a signal leaves octave-band energies and centroid intact.

    A 2-second signal keeps frame-boundary effects (zero-padded edge frames
    differ between forward and reversed analysis) well below the tolerance.
    """
    sr = 44100
    rng = np.random.default_rng(seed)
    tone, _ = _sine(freq, 0.4, duration=2.0, sr=sr)
    noise = (rng.standard_normal(len(tone)) * 0.1).astype(np.float32)
    signal = tone + noise

    forward = analyze_spectrum(_make_mono(signal, sr))
    reversed_ = analyze_spectrum(_make_mono(signal[::-1].copy(), sr))

    assert forward.octave_band_energy_db is not None
    assert reversed_.octave_band_energy_db is not None
    assert (
        forward.octave_band_energy_db.keys() == reversed_.octave_band_energy_db.keys()
    )
    for band, fwd_db in forward.octave_band_energy_db.items():
        rev_db = reversed_.octave_band_energy_db.get(band)
        assert abs(fwd_db - rev_db) < 1.0, f"band {band}: {fwd_db} vs {rev_db}"

    assert forward.spectral_centroid_hz is not None
    assert reversed_.spectral_centroid_hz is not None
    assert abs(forward.spectral_centroid_hz - reversed_.spectral_centroid_hz) <= (
        0.02 * forward.spectral_centroid_hz
    )


@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
def test_time_reversal_preserves_stereo_correlation(seed):
    """Pearson correlation is permutation-invariant, so reversal preserves it."""
    sr = 44100
    rng = np.random.default_rng(seed)
    left = (rng.standard_normal(sr) * 0.3).astype(np.float32)
    other = (rng.standard_normal(sr) * 0.3).astype(np.float32)
    right = (0.6 * left + 0.4 * other).astype(np.float32)

    forward = analyze_stereo(_make_stereo(left, right, sr))
    reversed_ = analyze_stereo(_make_stereo(left[::-1].copy(), right[::-1].copy(), sr))

    assert forward.correlation is not None
    assert reversed_.correlation is not None
    assert forward.correlation == pytest.approx(reversed_.correlation, abs=1e-3)


# ---------------------------------------------------------------------------
# Problem detection: DC offset is always flagged
# ---------------------------------------------------------------------------


@given(dc=st.floats(min_value=0.005, max_value=0.2))
def test_dc_offset_always_detected(dc):
    """Any DC offset well above the 5e-4 threshold is flagged."""
    mono, sr = _sine(440.0, 0.3)
    audio = _make_mono(mono + np.float32(dc), sr)

    result = detect_problems(audio)
    problem_types = [p.type for p in result.problems]
    assert "dc_offset" in problem_types


# ---------------------------------------------------------------------------
# Loudness gating: leading silence is excluded
# ---------------------------------------------------------------------------


@given(silence_s=st.floats(min_value=0.5, max_value=3.0))
def test_leading_silence_does_not_shift_integrated_lufs(
    silence_s, sine_1khz_minus23lufs
):
    """EBU R128 gating excludes silent blocks: integrated LUFS is unchanged."""
    samples, sr = sine_1khz_minus23lufs
    base = analyze_loudness(_make_mono(samples, sr))

    padded = np.concatenate([np.zeros(int(silence_s * sr), dtype=np.float32), samples])
    with_silence = analyze_loudness(_make_mono(padded, sr))

    assert base.integrated_lufs is not None
    assert with_silence.integrated_lufs is not None
    assert abs(with_silence.integrated_lufs - base.integrated_lufs) < 0.5

    assert base.true_peak_dbtp is not None
    assert with_silence.true_peak_dbtp is not None
    assert abs(with_silence.true_peak_dbtp - base.true_peak_dbtp) < 0.1
