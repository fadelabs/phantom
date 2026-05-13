"""Shared diagnostic utilities for doctor and server startup preflight."""

from __future__ import annotations

CORE_DEPS = {
    "numpy": "numpy",
    "scipy": "scipy",
    "soundfile": "soundfile",
    "essentia": "essentia",
    "pydantic": "pydantic",
    "fastmcp": "fastmcp",
    "plotext": "plotext",
    "rich_click": "rich_click",
}

OPTIONAL_DEPS = {
    "demucs": "separation",
    "matchering": "matching",
    "pedalboard": "processing",
    "librosa": "analysis",
}


def try_import(name: str) -> tuple[bool, str]:
    """Try to import a package. Returns (success, version_or_error)."""
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        return True, str(version)
    except Exception as exc:
        return False, str(exc)
