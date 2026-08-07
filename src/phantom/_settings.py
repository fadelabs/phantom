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

Comparability caveat for the FFT-size knobs
-------------------------------------------
The frame/hop knobs below change the analysis geometry: a different
octave-band or spectral frame size produces different band energies and
descriptors. The built-in genre profiles and reference-target comparisons
(``compare_to_profile`` / ``compare_to_reference``) are calibrated to the
default geometry, so results computed under non-default FFT sizes are not
numerically comparable with profile or reference targets. Reset the knobs
to defaults before comparing, or re-run the comparison itself under the
same tuned geometry.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from phantom._utils import _get_env_float, _get_env_int

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

    Problems (``phantom.problems``, ``PROB-01`` family)
    ----------------------------------------------------
    One knob per detector threshold; defaults are the former module
    constants. Codes refer to the detectors they gate:
    clipping_threshold (PROB-01), dc_offset_threshold (PROB-02),
    isp_overshoot_threshold_db / isp_severe_dbtp (PROB-03),
    dynamic_spread_min_db / noise_floor_moderate_db / noise_floor_minor_db
    (PROB-04), snr_professional_db / snr_poor_db (PROB-05),
    spectral_flatness_min / band_excess_threshold_db (PROB-07/08/09),
    resonance_median_floor_db / resonance_prominence_db (PROB-10),
    lossy_shelf_drop_db (PROB-13).

    Masking (``phantom.masking``)
    ------------------------------
    severity_high / severity_moderate / severity_low:
        Overlap-score boundaries for the high/moderate/low/none labels.
    masking_floor_db:
        Bands more than this far below the pair peak are zeroed before
        scoring.

    FFT / frame sizes (``phantom.spectral``, ``phantom._bands``,
    ``phantom.problems``)
    -------------------------------------------------------------------------
    spectral_frame_size / spectral_hop_size:
        Main spectral pass (2048/1024 at 44.1k, ~46ms/~23ms).
    octave_frame_size / octave_hop_size:
        Octave-band energy pass, shared by spectral and masking (4096/2048).
    flatness_frame_size:
        Spectral-flatness gate used by the band-excess detectors (4096).
    spectrum_frame_size:
        Shared average-power-spectrum pass used by resonance and lossy-codec
        detection (8192).

    Changing any frame size changes measured values; see the module
    docstring's comparability caveat before tuning.
    """

    # Phase / dynamics (previous migration).
    polarity_threshold: float = -0.5
    phat_window_s: float = 10.0
    crest_factor_low_db: float = 6.0

    # Problem detection threshold block (PROB-01..13).
    clipping_threshold: float = 1.0
    dc_offset_threshold: float = 5e-4
    isp_overshoot_threshold_db: float = 0.5
    isp_severe_dbtp: float = -1.0
    dynamic_spread_min_db: float = 10.0
    noise_floor_moderate_db: float = -50.0
    noise_floor_minor_db: float = -60.0
    snr_professional_db: float = 60.0
    snr_poor_db: float = 50.0
    spectral_flatness_min: float = 0.01
    band_excess_threshold_db: float = 6.0
    resonance_median_floor_db: float = -40.0
    resonance_prominence_db: float = 12.0
    lossy_shelf_drop_db: float = 20.0

    # Masking severity splits and energy floor.
    severity_high: float = 0.6
    severity_moderate: float = 0.3
    severity_low: float = 0.1
    masking_floor_db: float = 40.0

    # FFT / frame sizes for the spectral, octave-band, and problems passes.
    spectral_frame_size: int = 2048
    spectral_hop_size: int = 1024
    octave_frame_size: int = 4096
    octave_hop_size: int = 2048
    flatness_frame_size: int = 4096
    spectrum_frame_size: int = 8192

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
        clipping_threshold=_get_env_float("PHANTOM_CLIPPING_THRESHOLD", 1.0),
        dc_offset_threshold=_get_env_float("PHANTOM_DC_OFFSET_THRESHOLD", 5e-4),
        isp_overshoot_threshold_db=_get_env_float("PHANTOM_ISP_OVERSHOOT_DB", 0.5),
        isp_severe_dbtp=_get_env_float("PHANTOM_ISP_SEVERE_DBTP", -1.0),
        dynamic_spread_min_db=_get_env_float("PHANTOM_DYNAMIC_SPREAD_MIN_DB", 10.0),
        noise_floor_moderate_db=_get_env_float(
            "PHANTOM_NOISE_FLOOR_MODERATE_DB", -50.0
        ),
        noise_floor_minor_db=_get_env_float("PHANTOM_NOISE_FLOOR_MINOR_DB", -60.0),
        snr_professional_db=_get_env_float("PHANTOM_SNR_PROFESSIONAL_DB", 60.0),
        snr_poor_db=_get_env_float("PHANTOM_SNR_POOR_DB", 50.0),
        spectral_flatness_min=_get_env_float("PHANTOM_SPECTRAL_FLATNESS_MIN", 0.01),
        band_excess_threshold_db=_get_env_float(
            "PHANTOM_BAND_EXCESS_THRESHOLD_DB", 6.0
        ),
        resonance_median_floor_db=_get_env_float(
            "PHANTOM_RESONANCE_MEDIAN_FLOOR_DB", -40.0
        ),
        resonance_prominence_db=_get_env_int("PHANTOM_RESONANCE_PROMINENCE_DB", 12),
        lossy_shelf_drop_db=_get_env_float("PHANTOM_LOSSY_SHELF_DROP_DB", 20.0),
        severity_high=_get_env_float("PHANTOM_MASKING_SEVERITY_HIGH", 0.6),
        severity_moderate=_get_env_float("PHANTOM_MASKING_SEVERITY_MODERATE", 0.3),
        severity_low=_get_env_float("PHANTOM_MASKING_SEVERITY_LOW", 0.1),
        masking_floor_db=_get_env_float("PHANTOM_MASKING_FLOOR_DB", 40.0),
        spectral_frame_size=_get_env_int("PHANTOM_SPECTRAL_FRAME_SIZE", 2048),
        spectral_hop_size=_get_env_int("PHANTOM_SPECTRAL_HOP_SIZE", 1024),
        octave_frame_size=_get_env_int("PHANTOM_OCTAVE_FRAME_SIZE", 4096),
        octave_hop_size=_get_env_int("PHANTOM_OCTAVE_HOP_SIZE", 2048),
        flatness_frame_size=_get_env_int("PHANTOM_FLATNESS_FRAME_SIZE", 4096),
        spectrum_frame_size=_get_env_int("PHANTOM_SPECTRUM_FRAME_SIZE", 8192),
    )
