"""Phantom Link live metrics reader.

The Phantom Studio plugin publishes an analysis snapshot as JSON at 2 Hz to
``<metrics dir>/<instance-uuid>.json`` and deletes the file when the plugin
instance closes. This module reads those snapshots so Claude can ground
mixing advice in the numbers currently on the user's meters.

The metrics directory comes from ``PHANTOM_METRICS_DIR`` when set, otherwise
the platform default matching the plugin's publisher (``~/Library/
PhantomStudio/metrics`` on macOS). Reads bypass ``load_audio``'s sandbox, so
this module does its own path containment: the directory is realpath-resolved
and only regular ``*.json`` files that resolve inside it are eligible.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

from pydantic import BaseModel

from phantom.exceptions import AnalysisError, PathSecurityError

#: Snapshots older than this are flagged stale. The publisher writes at 2 Hz
#: and removes its file on shutdown, so a stale file usually means the plugin
#: host crashed or the DAW froze.
STALE_AFTER_SECONDS = 10.0

_INSTANCE_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]+$")

_NO_METRICS_MSG = (
    "No live metrics found — is the Phantom Studio plugin running? "
    "Load it on a track and start playback, then try again."
)
_UNREADABLE_MSG = "Live metrics file is unreadable right now — try again in a second."


class LiveMetricsResult(BaseModel):
    """Typed response for the read_live_metrics server tool."""

    instance_id: str
    age_seconds: float
    stale: bool
    instance_count: int
    snapshot: dict


def get_metrics_dir() -> str:
    """Resolve the metrics directory (PHANTOM_METRICS_DIR or platform default)."""
    env = os.environ.get("PHANTOM_METRICS_DIR")
    if env:
        return env
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/PhantomStudio/metrics")
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "PhantomStudio", "metrics")
    return os.path.expanduser("~/.config/PhantomStudio/metrics")


def _contained_json_files(real_base: str) -> list[str]:
    """List regular ``*.json`` files whose realpath stays inside the dir.

    The metrics dir only ever holds files the plugin wrote itself, so a
    symlink resolving elsewhere is not ours to read and is skipped.
    """
    files: list[str] = []
    for name in os.listdir(real_base):
        if not name.endswith(".json"):
            continue
        real = os.path.realpath(os.path.join(real_base, name))
        if not real.startswith(real_base + os.sep):
            continue
        if os.path.isfile(real):
            files.append(real)
    return files


def _newest_snapshot(candidates: list[str]) -> str:
    """Return the most recently written snapshot among *candidates*.

    A snapshot can vanish between listing and selection when its plugin
    instance closes -- the same race the read path handles -- so the mtime
    probe is guarded here rather than left to escape as a raw OSError.
    """
    if not candidates:
        raise AnalysisError(_NO_METRICS_MSG)
    try:
        return max(candidates, key=os.path.getmtime)
    except OSError as e:
        raise AnalysisError(_NO_METRICS_MSG) from e


def read_live_metrics(instance_id: str | None = None) -> LiveMetricsResult:
    """Read the newest (or a specific instance's) live metrics snapshot.

    Args:
        instance_id: Optional plugin instance UUID (the metrics file stem).
            When omitted, the most recently written snapshot is returned.

    Raises:
        AnalysisError: No snapshot is available or it cannot be parsed.
        PathSecurityError: ``instance_id`` is malformed or escapes the dir.
    """
    real_base = os.path.realpath(get_metrics_dir())
    if not os.path.isdir(real_base):
        raise AnalysisError(_NO_METRICS_MSG)

    candidates = _contained_json_files(real_base)

    if instance_id is not None:
        if not _INSTANCE_ID_REGEX.match(instance_id):
            raise PathSecurityError(
                "Invalid instance id: only letters, digits, '-' and '_' are allowed."
            )
        wanted = os.path.realpath(os.path.join(real_base, instance_id + ".json"))
        if not wanted.startswith(real_base + os.sep):
            raise PathSecurityError(
                "Access denied: instance id resolves outside the metrics directory."
            )
        if wanted not in candidates:
            raise AnalysisError(
                f"No live metrics for instance '{instance_id}' — "
                "is that plugin instance still open?"
            )
        chosen = wanted
    else:
        chosen = _newest_snapshot(candidates)

    try:
        mtime = os.path.getmtime(chosen)
        with open(chosen, encoding="utf-8") as fh:
            snapshot = json.load(fh)
    except OSError as e:
        # File vanished between listing and reading (plugin closed).
        raise AnalysisError(_NO_METRICS_MSG) from e
    except json.JSONDecodeError as e:
        raise AnalysisError(_UNREADABLE_MSG) from e

    if not isinstance(snapshot, dict):
        raise AnalysisError(_UNREADABLE_MSG)

    age = max(0.0, time.time() - mtime)
    return LiveMetricsResult(
        instance_id=os.path.splitext(os.path.basename(chosen))[0],
        age_seconds=round(age, 3),
        stale=age > STALE_AFTER_SECONDS,
        instance_count=len(candidates),
        snapshot=snapshot,
    )
