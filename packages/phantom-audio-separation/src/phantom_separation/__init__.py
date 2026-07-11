"""Demucs-based stem separation plugin for phantom-audio.

Exposes separate_stems() via the ``phantom.separation`` entry-point group;
phantom-audio's thin shim (phantom.separation) discovers and dispatches to
it automatically when this package is installed.
"""

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _metadata_version

    __version__ = _metadata_version("phantom-audio-separation")
except PackageNotFoundError:
    __version__ = "unknown"

from phantom_separation.demucs_backend import separate_stems

__all__ = ["separate_stems", "__version__"]
