"""Shared synthetic audio fixtures for Phantom tests.

All test audio is generated in-memory as numpy arrays.
No WAV files are committed to the repository (D-11, D-12).
"""

from pathlib import Path

import numpy as np
import pytest
import scipy.signal as _sig
import soundfile as sf


@pytest.fixture
def mono_sine_440hz():
    """1-second 440Hz sine wave, mono, 44100 Hz, float32."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    samples = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return samples, sr


@pytest.fixture
def stereo_sine_440hz():
    """1-second 440Hz sine wave, stereo (L=full amplitude, R=half amplitude), 44100 Hz, float32.

    The asymmetric channels are intentional -- used by balance/stereo tests
    that need a known L>R amplitude difference.
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    mono = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    samples = np.column_stack([mono, mono * 0.5])
    return samples, sr


@pytest.fixture
def stereo_silence():
    """1-second stereo silence, 44100 Hz, float32."""
    sr = 44100
    samples = np.zeros((sr, 2), dtype=np.float32)
    return samples, sr


@pytest.fixture
def wav_file_factory(tmp_path):
    """Factory fixture: write a numpy array to a temporary WAV file and return path."""
    _counter = [0]

    def _make(samples, sr=44100):
        _counter[0] += 1
        path = tmp_path / f"test_{_counter[0]}.wav"
        sf.write(str(path), samples, sr)
        return str(path)

    return _make


@pytest.fixture
def audio_file_factory(tmp_path):
    """Factory fixture: write a numpy array to a temporary audio file in any format."""
    _counter = [0]

    def _make(samples, sr=44100, fmt="WAV"):
        _counter[0] += 1
        ext = fmt.lower()
        if ext == "aiff":
            ext = "aif"
        path = tmp_path / f"test_{_counter[0]}.{ext}"
        sf.write(str(path), samples, sr, format=fmt)
        return str(path)

    return _make


@pytest.fixture
def multichannel_wav(tmp_path):
    """Write a 4-channel WAV file for rejection testing."""
    sr = 44100
    samples = np.zeros((sr, 4), dtype=np.float32)
    path = tmp_path / "multichannel.wav"
    sf.write(str(path), samples, sr)
    return str(path)


# -- Spectral and loudness fixtures (Phase 2) --------------------------------


@pytest.fixture
def white_noise_1s():
    """1-second white noise, mono, 44100 Hz, float32.

    Seeded RNG for reproducibility. Scaled to amplitude 0.5.
    Purpose: spectral flatness tests (flatness near 1.0 for noise).
    """
    sr = 44100
    rng = np.random.default_rng(42)
    samples = rng.standard_normal(sr).astype(np.float32)
    samples = samples * 0.5
    return samples, sr


@pytest.fixture
def multi_tone_1s():
    """1-second two-tone signal (440 Hz + 466.16 Hz), mono, 44100 Hz, float32.

    A4 and A#4 — a minor second apart, producing high dissonance.
    Purpose: dissonance testing.
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    samples = (
        0.5 * np.sin(2 * np.pi * 440 * t) + 0.5 * np.sin(2 * np.pi * 466.16 * t)
    ).astype(np.float32)
    return samples, sr


@pytest.fixture
def sine_1khz_minus23lufs():
    """5-second 1 kHz sine wave calibrated to ~-23 LUFS, mono, 48000 Hz, float32.

    5 seconds needed for EBU R128 (3s short-term window + settling).
    48 kHz sample rate for broadcast standard.
    Amplitude calibrated for EBU R128 mono measurement (signal duplicated
    to both channels per EBU Tech 3341 s5): 10^((-23 - (-3.01)) / 20).
    Purpose: EBU R128 loudness measurement validation.
    """
    sr = 48000
    t = np.linspace(0, 5.0, sr * 5, endpoint=False, dtype=np.float32)
    # With mono duplicated to both channels, the EBU R128 sum adds +3 dB.
    # Compensate: amplitude = 10^((-23 - (-3.01)) / 20) * 10^(-3.01 / 20)
    # which simplifies to 10^(-23 / 20).
    amplitude = 10 ** (-23.0 / 20)
    samples = (amplitude * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
    return samples, sr


@pytest.fixture
def near_silence():
    """1-second near-silence (~-100 dBFS), mono, 44100 Hz, float32.

    Amplitude 1e-5, 440 Hz sine carrier.
    Purpose: LOUD-05 near-silence guard testing.
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    samples = (1e-5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    return samples, sr


@pytest.fixture
def clipped_sine():
    """1-second 440 Hz sine wave clipped to [-1.0, 1.0], mono, 44100 Hz, float32.

    Generated at amplitude 1.2, then clipped via np.clip.
    Purpose: true peak detection testing (clipped signal has inter-sample peaks).
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    samples = np.clip(1.2 * np.sin(2 * np.pi * 440 * t), -1.0, 1.0).astype(np.float32)
    return samples, sr


# -- Long audio fixtures (Phase 22) ------------------------------------------


@pytest.fixture(scope="session")
def long_stereo_60s():
    """60-second stereo signal: 440Hz sine (amp 0.3) + white noise (amp 0.05).

    Left = mono, Right = mono * 0.8. Session-scoped to avoid regenerating
    2.6M samples per test. Returns (samples, sr) tuple.
    Purpose: testing duration handling, not analysis accuracy (D-17).

    Seeded RNG (seed 42) for reproducibility, matching conftest convention.
    """
    sr = 44100
    duration = 60.0
    n_samples = int(sr * duration)  # 2646000
    t = np.linspace(0, duration, n_samples, endpoint=False, dtype=np.float32)
    rng = np.random.default_rng(42)
    sine = (0.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    noise = (rng.standard_normal(n_samples).astype(np.float32) * 0.05).astype(
        np.float32
    )
    mono = sine + noise
    samples = np.column_stack([mono, mono * 0.8])
    return samples, sr


# -- Problem detection fixtures (Phase 4) -------------------------------------


@pytest.fixture
def dc_offset_sine():
    """1-second 440Hz sine at amp 0.5 + DC offset of 0.05, mono, 44100 Hz, float32.

    Purpose: DC offset detection testing (PROB-02).
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    samples = (0.5 * np.sin(2 * np.pi * 440 * t) + 0.05).astype(np.float32)
    return samples, sr


@pytest.fixture
def signal_with_hum():
    """2-second 440Hz sine at amp 0.3 + 60Hz hum at amp 0.1, mono, 44100 Hz, float32.

    Must be 2+ seconds for HumDetector's minimumDuration.
    Purpose: Hum detection testing (PROB-06).
    """
    sr = 44100
    t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
    samples = (
        0.3 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.sin(2 * np.pi * 60 * t)
    ).astype(np.float32)
    return samples, sr


@pytest.fixture
def noisy_signal():
    """2-second signal with loud and quiet sections + high noise floor, mono, 44100 Hz, float32.

    First second: 440Hz sine at amp 0.5 (loud passage).
    Second second: white noise only at amp 0.05 (quiet passage with audible noise).
    Seeded RNG (seed 99) for reproducibility. The quiet section's noise floor is
    above -50 dBFS in block-RMS analysis, triggering noise floor detection.
    Purpose: Noise floor (PROB-04) and SNR (PROB-05) testing.
    """
    sr = 44100
    rng = np.random.default_rng(99)
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    # Loud section: 440Hz sine
    loud = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    # Quiet section: noise only (simulates a quiet passage with audible background noise)
    quiet_noise = (rng.standard_normal(sr).astype(np.float32) * 0.05).astype(np.float32)
    samples = np.concatenate([loud, quiet_noise])
    return samples, sr


# -- Frequency-domain problem detection fixtures (Phase 4, Plan 02) ----------


@pytest.fixture
def sibilant_signal():
    """2-second signal with excessive 5-10kHz energy, mono, 44100 Hz, float32.

    White noise (amp 0.1) + boosted 7kHz sine (amp 0.4).
    Purpose: Sibilance detection testing (PROB-07).
    """
    sr = 44100
    rng = np.random.default_rng(101)
    t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
    noise = rng.standard_normal(sr * 2).astype(np.float32) * 0.1
    sibilance = (0.4 * np.sin(2 * np.pi * 7000 * t)).astype(np.float32)
    samples = noise + sibilance
    return samples, sr


@pytest.fixture
def muddy_signal():
    """2-second signal with excessive 200-500Hz energy, mono, 44100 Hz, float32.

    White noise (amp 0.1) + strong 300Hz sine (amp 0.5).
    Purpose: Mud detection testing (PROB-08).
    """
    sr = 44100
    rng = np.random.default_rng(102)
    t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
    noise = rng.standard_normal(sr * 2).astype(np.float32) * 0.1
    mud = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    samples = noise + mud
    return samples, sr


@pytest.fixture
def harsh_signal():
    """2-second signal with excessive 2-4kHz energy, mono, 44100 Hz, float32.

    White noise (amp 0.1) + boosted 3kHz sine (amp 0.4).
    Purpose: Harshness detection testing (PROB-09).
    """
    sr = 44100
    rng = np.random.default_rng(103)
    t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
    noise = rng.standard_normal(sr * 2).astype(np.float32) * 0.1
    harshness = (0.4 * np.sin(2 * np.pi * 3000 * t)).astype(np.float32)
    samples = noise + harshness
    return samples, sr


@pytest.fixture
def resonant_signal():
    """2-second signal with narrow resonant peak at 120Hz, mono, 44100 Hz, float32.

    White noise (amp 0.05) + narrow 120Hz sine (amp 0.6).
    Purpose: Resonant peak detection testing (PROB-10).
    """
    sr = 44100
    rng = np.random.default_rng(104)
    t = np.linspace(0, 2.0, sr * 2, endpoint=False, dtype=np.float32)
    noise = rng.standard_normal(sr * 2).astype(np.float32) * 0.05
    resonance = (0.6 * np.sin(2 * np.pi * 120 * t)).astype(np.float32)
    samples = noise + resonance
    return samples, sr


@pytest.fixture
def lossy_sim_signal():
    """2-second lowpassed noise simulating lossy codec shelf, mono, 44100 Hz, float32.

    White noise (amp 0.3) with steep 12th-order lowpass at 15kHz.
    Simulates ~128kbps MP3 spectral shelf (energy drops sharply above 15kHz).
    Purpose: Lossy codec detection testing (PROB-13).
    """
    sr = 44100
    rng = np.random.default_rng(105)
    noise = rng.standard_normal(sr * 2).astype(np.float32) * 0.3
    sos = _sig.butter(12, 15000 / (sr / 2), btype="low", output="sos")
    samples = _sig.sosfilt(sos, noise).astype(np.float32)
    return samples, sr


# -- Frequency masking fixtures (Phase 5) ----------------------------------------


@pytest.fixture
def overlapping_stems_raw():
    """Two 1-second sines at 300 Hz and 350 Hz for masking tests.

    Returns (samples_a, samples_b, sr) tuple. Both signals fall in the
    250_hz octave band. Amplitude 0.5, float32, sr=44100.
    Purpose: reusable raw stem data for masking analysis tests.
    """
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    samples_a = (0.5 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    samples_b = (0.5 * np.sin(2 * np.pi * 350 * t)).astype(np.float32)
    return samples_a, samples_b, sr


# -- Reference comparison fixtures (Phase 7) ----------------------------------


@pytest.fixture
def comparison_stereo_audio():
    """3-second 440Hz stereo sine wave at 0.5 amplitude, 44100 Hz, float32.

    Both channels identical (mono-compatible stereo).
    Purpose: Reference comparison integration testing.
    """
    sr = 44100
    t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
    mono = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    samples = np.column_stack([mono, mono])
    return samples, sr


@pytest.fixture
def comparison_profile():
    """A ReferenceProfile with known values for comparison testing.

    - lufs_range: (-14.0, -8.0)
    - crest_factor_range: (6.0, 12.0)
    - true_peak_max_dbtp: -1.0
    - bands: all 0.0 (flat target)
    - width: "moderate"
    - mono_below_hz: 120.0

    Purpose: Reference comparison integration testing.
    """
    from phantom._profiles import (
        FrequencyTargets,
        LoudnessTargets,
        ReferenceProfile,
        SpatialConventions,
        StereoConventions,
    )

    return ReferenceProfile(
        genre="test",
        description="Test profile for comparison tests",
        loudness=LoudnessTargets(
            lufs_range=(-14.0, -8.0),
            crest_factor_range=(6.0, 12.0),
            true_peak_max_dbtp=-1.0,
        ),
        frequency=FrequencyTargets(
            bands={
                "31_hz": 0.0,
                "62_hz": 0.0,
                "125_hz": 0.0,
                "250_hz": 0.0,
                "500_hz": 0.0,
                "1000_hz": 0.0,
                "2000_hz": 0.0,
                "4000_hz": 0.0,
                "8000_hz": 0.0,
                "16000_hz": 0.0,
            }
        ),
        stereo=StereoConventions(width="moderate", mono_below_hz=120.0),
        spatial=SpatialConventions(
            reverb_type="room", reverb_amount="moderate", pre_delay_ms="medium"
        ),
        processing_notes="Test profile.",
    )


# -- Live integration test fixtures (Phase 12.1) --------------------------------

LIVE_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "live"
LIVE_MIX = LIVE_FIXTURES_DIR / "mix.wav"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: requires real audio in tests/fixtures/live/"
    )
    config.addinivalue_line("markers", "slow: long-running tests (60s+ audio fixtures)")


def pytest_collection_modifyitems(config, items):
    if not LIVE_MIX.exists():
        skip_live = pytest.mark.skip(
            reason="Live audio fixtures not present in tests/fixtures/live/"
        )
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


@pytest.fixture
def live_mix():
    """Path to the real mix WAV file."""
    return str(LIVE_MIX)


@pytest.fixture
def live_stems():
    """Dict mapping stem name to path for all available stem WAV files.

    Discovers stems dynamically via glob pattern stem-*.wav.
    Keys are stem names (e.g., 'vocals', 'drums', 'bass').
    """
    stems = {}
    for f in LIVE_FIXTURES_DIR.glob("stem-*.wav"):
        name = f.stem.replace("stem-", "")
        stems[name] = str(f)
    return stems


@pytest.fixture
def live_stem_paths(live_stems):
    """List of all live stem file paths (for batch/masking tools)."""
    return list(live_stems.values())
