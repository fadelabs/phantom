"""Audio data model and loading function.

Provides the AudioData Pydantic model (the universal audio type for Phantom)
and the load_audio() function for reading audio files from disk.

AudioData normalizes all audio to float32 samples in a 2D array [N, channels]
and provides .left, .right, and .mono channel-access properties.

Supports all formats handled by libsndfile: WAV, FLAC, AIFF, OGG, and more.
Mono and stereo only (>2 channels rejected per AIO-03).
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import soundfile as sf
from pydantic import BaseModel, ConfigDict, model_validator

from phantom.exceptions import AudioLoadError
from phantom._utils import validate_input_path

# Sample rate bounds for supported audio files (SC-9)
MIN_SAMPLE_RATE = 8000  # 8 kHz -- telephone quality floor
MAX_SAMPLE_RATE = 384000  # 384 kHz -- DSD/high-res ceiling

# Formats that users commonly attempt but libsndfile cannot read
_UNSUPPORTED_EXTENSIONS = {".mp3", ".aac", ".m4a", ".wma"}


class AudioData(BaseModel):
    """Pydantic model holding audio samples and metadata.

    Samples are stored as a 2D float32 numpy array with shape [num_samples, num_channels].
    Channel access is provided via .left, .right, and .mono properties.

    Attributes:
        samples: Audio sample data as float32 array, shape [num_samples, num_channels].
        sample_rate: Sample rate in Hz (e.g. 44100, 48000, 96000).
        num_channels: Number of audio channels (1 for mono, 2 for stereo).
        duration: Duration in seconds.
        num_samples: Number of sample frames.
        file_path: Source file path if loaded from disk, None if created in-memory.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    samples: np.ndarray
    sample_rate: int
    num_channels: int
    duration: float
    num_samples: int
    file_path: Optional[str] = None

    @model_validator(mode="after")
    def _validate_samples(self) -> "AudioData":
        """Validate that samples array shape matches declared metadata."""
        if self.samples.ndim != 2:
            raise ValueError(
                f"samples must be a 2D array [num_samples, num_channels], "
                f"got {self.samples.ndim}D array with shape {self.samples.shape}"
            )
        if self.samples.shape[1] != self.num_channels:
            raise ValueError(
                f"samples has {self.samples.shape[1]} columns but "
                f"num_channels is {self.num_channels}"
            )
        return self

    @property
    def left(self) -> np.ndarray:
        """Return the left channel (channel 0) for both mono and stereo."""
        return self.samples[:, 0]

    @property
    def right(self) -> np.ndarray:
        """Return the right channel (channel 1) for stereo audio.

        Raises:
            AudioLoadError: If the audio is mono (only 1 channel).
        """
        if self.num_channels < 2:
            raise AudioLoadError(
                "Cannot access right channel on a mono file. "
                "Use .left or .mono instead."
            )
        return self.samples[:, 1]

    @property
    def mono(self) -> np.ndarray:
        """Return a mono mixdown of the audio.

        For mono input, returns samples[:, 0] directly.
        For stereo input, returns the mean of left and right channels.
        """
        if self.num_channels == 1:
            return self.samples[:, 0]
        return np.mean(self.samples[:, :2], axis=1)


def load_audio(
    path: str,
    max_duration: float | None = None,
    max_file_size: int | None = None,
) -> AudioData:
    """Load an audio file and return an AudioData instance.

    Reads the file as float32 samples normalized to [-1.0, 1.0].
    Supports all formats handled by libsndfile (WAV, FLAC, AIFF, OGG, etc.).
    Only mono and stereo files are supported; files with more than
    2 channels are rejected with an AudioLoadError.

    Args:
        path: Path to an audio file on disk.
        max_duration: Maximum allowed duration in seconds. Precedence:
            this parameter > PHANTOM_MAX_DURATION env var > 900s default.
        max_file_size: Maximum allowed file size in bytes. Precedence:
            this parameter > PHANTOM_MAX_FILE_SIZE env var > 500_000_000 default.

    Returns:
        AudioData with the loaded samples and metadata.

    Raises:
        PathSecurityError: If path is outside PHANTOM_AUDIO_DIR (when set).
        AudioLoadError: If the file cannot be read, exceeds duration/size
            limits, or has >2 channels.
    """
    # Step 1: Path validation (SEC-01, D-04)
    path = validate_input_path(path)

    # Step 1.5: Unsupported format detection — check extension before sf.info
    ext = os.path.splitext(path)[1].lower()
    if ext in _UNSUPPORTED_EXTENSIONS:
        fmt_name = ext.lstrip(".").upper()
        raise AudioLoadError(
            f"{fmt_name} format is not supported. Convert to WAV first:\n"
            f"  phantom render {os.path.basename(path)} --format wav"
        )

    # Step 2: Read header -- validates existence and readability (existing)
    try:
        info = sf.info(path)
    except Exception as exc:
        raise AudioLoadError(
            f"Cannot read audio file: {os.path.basename(path)}"
        ) from exc

    # Step 2.5: Sample rate validation (SC-9)
    if info.samplerate < MIN_SAMPLE_RATE or info.samplerate > MAX_SAMPLE_RATE:
        raise AudioLoadError(
            f"Sample rate {info.samplerate} Hz is outside the supported range "
            f"({MIN_SAMPLE_RATE}-{MAX_SAMPLE_RATE} Hz). "
            f"Check the file format."
        )

    # Step 3: Duration guard (SEC-03, D-05, D-06)
    effective_max_duration = max_duration
    if effective_max_duration is None:
        env_val = os.environ.get("PHANTOM_MAX_DURATION")
        if env_val is not None and env_val.strip():
            try:
                effective_max_duration = float(env_val)
            except ValueError:
                raise AudioLoadError(
                    f"PHANTOM_MAX_DURATION must be a number (seconds), got: '{env_val}'"
                )
        else:
            effective_max_duration = 900.0  # 15 minutes default
    if effective_max_duration <= 0:
        raise AudioLoadError(
            f"max_duration must be a positive number, got {effective_max_duration}. "
            f"Check PHANTOM_MAX_DURATION env var or max_duration parameter."
        )
    if info.duration > effective_max_duration:
        mins = info.duration / 60
        limit_mins = effective_max_duration / 60
        raise AudioLoadError(
            f"Audio file is {mins:.1f} minutes ({info.duration:.0f}s), "
            f"which exceeds the {limit_mins:.0f}-minute limit "
            f"({effective_max_duration:.0f}s). "
            f"Set PHANTOM_MAX_DURATION to increase the limit, "
            f"or trim the file."
        )

    # Step 4: File size guard (D-08)
    effective_max_size = max_file_size
    if effective_max_size is None:
        env_val = os.environ.get("PHANTOM_MAX_FILE_SIZE")
        if env_val is not None and env_val.strip():
            try:
                effective_max_size = int(env_val)
            except ValueError:
                raise AudioLoadError(
                    f"PHANTOM_MAX_FILE_SIZE must be an integer (bytes), got: '{env_val}'"
                )
        else:
            effective_max_size = 500_000_000  # 500 MB default
    if effective_max_size <= 0:
        raise AudioLoadError(
            f"max_file_size must be a positive number, got {effective_max_size}. "
            f"Check PHANTOM_MAX_FILE_SIZE env var or max_file_size parameter."
        )
    actual_size = os.path.getsize(path)
    if actual_size > effective_max_size:
        raise AudioLoadError(
            f"Audio file is {actual_size / 1_000_000:.1f} MB, "
            f"which exceeds the {effective_max_size / 1_000_000:.0f} MB limit. "
            f"Set PHANTOM_MAX_FILE_SIZE to increase the limit."
        )

    # Step 5: Channel count check (existing)
    if info.channels > 2:
        raise AudioLoadError(
            f"Cannot load {info.channels}-channel audio file. "
            f"Phantom supports mono and stereo only."
        )

    # Step 6: Load audio as float32 (existing)
    data, sample_rate = sf.read(path, dtype="float32", always_2d=True)

    return AudioData(
        samples=data,
        sample_rate=sample_rate,
        num_channels=data.shape[1],
        duration=len(data) / sample_rate,
        num_samples=len(data),
        file_path=path,
    )
