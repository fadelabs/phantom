"""Shared utility functions for Phantom analysis modules."""

from __future__ import annotations

import functools
import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from phantom.exceptions import (
    AnalysisError,
    AudioLoadError,
    PathSecurityError,
    PhantomError,
)

if TYPE_CHECKING:
    from phantom.audio import AudioData

# Silence threshold in dBFS -- signals below this are treated as silence.
SILENCE_THRESHOLD_DB = -80.0

# Decode-safety defaults (shared by load_audio and separate_stems).
DEFAULT_MAX_DURATION = 900.0  # 15 minutes
DEFAULT_MAX_FILE_SIZE = 500_000_000  # 500 MB


def enforce_decode_limits(
    path: str,
    *,
    info=None,
    max_duration: float | None = None,
    max_file_size: int | None = None,
):
    """Reject over-long or oversized audio before it is decoded (SEC-03).

    Reads only the file header via ``sf.info`` (no full decode) and enforces
    duration and file-size caps. Mirrored from ``load_audio`` so paths that
    feed decoders directly -- e.g. demucs in ``separate_stems`` -- get the same
    decompression-bomb / unbounded-decode protection (Advisory 2). A small,
    highly compressed FLAC/OGG can otherwise expand to multi-gigabyte PCM, and
    this also bounds exposure to decoder bugs such as libsndfile CVE-2026-37555.

    Args:
        path: Path to an audio file (already path-validated by the caller).
        info: Pre-read ``sf.info`` result to avoid a second header read; read
            internally when None.
        max_duration: Override for the duration cap (seconds). Precedence:
            param > PHANTOM_MAX_DURATION > DEFAULT_MAX_DURATION.
        max_file_size: Override for the size cap (bytes). Precedence:
            param > PHANTOM_MAX_FILE_SIZE > DEFAULT_MAX_FILE_SIZE.

    Returns:
        The ``sf.info`` result (read here or passed in), so callers can reuse it.

    Raises:
        AudioLoadError: If the file is unreadable, too long, or too large.
    """
    import soundfile as sf

    if info is None:
        try:
            info = sf.info(path)
        except Exception as exc:
            raise AudioLoadError(
                f"Cannot read audio file: {os.path.basename(path)}"
            ) from exc

    check_duration_size(
        info.duration,
        os.path.getsize(path),
        max_duration=max_duration,
        max_file_size=max_file_size,
    )
    return info


def check_duration_size(
    duration: float,
    file_size: int,
    *,
    max_duration: float | None = None,
    max_file_size: int | None = None,
) -> None:
    """Enforce duration and file-size caps given already-measured values.

    Split out from :func:`enforce_decode_limits` so callers that hold an open
    file descriptor (load_audio) can pass an fd-derived duration/size and avoid
    a second open-by-path (Finding 4). Messages match the original load_audio
    guards.
    """
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
            effective_max_duration = DEFAULT_MAX_DURATION
    if effective_max_duration <= 0:
        raise AudioLoadError(
            f"max_duration must be a positive number, got {effective_max_duration}. "
            f"Check PHANTOM_MAX_DURATION env var or max_duration parameter."
        )
    if duration > effective_max_duration:
        mins = duration / 60
        limit_mins = effective_max_duration / 60
        raise AudioLoadError(
            f"Audio file is {mins:.1f} minutes ({duration:.0f}s), "
            f"which exceeds the {limit_mins:.0f}-minute limit "
            f"({effective_max_duration:.0f}s). "
            f"Set PHANTOM_MAX_DURATION to increase the limit, "
            f"or trim the file."
        )

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
            effective_max_size = DEFAULT_MAX_FILE_SIZE
    if effective_max_size <= 0:
        raise AudioLoadError(
            f"max_file_size must be a positive number, got {effective_max_size}. "
            f"Check PHANTOM_MAX_FILE_SIZE env var or max_file_size parameter."
        )
    if file_size > effective_max_size:
        raise AudioLoadError(
            f"Audio file is {file_size / 1_000_000:.1f} MB, "
            f"which exceeds the {effective_max_size / 1_000_000:.0f} MB limit. "
            f"Set PHANTOM_MAX_FILE_SIZE to increase the limit."
        )


def open_validated_input(path: str) -> int:
    """Open an already-validated input path for reading, returning a held fd.

    The caller MUST read via this descriptor (not re-open by path) and is
    responsible for closing it. When input confinement is active
    (PHANTOM_AUDIO_DIR set), the final component is opened with O_NOFOLLOW so a
    symlink swapped in after validate_input_path resolved the path is rejected
    (TOCTOU, Finding 4); the resolved target is a regular file, so legitimate
    symlinks *inside* the allowed dir are unaffected (they were already
    resolved). When confinement is unset, symlinks are followed as before.

    Residual: an attacker who can swap an intermediate *directory* component
    between validation and this open could still redirect; fully closing that
    needs openat-based traversal. The dominant final-component vector and the
    re-open-by-path gap are closed here.

    Raises:
        AudioLoadError: If the path cannot be opened safely or is not a regular
            file.
    """
    confined = bool(os.environ.get("PHANTOM_AUDIO_DIR"))
    flags = os.O_RDONLY
    if confined and hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise AudioLoadError(
            f"Cannot read audio file: {os.path.basename(path)}"
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise AudioLoadError(
                f"Cannot read audio file: {os.path.basename(path)} "
                "(not a regular file)."
            )
    except BaseException:
        os.close(fd)
        raise
    return fd


# Default sandbox for file writes when PHANTOM_OUTPUT_DIR is unset (Finding 1).
# Writes are ALWAYS confined; this is the fallback root, created on demand.
DEFAULT_OUTPUT_DIR = "~/.phantom/output"


def get_output_dir() -> str:
    """Return the confined output directory, creating the default if needed.

    Phantom confines every file write to an output directory (SEC-02, Finding 1).
    There is no longer an "unconfined" mode:

    - ``PHANTOM_OUTPUT_DIR`` set   -> use it; it must already exist.
    - ``PHANTOM_OUTPUT_DIR`` unset -> default ``~/.phantom/output``, created on
      demand so writes work out of the box.

    Returns:
        The realpath of the output directory.

    Raises:
        PathSecurityError: If an explicitly configured dir does not exist, or
            the default sandbox cannot be created.
    """
    configured = os.environ.get("PHANTOM_OUTPUT_DIR")
    if configured and configured.strip():
        real_base = os.path.realpath(configured)
        if not os.path.isdir(real_base):
            raise PathSecurityError(
                "PHANTOM_OUTPUT_DIR points to a directory that does not exist: "
                "check the path and create the directory."
            )
        return real_base

    default = os.path.expanduser(DEFAULT_OUTPUT_DIR)
    try:
        os.makedirs(default, exist_ok=True)
    except OSError as exc:
        raise PathSecurityError(
            f"Could not create the default output directory ({DEFAULT_OUTPUT_DIR}): "
            f"{exc}. Set PHANTOM_OUTPUT_DIR to a writable directory."
        ) from exc
    return os.path.realpath(default)


def atomic_write_text(path: str | Path, content: str) -> None:
    """Atomically write *content* to *path* without a predictable temp file.

    Creates a unique temp file (O_EXCL, mode 0600) in the destination directory
    via tempfile.mkstemp, then os.replace() to swap it in. This avoids a
    predictable '<target>.tmp' sibling that an attacker with directory write
    access could pre-place as a symlink to redirect the write.
    """
    path = Path(path)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, str(path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _get_env_int(name: str, default: int) -> int:
    """Read an integer from an environment variable, falling back to *default*.

    Returns *default* when the variable is unset or blank.  Raises
    ``AnalysisError`` with a musician-friendly message if the value is
    present but not a valid integer.
    """
    env_val = os.environ.get(name)
    if env_val is not None and env_val.strip():
        try:
            return int(env_val)
        except ValueError as exc:
            raise AnalysisError(f"{name} must be an integer, got: '{env_val}'") from exc
    return default


def _get_env_float(name: str, default: float) -> float:
    """Read a float from an environment variable, falling back to *default*.

    Returns *default* when the variable is unset or blank.  Raises
    ``AnalysisError`` with a musician-friendly message if the value is
    present but not a valid number.
    """
    env_val = os.environ.get(name)
    if env_val is not None and env_val.strip():
        try:
            return float(env_val)
        except ValueError as exc:
            raise AnalysisError(f"{name} must be a number, got: '{env_val}'") from exc
    return default


def wrap_errors(message_prefix: str):
    """Decorator that wraps unexpected exceptions in AnalysisError.

    PhantomError subclasses (AnalysisError, AudioLoadError, PathSecurityError,
    ProfileLoadError, DependencyMissingError) pass through unchanged.  All other
    exceptions are caught and re-raised as ``AnalysisError`` with *message_prefix*
    prepended and the original exception chained via ``__cause__``.

    Args:
        message_prefix: Human-readable context prepended to the wrapped message,
            e.g. ``"Spectral analysis failed"``.
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except PhantomError:
                raise
            except Exception as exc:
                raise AnalysisError(f"{message_prefix}: {exc}") from exc

        return wrapper

    return decorator


def _block_rms_db(
    mono: np.ndarray,
    block_size: int = 4096,
    hop: int = 2048,
) -> list[float]:
    """Compute per-block RMS levels in dBFS.

    Splits *mono* into overlapping blocks and returns the RMS of each
    block converted to dB.  Silent blocks (RMS == 0) are excluded.

    Args:
        mono: 1-D float32/float64 audio array.
        block_size: Number of samples per block (must be > 0).
        hop: Hop size between consecutive blocks (must be > 0).

    Returns:
        List of RMS values in dBFS, one per non-silent block.
    """
    if mono.ndim != 1:
        raise ValueError(f"mono must be 1-D, got {mono.ndim}-D array")
    if block_size <= 0:
        raise ValueError(f"block_size must be positive, got {block_size}")
    if hop <= 0:
        raise ValueError(f"hop must be positive, got {hop}")
    if not np.issubdtype(mono.dtype, np.floating):
        mono = mono.astype(np.float64)
    levels: list[float] = []
    for i in range(0, len(mono) - block_size + 1, hop):
        block = mono[i : i + block_size]
        rms = float(np.sqrt(np.mean(block**2)))
        if rms > 0:
            levels.append(20.0 * np.log10(rms))
    return levels


def is_near_silent(mono: np.ndarray) -> bool:
    """Check whether a mono signal is near-silent.

    Returns True if the RMS level is below SILENCE_THRESHOLD_DB.
    """
    if not np.issubdtype(mono.dtype, np.floating):
        mono = mono.astype(np.float64)
    rms = float(np.sqrt(np.mean(mono**2)))
    if rms == 0:
        return True
    rms_db = 20 * np.log10(rms)
    return rms_db < SILENCE_THRESHOLD_DB


def guarded_mono(audio: "AudioData", failure_label: str) -> np.ndarray | None:
    """Return ``audio.mono`` after the standard empty/silence guards (B.2).

    Every analyzer starts with the same two pre-checks: zero samples raise
    ``AnalysisError``, and a near-silent signal short-circuits to the
    analyzer's empty result. *failure_label* carries the per-module wrap
    prefix so the raised message stays identical, e.g.
    ``guarded_mono(audio, "Spectral analysis failed")``.

    The near-silence decision uses the memoized ``AudioData.is_near_silent``
    (mono mixdown, A.7). Callers that must check individual channels
    (stereo, phase) keep using the module-level :func:`is_near_silent` array
    helper instead.

    Returns:
        The mono mixdown when analysis should proceed, or ``None`` when the
        signal is near-silent -- the caller returns its empty result.

    Raises:
        AnalysisError: If the audio has 0 samples.
    """
    mono = audio.mono
    if len(mono) == 0:
        raise AnalysisError(f"{failure_label}: audio has 0 samples")
    if audio.is_near_silent:
        return None
    return mono


def validate_input_path(path: str) -> str:
    """Validate and resolve an input audio file path.

    When PHANTOM_AUDIO_DIR is set:
    - Relative paths are resolved relative to PHANTOM_AUDIO_DIR (D-01)
    - Symlinks resolved via os.path.realpath() (D-02)
    - Both base and path get realpath treatment (D-03)
    - Paths outside the allowed directory raise PathSecurityError

    When PHANTOM_AUDIO_DIR is unset:
    - Returns path unchanged (D-13, backwards compatible)

    Input reads are intentionally NOT confined by default: Phantom's core
    purpose is analyzing arbitrary audio files anywhere on disk. The residual
    risk is a read/parseability oracle (e.g. probing /etc/passwd) -- lower
    severity than writes, which ARE always confined (see validate_output_path).
    Set PHANTOM_AUDIO_DIR to confine reads as well.

    Args:
        path: File path string to validate.

    Returns:
        The validated (possibly resolved) path string.

    Raises:
        PathSecurityError: If the resolved path is outside PHANTOM_AUDIO_DIR.
    """
    audio_dir = os.environ.get("PHANTOM_AUDIO_DIR")
    if not audio_dir:
        return path  # No restriction (D-13)

    # D-01: Resolve relative paths against PHANTOM_AUDIO_DIR
    if not os.path.isabs(path):
        path = os.path.join(audio_dir, path)

    # D-02, D-03: Resolve both sides via realpath
    real_base = os.path.realpath(audio_dir)
    real_path = os.path.realpath(path)

    # SC-7: Directory existence check
    if not os.path.isdir(real_base):
        raise PathSecurityError(
            "PHANTOM_AUDIO_DIR points to a directory that does not exist: "
            "check the path and create the directory."
        )

    # Containment check (pattern from _profiles.py, with os.sep suffix)
    if not (real_path.startswith(real_base + os.sep) or real_path == real_base):
        raise PathSecurityError(
            "Access denied: audio file is outside the allowed directory. "
            "Set PHANTOM_AUDIO_DIR to a directory containing your audio files."
        )

    return real_path


def validate_output_path(path: str) -> str:
    """Validate an output path against the confined output directory.

    Writes are ALWAYS confined (SEC-02, Finding 1). The base directory is
    ``PHANTOM_OUTPUT_DIR`` when set, otherwise the default ``~/.phantom/output``
    sandbox (see :func:`get_output_dir`). Relative paths resolve against the
    base; symlinks are resolved and containment is re-verified on the final
    realpath before it is returned to the caller for opening.

    Args:
        path: Output path string to validate.

    Returns:
        The validated, fully resolved (realpath) output path.

    Raises:
        PathSecurityError: If the resolved path escapes the output directory,
            or the output directory is missing/uncreatable.
    """
    real_base = get_output_dir()

    # Resolve relative paths against the confined base.
    if not os.path.isabs(path):
        path = os.path.join(real_base, path)

    # Resolve symlinks and re-verify containment on the FINAL path.
    real_path = os.path.realpath(path)

    if not (real_path.startswith(real_base + os.sep) or real_path == real_base):
        raise PathSecurityError(
            "Access denied: output path is outside the allowed directory. "
            "Set PHANTOM_OUTPUT_DIR to the directory where outputs should be "
            "written, or write within the default ~/.phantom/output sandbox."
        )

    return real_path
