"""Tunable analysis settings (C.1).

Centralizes the analysis thresholds and frame sizes that used to be fixed
module constants: polarity -0.5, crest 6.0, the detect_problems threshold
block, masking severity splits, and the FFT/frame sizes. Every knob has an
environment-variable override (``PHANTOM_*``) falling back to a default that
reproduces the original constant exactly, and every consuming analyzer
accepts an explicit :class:`AnalysisSettings` instance for programmatic
tuning.

Settings resolve per call, not at import: the analyzers read the effective
settings when they run, so an env change takes effect without a restart and
monkeypatch-based tests work naturally. Because results can differ by
settings, the analysis cache folds a settings fingerprint into its key
(``phantom._cache``) so a tuned run never serves a hit computed under
different settings.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from phantom._utils import _get_env_float

# ---------------------------------------------------------------------------
# The settings object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AnalysisSettings:
    """Tunable analysis thresholds and frame sizes.

    Defaults reproduce the constants they replace exactly: no env var set and
    no explicit instance means byte-identical results to before C.1. All
    fields are plain numbers; equality/ordering are value-based (frozen
    dataclass).

    Phase (``phantom.phase``)
    -------------------------
    polarity_threshold:
        Overall L/R correlation below this flags polarity inversion
        (was the literal -0.5).
    phat_window_s:
        GCC-PHAT truncation window in seconds (env: ``PHANTOM_PHAT_WINDOW_S``,
        which predates this module and keeps its name).

    Dynamics (``phantom.dynamics``)
    -------------------------------
    crest_factor_low_db:
        Crest factor below this marks the track as low-crest /
        over-compressed (was the literal 6.0).
    """

    polarity_threshold: float = -0.5
    phat_window_s: float = 10.0
    crest_factor_low_db: float = 6.0

    def fingerprint(self) -> str:
        """Deterministic per-value hash used for analysis cache keys.

        Two instances with equal knob values hash identically; any env- or
        programmatic- difference produces a different fingerprint, so the
        shared analysis cache cannot serve a result computed under different
        settings (see ``phantom._cache._cached_analysis``). The repr of the
        field tuple is deterministic within and across processes.
        """
        values = tuple(v for _, v in vars(self).items())
        return hashlib.sha256(repr(values).encode()).hexdigest()


def analysis_settings() -> AnalysisSettings:
    """Resolve the effective settings for this call from the environment.

    Reads the ``PHANTOM_*`` override for every knob (per call, matching the
    ``PHANTOM_PHAT_WINDOW_S`` idiom) and returns an :class:`AnalysisSettings`
    with env values where set and the documented defaults otherwise. A
    malformed value raises a musician-friendly ``AnalysisError``, exactly as
    ``_get_env_float`` already does for the window knob.
    """
    return AnalysisSettings(
        polarity_threshold=_get_env_float("PHANTOM_POLARITY_THRESHOLD", -0.5),
        phat_window_s=_get_env_float("PHANTOM_PHAT_WINDOW_S", 10.0),
        crest_factor_low_db=_get_env_float("PHANTOM_CREST_FACTOR_LOW_DB", 6.0),
    )
