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
from functools import cached_property
from typing import Optional

import numpy as np
import soundfile as sf
from pydantic import BaseModel, ConfigDict, model_validator

from phantom.exceptions import AnalysisError, AudioLoadError
from phantom._utils import (
    SILENCE_THRESHOLD_DB,
    _block_rms_db,
    check_decoded_size,
    check_duration_size,
    open_validated_input,
    validate_input_path,
)

# Sample rate bounds for supported audio files (SC-9)
MIN_SAMPLE_RATE = 8000  # 8 kHz -- telephone quality floor
MAX_SAMPLE_RATE = 384000  # 384 kHz -- DSD/high-res ceiling

# Magnitude ceiling for sample values. essentia's float32 accumulators
# overflow when squared samples approach float32 max, which makes
# HumDetector hang exactly like NaN input; a probe verified that 1e17
# amplitude completes while 1e19+ spins forever, so the hang onset sits
# near |x| ~ 1e18. The 1e15 ceiling sits well below that onset and is
# astronomically beyond any real audio (digital full scale is 1.0).
MAX_ANALYZABLE_AMPLITUDE = 1e15

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
        """Validate that samples array shape matches declared metadata.

        Raises:
            AnalysisError: If the samples shape contradicts the declared
                metadata. PhantomError (not a bare ValueError, B.9) so callers
                without the analyzer @wrap_errors decorator still surface a
                type they can catch; the message is unchanged.
        """
        if self.samples.ndim != 2:
            raise AnalysisError(
                f"samples must be a 2D array [num_samples, num_channels], "
                f"got {self.samples.ndim}D array with shape {self.samples.shape}"
            )
        if self.samples.shape[1] != self.num_channels:
            raise AnalysisError(
                f"samples has {self.samples.shape[1]} columns but "
                f"num_channels is {self.num_channels}"
            )
        # The analyzers assume finite samples within a representable
        # magnitude: NaN/Inf corrupt every measurement, and magnitude
        # overflow in essentia's float32 accumulators hangs HumDetector in
        # an uninterruptible C++ loop (same failure as NaN input), so both
        # are rejected at the model boundary (load_audio issues load-specific
        # errors before constructing this model).
        if not np.isfinite(self.samples).all():
            raise AnalysisError(
                "samples must contain only finite values (no NaN or Infinity)"
            )
        peak = float(np.max(np.abs(self.samples))) if self.samples.size else 0.0
        if peak > MAX_ANALYZABLE_AMPLITUDE:
            raise AnalysisError(
                "samples must not exceed the supported magnitude range "
                f"(peak {peak:.3g} > {MAX_ANALYZABLE_AMPLITUDE:.3g}, far beyond "
                "digital full scale)"
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

    @cached_property
    def mono(self) -> np.ndarray:
        """Return a (memoized) mono mixdown of the audio.

        For mono input, returns samples[:, 0]. For stereo, the mean of the
        first two channels. Computed once per instance (P-03).
        """
        if self.num_channels == 1:
            return self.samples[:, 0]
        return np.mean(self.samples[:, :2], axis=1)

    @cached_property
    def mono_rms(self) -> float:
        """Full-signal RMS of the mono mixdown, computed once (P-04)."""
        m = self.mono
        if not np.issubdtype(m.dtype, np.floating):
            m = m.astype(np.float64)
        return float(np.sqrt(np.mean(m**2)))

    @cached_property
    def block_rms_db(self) -> list[float]:
        """Per-block RMS of the mono mixdown in dBFS, computed once (A.2).

        Delegates to the shared array helper; memoized so the block loop that
        previously ran separately in ``detect_problems`` (noise floor + SNR)
        and ``analyze_dynamics`` (dynamic range) runs at most once per
        instance.
        """
        return _block_rms_db(self.mono)

    @cached_property
    def is_near_silent(self) -> bool:
        """Whether the mono mixdown falls below SILENCE_THRESHOLD_DB (A.7).

        Same predicate as the module-level ``is_near_silent(audio.mono)``
        helper, evaluated off the memoized :attr:`mono_rms` so the two never
        pay separate whole-signal passes (review F4). The stereo/phase paths
        that must check individual channels (an out-of-phase pair cancels in
        the mono mixdown but both channels carry energy) still call the array
        helper directly.

        Like ``mono``/``mono_rms``, this is a ``cached_property``: samples are
        treated as immutable after construction (the same invariant
        ``_cache.py`` relies on for ``_content_hash``), so the memo is never
        invalidated and would go stale if samples were mutated in place.
        """
        rms = self.mono_rms
        if rms == 0:
            return True  # guards np.log10(0) -- the helper's early return
        return bool(20.0 * np.log10(rms) < SILENCE_THRESHOLD_DB)


def load_audio(
    path: str,
    max_duration: float | None = None,
    max_file_size: int | None = None,
    max_decoded_bytes: int | None = None,
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
        max_decoded_bytes: Maximum decoded float32 footprint in bytes (frames
            x channels x 4). Precedence: this parameter >
            PHANTOM_MAX_DECODED_BYTES env var > 1_000_000_000 default.

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

    # Step 2: Open the validated path ONCE and hold the descriptor. When input
    # confinement is active this uses O_NOFOLLOW and reads every byte via this
    # fd, closing the validate-then-reopen symlink TOCTOU (Finding 4).
    fd = open_validated_input(path)
    try:
        try:
            snd = sf.SoundFile(fd, mode="r", closefd=False)
        except Exception as exc:
            raise AudioLoadError(
                f"Cannot read audio file: {os.path.basename(path)}"
            ) from exc

        with snd:
            # Step 2.5: Sample rate validation (SC-9)
            if snd.samplerate < MIN_SAMPLE_RATE or snd.samplerate > MAX_SAMPLE_RATE:
                raise AudioLoadError(
                    f"Sample rate {snd.samplerate} Hz is outside the supported range "
                    f"({MIN_SAMPLE_RATE}-{MAX_SAMPLE_RATE} Hz). "
                    f"Check the file format."
                )

            # Steps 3 & 4: Duration + file-size guards (SEC-03, D-05, D-06, D-08).
            # Size comes from the held fd (fstat), not a second path lookup.
            duration_s = snd.frames / snd.samplerate if snd.samplerate else 0.0
            check_duration_size(
                duration_s,
                os.fstat(fd).st_size,
                max_duration=max_duration,
                max_file_size=max_file_size,
            )

            # Step 4.5: Decoded-size guard (AUD-03). The duration/size caps
            # still permit multi-GB decodes (900 s x 384 kHz x stereo x
            # float32 ~= 2.8 GB), so the decoded footprint is capped here,
            # before any read.
            check_decoded_size(
                snd.frames, snd.channels, max_decoded_bytes=max_decoded_bytes
            )

            # Step 5: Channel count check (existing)
            if snd.channels > 2:
                raise AudioLoadError(
                    f"Cannot load {snd.channels}-channel audio file. "
                    f"Phantom supports mono and stereo only."
                )

            # Step 6: Load audio as float32 via the held descriptor
            data = snd.read(dtype="float32", always_2d=True)
            sample_rate = snd.samplerate

            # Step 6.5: Finite-sample and magnitude guard (AUD-01/02).
            # Float-format files can carry NaN/Inf samples, and float32
            # values near the format's ceiling overflow essentia's internal
            # accumulators — both hang HumDetector and corrupt measurements,
            # so such files are rejected here with a load-specific error (the
            # AudioData validator below raises AnalysisError, which would
            # surface as a generic analysis failure instead).
            if not np.isfinite(data).all():
                raise AudioLoadError(
                    "Audio file contains non-finite samples (NaN or Infinity). "
                    "The file may be corrupt — re-export it from its source "
                    "application."
                )
            peak = float(np.max(np.abs(data))) if data.size else 0.0
            if peak > MAX_ANALYZABLE_AMPLITUDE:
                raise AudioLoadError(
                    "Audio file contains samples with magnitude far beyond "
                    f"digital full scale (peak {peak:.3g}). Normalize the "
                    "file's level and re-export it."
                )
    finally:
        os.close(fd)

    return AudioData(
        samples=data,
        sample_rate=sample_rate,
        num_channels=data.shape[1],
        duration=len(data) / sample_rate,
        num_samples=len(data),
        file_path=path,
    )
