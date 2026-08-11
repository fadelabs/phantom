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
        "PHANTOM_MAX_DECODED_BYTES",
        "int",
        "1000000000",
        "Maximum decoded float32 footprint per audio file in bytes.",
    ),
    EnvVar(
        "PHANTOM_MAX_AGGREGATE_BYTES",
        "int",
        "4000000000",
        "Combined decoded-size cap for multi-file tools.",
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
        "PHANTOM_CLIPPING_THRESHOLD",
        "float",
        "1.0",
        "Sample magnitude at or above this counts as clipping (PROB-01).",
    ),
    EnvVar(
        "PHANTOM_DC_OFFSET_THRESHOLD",
        "float",
        "0.0005",
        "Mean sample value above this flags DC offset (PROB-02).",
    ),
    EnvVar(
        "PHANTOM_ISP_OVERSHOOT_DB",
        "float",
        "0.5",
        "True-peak overshoot above this flags inter-sample peaks (PROB-03).",
    ),
    EnvVar(
        "PHANTOM_ISP_SEVERE_DBTP",
        "float",
        "-1.0",
        "True peak above this raises ISP severity to significant (PROB-03).",
    ),
    EnvVar(
        "PHANTOM_DYNAMIC_SPREAD_MIN_DB",
        "float",
        "10.0",
        "Minimum P90-P10 block spread to trust a noise-floor estimate (PROB-04/05).",
    ),
    EnvVar(
        "PHANTOM_NOISE_FLOOR_MODERATE_DB",
        "float",
        "-50.0",
        "Noise floor above this is flagged moderate (PROB-04).",
    ),
    EnvVar(
        "PHANTOM_NOISE_FLOOR_MINOR_DB",
        "float",
        "-60.0",
        "Noise floor above this is flagged minor (PROB-04).",
    ),
    EnvVar(
        "PHANTOM_SNR_PROFESSIONAL_DB",
        "float",
        "60.0",
        "SNR at or above this counts as professional (PROB-05).",
    ),
    EnvVar(
        "PHANTOM_SNR_POOR_DB",
        "float",
        "50.0",
        "SNR below this is flagged poor/significant (PROB-05).",
    ),
    EnvVar(
        "PHANTOM_SPECTRAL_FLATNESS_MIN",
        "float",
        "0.01",
        "Minimum flatness to run band-excess detectors (PROB-07/08/09).",
    ),
    EnvVar(
        "PHANTOM_BAND_EXCESS_THRESHOLD_DB",
        "float",
        "6.0",
        "Band energy above expected level triggers detection (PROB-07/08/09).",
    ),
    EnvVar(
        "PHANTOM_RESONANCE_MEDIAN_FLOOR_DB",
        "float",
        "-40.0",
        "Median spectral level floor for resonance detection (PROB-10).",
    ),
    EnvVar(
        "PHANTOM_RESONANCE_PROMINENCE_DB",
        "int",
        "12",
        "Peak prominence threshold for resonance detection (PROB-10).",
    ),
    EnvVar(
        "PHANTOM_LOSSY_SHELF_DROP_DB",
        "float",
        "20.0",
        "Shelf drop above this indicates a lossy codec (PROB-13).",
    ),
    EnvVar(
        "PHANTOM_MASKING_SEVERITY_HIGH",
        "float",
        "0.6",
        "Overlap score at or above this is labeled high severity.",
    ),
    EnvVar(
        "PHANTOM_MASKING_SEVERITY_MODERATE",
        "float",
        "0.3",
        "Overlap score at or above this is labeled moderate severity.",
    ),
    EnvVar(
        "PHANTOM_MASKING_SEVERITY_LOW",
        "float",
        "0.1",
        "Overlap score at or above this is labeled low severity.",
    ),
    EnvVar(
        "PHANTOM_MASKING_FLOOR_DB",
        "float",
        "40.0",
        "Bands more than this below the pair peak are zeroed before scoring.",
    ),
    EnvVar(
        "PHANTOM_SPECTRAL_FRAME_SIZE",
        "int",
        "2048",
        "Frame size of the main spectral analysis pass.",
    ),
    EnvVar(
        "PHANTOM_SPECTRAL_HOP_SIZE",
        "int",
        "1024",
        "Hop size of the main spectral analysis pass.",
    ),
    EnvVar(
        "PHANTOM_OCTAVE_FRAME_SIZE",
        "int",
        "4096",
        "Frame size of the octave-band energy pass (spectral + masking).",
    ),
    EnvVar(
        "PHANTOM_OCTAVE_HOP_SIZE",
        "int",
        "2048",
        "Hop size of the octave-band energy pass (spectral + masking).",
    ),
    EnvVar(
        "PHANTOM_FLATNESS_FRAME_SIZE",
        "int",
        "4096",
        "Frame size of the spectral-flatness gate (band-excess detectors).",
    ),
    EnvVar(
        "PHANTOM_SPECTRUM_FRAME_SIZE",
        "int",
        "8192",
        "Frame size of the shared power-spectrum pass (resonance, lossy).",
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
