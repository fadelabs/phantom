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

# Optional deps probed by direct import. Stem separation is NOT probed this
# way anymore: it ships as the sibling plugin distribution
# phantom-audio-separation and is detected via separation_plugin_status().
OPTIONAL_DEPS = {
    "matchering": "matching",
    "pedalboard": "processing",
    "librosa": "analysis",
}

#: Entry-point group that separation backend plugins register under.
#: Mirrors phantom.separation.SEPARATION_EP_GROUP (kept here too so
#: diagnostics never import the dispatch module).
SEPARATION_EP_GROUP = "phantom.separation"

#: Distribution that provides the separation plugin (install hint / doctor row).
SEPARATION_PLUGIN_DIST = "phantom-audio-separation"


def try_import(name: str) -> tuple[bool, str]:
    """Try to import a package. Returns (success, version_or_error)."""
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        return True, str(version)
    except Exception as exc:
        return False, str(exc)


def separation_plugin_status() -> tuple[bool, str]:
    """Check whether a separation backend plugin is installed and loadable.

    Returns (ok, version_or_error). ok is True only when an entry point in
    the phantom.separation group is present AND its module imports
    successfully -- a merely-present-but-broken plugin reports False so
    ``phantom doctor`` never claims separation works when it does not.
    """
    from importlib.metadata import entry_points, version as dist_version

    try:
        eps = list(entry_points(group=SEPARATION_EP_GROUP))
    except Exception as exc:
        return False, str(exc)
    if not eps:
        return False, "not installed"
    ep = eps[0]
    try:
        ep.load()
    except Exception as exc:
        return False, f"plugin found but failed to load: {exc}"
    try:
        dist = getattr(ep, "dist", None)
        name = dist.name if dist is not None else SEPARATION_PLUGIN_DIST
        return True, str(dist_version(name))
    except Exception:
        return True, "?"
