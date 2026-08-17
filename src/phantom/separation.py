"""Stem separation dispatch shim.

The Demucs implementation lives in the sibling distribution
``phantom-audio-separation`` (see packages/phantom-audio-separation) so the
core library carries no PyTorch dependency tree. This module keeps the
public API stable: it discovers an installed separation backend through the
``phantom.separation`` entry-point group and dispatches to it, or raises
DependencyMissingError with the familiar install hint when no plugin is
installed. The ``phantom-audio[separation]`` extra remains a meta-installer
that pulls in phantom-audio-separation.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from collections.abc import Callable

from pydantic import BaseModel

from phantom.exceptions import DependencyMissingError
from phantom._utils import wrap_errors

#: Entry-point group that separation backend plugins register under.
SEPARATION_EP_GROUP = "phantom.separation"


class SeparationResult(BaseModel):
    """Result of stem separation."""

    stems: dict[str, str]


def _load_backend() -> Callable[[str, str], SeparationResult] | None:
    """Discover and load the first installed separation backend plugin.

    Returns the backend callable, or None when no plugin is installed.
    Load errors from a present-but-broken plugin propagate to the caller
    (wrap_errors turns them into AnalysisError with context).
    """
    for ep in entry_points(group=SEPARATION_EP_GROUP):
        return ep.load()
    return None


@wrap_errors("Source separation failed")
def separate_stems(input_path: str, output_dir: str) -> SeparationResult:
    """Separate a stereo mix into individual stems (vocals, drums, bass, other).

    Dispatches to the installed separation backend plugin (normally
    phantom-audio-separation, which uses Meta's Hybrid Transformer Demucs
    model). Each stem is saved as a WAV file in the output directory.

    Separation is an optional feature. If no backend plugin is installed,
    a DependencyMissingError is raised with install instructions.

    Note: First use downloads the htdemucs model (~80 MB). Subsequent
    calls use the cached model.

    Args:
        input_path: Path to the input WAV file to separate.
        output_dir: Directory where stem WAV files will be written.
            Created if it does not exist.

    Returns:
        SeparationResult model with stems dict mapping stem names to
        output file paths:
        {"vocals": "/out/vocals.wav", "drums": "/out/drums.wav",
         "bass": "/out/bass.wav", "other": "/out/other.wav"}

    Raises:
        DependencyMissingError: If no separation plugin is installed (per D-06).
        PathSecurityError: If output_dir is outside PHANTOM_OUTPUT_DIR (when set).
        FileNotFoundError: If input file does not exist.
        AnalysisError: If separation processing fails.
    """
    backend = _load_backend()
    if backend is None:
        raise DependencyMissingError(
            package="phantom-audio-separation",
            extra="separation",
            detail=(
                "Stem separation ships as the sibling package "
                "phantom-audio-separation, which provides AI-powered source "
                "separation into vocals, drums, bass, and other stems."
            ),
        )
    return backend(input_path, output_dir)
