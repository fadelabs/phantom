"""Load the native analysis engine only when an algorithm is requested.

Installation diagnostics and result models remain importable when Essentia is
missing or its native library cannot load.
"""

from importlib import import_module

from phantom.exceptions import AnalysisError


def __getattr__(name: str):
    if name.startswith("__"):
        raise AttributeError(name)
    try:
        engine = import_module("essentia.standard")
    except (ImportError, OSError) as exc:
        raise AnalysisError(
            "The Essentia analysis engine is unavailable. Run phantom doctor "
            "to diagnose the installation. Audio analysis currently requires "
            "macOS or Linux."
        ) from exc
    return getattr(engine, name)
