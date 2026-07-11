"""Fixtures for phantom-audio-separation tests.

Mirrors the root test suite's conventions: synthetic in-memory audio only,
writes confined to each test's tmp_path.
"""

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture(autouse=True)
def _confine_writes_to_tmp(tmp_path, monkeypatch):
    """Confine writes to each test's tmp_path by default.

    Phantom confines all file writes to PHANTOM_OUTPUT_DIR (default
    ~/.phantom/output). Point it at the per-test tmp_path so write-path
    tests keep their outputs inside the sandbox.
    """
    monkeypatch.setenv("PHANTOM_OUTPUT_DIR", str(tmp_path))


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
def stereo_sine_input(wav_file_factory):
    """A 1-second stereo 440 Hz sine WAV file path."""
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    samples = np.column_stack(
        [
            0.5 * np.sin(2 * np.pi * 440 * t),
            0.5 * np.sin(2 * np.pi * 440 * t),
        ]
    ).astype(np.float32)
    return wav_file_factory(samples, sr)
