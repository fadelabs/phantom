"""Reference profile data models and loader functions.

Provides the ReferenceProfile Pydantic model hierarchy for genre-specific
audio engineering targets. Profiles define what "good" sounds like for a
genre: loudness, frequency balance, stereo conventions, and spatial processing.

Public API:
    load_profile(name) — Load a genre profile by name (case-insensitive, alias-aware).
    list_profiles()    — List all available profile names (built-in + user).
"""

from __future__ import annotations

import importlib.resources
import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from phantom.exceptions import ProfileLoadError


class LoudnessTargets(BaseModel):
    """Target loudness range for a genre."""

    model_config = ConfigDict(frozen=True)

    lufs_range: tuple[float, float]
    crest_factor_range: tuple[float, float]
    true_peak_max_dbtp: float


class FrequencyTargets(BaseModel):
    """Target frequency balance as dB offsets from flat per octave band."""

    model_config = ConfigDict(frozen=True)

    bands: dict[str, float]


class StereoConventions(BaseModel):
    """Stereo field conventions for a genre."""

    model_config = ConfigDict(frozen=True)

    width: str
    mono_below_hz: float


class SpatialConventions(BaseModel):
    """Reverb and spatial processing conventions."""

    model_config = ConfigDict(frozen=True)

    reverb_type: str
    reverb_amount: str
    pre_delay_ms: str


class ReferenceProfile(BaseModel):
    """Complete reference profile for a genre.

    Attributes:
        genre: Genre identifier (e.g. "rock", "hip-hop").
        description: Human-readable genre description.
        loudness: Target loudness ranges (LUFS, crest factor, true peak).
        frequency: Target frequency balance per octave band.
        stereo: Stereo field conventions (width, mono-below).
        spatial: Reverb and spatial processing conventions.
        processing_notes: Genre-specific mixing/mastering approach text.
    """

    model_config = ConfigDict(frozen=True)

    genre: str
    description: str
    loudness: LoudnessTargets
    frequency: FrequencyTargets
    stereo: StereoConventions
    spatial: SpatialConventions
    processing_notes: str


# ---------------------------------------------------------------------------
# Alias mapping (D-07 case-insensitive, D-08 common aliases)
# ---------------------------------------------------------------------------

_ALIASES: dict[str, str] = {
    "hiphop": "hip-hop",
    "hip hop": "hip-hop",
    "lofi": "lo-fi",
    "lo fi": "lo-fi",
    "rockmetal": "rock-metal",
    "rock metal": "rock-metal",
}


def _resolve_name(name: str) -> str:
    """Resolve a profile name: strip, lowercase, then alias lookup."""
    key = name.strip().lower()
    resolved = _ALIASES.get(key, key)
    # Reject path traversal attempts
    if "/" in resolved or "\\" in resolved or ".." in resolved:
        raise ProfileLoadError(
            f"Invalid profile name: '{name}'. "
            "Profile names must not contain path separators or '..'."
        )
    return resolved


# ---------------------------------------------------------------------------
# Internal loaders
# ---------------------------------------------------------------------------


def _load_user_profile(name: str) -> dict | None:
    """Try loading a profile from the user's custom profiles directory.

    Returns None if PHANTOM_PROFILES_DIR is not set or file not found.
    """
    user_dir = os.environ.get("PHANTOM_PROFILES_DIR")
    if not user_dir:
        return None
    path = Path(user_dir) / f"{name}.json"

    # Realpath containment check (X-WR-03, S-WR-04)
    resolved_path = path.resolve()
    base = Path(user_dir).resolve()
    if not str(resolved_path).startswith(str(base) + os.sep) and resolved_path != base:
        raise ProfileLoadError(f"Invalid profile name: '{name}'")
    path = resolved_path

    if not path.is_file():
        return None

    # File size guard (X-WR-02): reject profiles larger than 1 MB
    if path.stat().st_size > 1_000_000:
        raise ProfileLoadError(f"Profile file too large: {name}")

    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProfileLoadError(
            f"Profile '{name}' contains invalid JSON: {exc}"
        ) from exc


def _load_builtin_profile(name: str) -> dict | None:
    """Load a built-in profile JSON file from the phantom.profiles subpackage.

    Returns None if the profile does not exist.
    """
    profiles_pkg = importlib.resources.files("phantom.profiles")
    resource = profiles_pkg.joinpath(f"{name}.json")
    if not resource.is_file():
        return None
    text = resource.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProfileLoadError(
            f"Built-in profile '{name}' contains invalid JSON: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_profiles() -> list[str]:
    """List all available reference profile names.

    Returns profiles from both the user's custom directory (PHANTOM_PROFILES_DIR)
    and the built-in profiles bundled with Phantom. User profiles that share a
    name with a built-in profile will appear once (the user version takes
    precedence when loaded).

    Returns:
        Sorted list of profile names (without .json extension).
    """
    names: set[str] = set()

    # Scan user directory first
    user_dir = os.environ.get("PHANTOM_PROFILES_DIR")
    if user_dir:
        user_path = Path(user_dir)
        if user_path.is_dir():
            for item in user_path.iterdir():
                if item.is_file() and item.suffix == ".json":
                    names.add(item.stem)

    # Scan built-in profiles
    profiles_pkg = importlib.resources.files("phantom.profiles")
    for item in profiles_pkg.iterdir():
        if hasattr(item, "name") and item.name.endswith(".json") and item.is_file():
            names.add(item.name.removesuffix(".json"))

    return sorted(names)


def load_profile(name: str) -> ReferenceProfile:
    """Load a genre reference profile by name.

    Profile names are case-insensitive. Common aliases are supported:
    "hiphop" resolves to "hip-hop", "lofi" to "lo-fi", "rockmetal" to
    "rock-metal".

    Search order (per REF-06):
        1. PHANTOM_PROFILES_DIR environment variable directory (user overrides)
        2. Built-in profiles bundled with Phantom

    A user profile completely replaces the built-in profile of the same name
    (no partial merging).

    Args:
        name: Genre name (e.g. "rock", "hip-hop", "lofi").

    Returns:
        ReferenceProfile with the genre's loudness, frequency, stereo,
        and spatial targets.

    Raises:
        ProfileLoadError: If the profile is not found or is malformed.
    """
    resolved = _resolve_name(name)

    # Search order: user directory first, then builtins (D-09)
    raw = _load_user_profile(resolved)
    if raw is None:
        raw = _load_builtin_profile(resolved)

    if raw is None:
        available = list_profiles()
        raise ProfileLoadError(
            f"No profile found for '{name}'. Available profiles: {', '.join(available)}"
        )

    try:
        return ReferenceProfile.model_validate(raw)
    except ValidationError as exc:
        raise ProfileLoadError(f"Profile '{name}' is malformed: {exc}") from exc
