"""Canonical registry of the environment variables Phantom honors.

Single source of truth for the ``PHANTOM_*`` env vars the runtime reads.
``phantom doctor`` derives its environment-variable table from this registry
instead of maintaining its own list, and ``tests/test_cli_doctor.py`` scans
the source for env-read literals and asserts the registry covers exactly
those — so the two cannot drift apart.

The registry carries the variable name, its value kind (dir / int / float /
flag), a documented default, and a one-line purpose. It does not read values
itself; callers still read env vars where they need them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvVar:
    """Declarative metadata for one ``PHANTOM_*`` environment variable."""

    name: str
    kind: str  # "dir" | "int" | "float" | "flag"
    default: str
    purpose: str


ENV_VARS: tuple[EnvVar, ...] = (
    EnvVar(
        "PHANTOM_AUDIO_DIR",
        "dir",
        "",
        "Restrict audio file reads to this directory tree.",
    ),
    EnvVar(
        "PHANTOM_OUTPUT_DIR",
        "dir",
        "~/.phantom/output",
        "Directory all file writes are confined to.",
    ),
    EnvVar(
        "PHANTOM_PROFILES_DIR",
        "dir",
        "",
        "Custom reference profile directory (overrides built-ins).",
    ),
    EnvVar(
        "PHANTOM_METRICS_DIR",
        "dir",
        "(platform default)",
        "Directory for live metrics snapshots.",
    ),
    EnvVar(
        "PHANTOM_MAX_DURATION",
        "float",
        "900",
        "Maximum audio duration in seconds.",
    ),
    EnvVar(
        "PHANTOM_MAX_FILE_SIZE",
        "int",
        "500000000",
        "Maximum audio file size in bytes.",
    ),
    EnvVar(
        "PHANTOM_MAX_AGGREGATE_BYTES",
        "int",
        "4000000000",
        "Combined decoded-size cap for multi-stem tools.",
    ),
    EnvVar(
        "PHANTOM_MASKING_TOP_N",
        "int",
        "",
        "Number of top masking pairs returned (auto when unset).",
    ),
    EnvVar(
        "PHANTOM_PHAT_WINDOW_S",
        "float",
        "10.0",
        "GCC-PHAT cross-correlation window in seconds.",
    ),
    EnvVar(
        "PHANTOM_POLARITY_THRESHOLD",
        "float",
        "-0.5",
        "L/R correlation below this flags polarity inversion.",
    ),
    EnvVar(
        "PHANTOM_CREST_FACTOR_LOW_DB",
        "float",
        "6.0",
        "Crest factor below this marks a track as over-compressed.",
    ),
    EnvVar(
        "PHANTOM_PROFILE_MERGE",
        "flag",
        "",
        "Merge a user profile over the built-in instead of replacing it.",
    ),
    EnvVar(
        "PHANTOM_PROFILE_OVERRIDE_QUIET",
        "flag",
        "",
        "Silence the user-profile-override log line.",
    ),
    EnvVar(
        "PHANTOM_DEBUG",
        "flag",
        "",
        "Enable verbose error output from MCP tools.",
    ),
    EnvVar(
        "PHANTOM_QUIET",
        "flag",
        "",
        "Suppress startup preflight messages.",
    ),
)
