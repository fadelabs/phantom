"""Shared utility functions for Phantom analysis modules."""

from __future__ import annotations

import functools
import os

import numpy as np

from phantom.exceptions import AnalysisError, PathSecurityError, PhantomError

# Silence threshold in dBFS -- signals below this are treated as silence.
SILENCE_THRESHOLD_DB = -80.0


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
            raise AnalysisError(
                f"{name} must be an integer, got: '{env_val}'"
            ) from exc
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
            raise AnalysisError(
                f"{name} must be a number, got: '{env_val}'"
            ) from exc
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
    rms = float(np.sqrt(np.mean(mono**2)))
    if rms == 0:
        return True
    rms_db = 20 * np.log10(rms)
    return rms_db < SILENCE_THRESHOLD_DB


def validate_input_path(path: str) -> str:
    """Validate and resolve an input audio file path.

    When PHANTOM_AUDIO_DIR is set:
    - Relative paths are resolved relative to PHANTOM_AUDIO_DIR (D-01)
    - Symlinks resolved via os.path.realpath() (D-02)
    - Both base and path get realpath treatment (D-03)
    - Paths outside the allowed directory raise PathSecurityError

    When PHANTOM_AUDIO_DIR is unset:
    - Returns path unchanged (D-13, backwards compatible)

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
    """Validate an output path against PHANTOM_OUTPUT_DIR restriction.

    When PHANTOM_OUTPUT_DIR is set:
    - Resolved path must be within the allowed output directory
    - Symlinks resolved via os.path.realpath()

    When PHANTOM_OUTPUT_DIR is unset:
    - Returns path unchanged (D-11, backwards compatible)

    Args:
        path: Output path string to validate.

    Returns:
        The validated (possibly resolved) path string.

    Raises:
        PathSecurityError: If the resolved path is outside PHANTOM_OUTPUT_DIR.
    """
    output_dir = os.environ.get("PHANTOM_OUTPUT_DIR")
    if not output_dir:
        return path  # No restriction (D-11)

    # Resolve relative paths against PHANTOM_OUTPUT_DIR (consistent with input)
    if not os.path.isabs(path):
        path = os.path.join(output_dir, path)

    real_base = os.path.realpath(output_dir)
    real_path = os.path.realpath(path)

    # Directory existence check (consistent with validate_input_path)
    if not os.path.isdir(real_base):
        raise PathSecurityError(
            "PHANTOM_OUTPUT_DIR points to a directory that does not exist: "
            "check the path and create the directory."
        )

    if not (real_path.startswith(real_base + os.sep) or real_path == real_base):
        raise PathSecurityError(
            "Access denied: output path is outside the allowed directory. "
            "Set PHANTOM_OUTPUT_DIR to a directory where outputs should be written."
        )

    return real_path
