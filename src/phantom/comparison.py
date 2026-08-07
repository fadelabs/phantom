"""Reference comparison analysis: profile, reference, and matching."""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
from pydantic import BaseModel, field_validator

from phantom._rounding import round_db, round_hz, round_ratio
from phantom._utils import (
    validate_input_path,
    validate_output_path,
    wrap_errors,
)
from phantom.audio import AudioData, load_audio

# Re-exported for backward compatibility: existing callers/tests import
# ``_cached_analysis`` from this module (see tests/test_comparison.py). The
# canonical definition now lives in phantom._cache (P-01).
from phantom._cache import _cached_analysis
from phantom.exceptions import AnalysisError, AudioLoadError, DependencyMissingError
from phantom.facade import ANALYSIS_TYPES
from phantom.loudness import analyze_loudness
from phantom._profiles import ReferenceProfile
from phantom.spectral import analyze_spectrum

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Deviation classification thresholds (inclusive upper bounds):
#   <= ON_TARGET  -> "on_target"
#   <= SLIGHT     -> "slightly_above/below"  (boundary 3.0 dB is "slight")
#   <= MODERATE   -> "above/below_target"    (boundary 6.0 dB is "moderate")
#   >  MODERATE   -> "significantly_above/below"
_THRESHOLD_ON_TARGET = 1.0
_THRESHOLD_SLIGHT = 3.0
_THRESHOLD_MODERATE = 6.0

_WIDTH_RANGES: dict[str, tuple[float, float]] = {
    "narrow": (0.0, 0.3),
    "moderate": (0.3, 0.7),
    "wide": (0.7, 1.2),
}

_BASS_MONO_THRESHOLD = 0.95


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class DeviationResult(BaseModel):
    """Deviation of a measured value from a target or reference."""

    value: Optional[float] = None
    target: Optional[float] = None
    reference: Optional[float] = None
    deviation: Optional[float] = None
    rating: str = "unmeasurable"


class RangeDeviationResult(BaseModel):
    """Deviation of a measured value from a target range."""

    value: Optional[float] = None
    target_range: Optional[list[float]] = None
    deviation: Optional[float] = None
    rating: str = "unmeasurable"

    @field_validator("target_range", mode="before")
    @classmethod
    def _round_range(cls, v):
        if v is None:
            return v
        return [round(x, 2) for x in v]


class MonoBelowResult(BaseModel):
    """Result of mono-below frequency check."""

    mono_below_hz: float
    bass_correlation: float
    has_stereo_bass: bool
    rating: str

    @field_validator("mono_below_hz", mode="before")
    @classmethod
    def _round_hz(cls, v):
        return round_hz(v)

    @field_validator("bass_correlation", mode="before")
    @classmethod
    def _round_corr(cls, v):
        return round_ratio(v)


class LoudnessProfileComparisonSection(BaseModel):
    integrated_lufs: RangeDeviationResult
    true_peak_dbtp: DeviationResult


class DynamicsComparisonSection(BaseModel):
    crest_factor_db: RangeDeviationResult | DeviationResult


class StereoProfileComparisonSection(BaseModel):
    width: RangeDeviationResult
    mono_below: MonoBelowResult


class LoudnessReferenceComparisonSection(BaseModel):
    integrated_lufs: DeviationResult
    true_peak_dbtp: DeviationResult
    loudness_range_lu: DeviationResult


class DynamicsReferenceComparisonSection(BaseModel):
    rms_dbfs: DeviationResult
    crest_factor_db: DeviationResult
    dynamic_range_db: DeviationResult


class StereoReferenceComparisonSection(BaseModel):
    correlation: DeviationResult
    stereo_width: DeviationResult


class MetricDiff(BaseModel):
    before: Optional[float] = None
    after: Optional[float] = None
    change: Optional[float] = None

    @field_validator("before", "after", "change", mode="before")
    @classmethod
    def _round(cls, v):
        return round_db(v)


class MatchAdjustments(BaseModel):
    integrated_lufs: MetricDiff
    true_peak_dbtp: MetricDiff
    spectral_change_db: dict[str, MetricDiff]


class ProfileComparisonResult(BaseModel):
    loudness: Optional[LoudnessProfileComparisonSection] = None
    frequency: Optional[dict[str, DeviationResult]] = None
    dynamics: Optional[DynamicsComparisonSection] = None
    stereo: Optional[StereoProfileComparisonSection] = None


class ReferenceComparisonResult(BaseModel):
    loudness: Optional[LoudnessReferenceComparisonSection] = None
    frequency: Optional[dict[str, DeviationResult]] = None
    dynamics: Optional[DynamicsReferenceComparisonSection] = None
    stereo: Optional[StereoReferenceComparisonSection] = None


class MatchResult(BaseModel):
    output_path: str
    adjustments: MatchAdjustments


# ---------------------------------------------------------------------------
# Private Helpers
# ---------------------------------------------------------------------------


def _classify_deviation(
    abs_dev: float,
    deviation: float,
    thresholds: tuple[float, float, float] | None = None,
) -> str:
    """Classify a deviation magnitude into a rating string.

    Boundary values are inclusive to the lower category (e.g., exactly 3.0 dB
    is classified as "slightly_above/below", not "above/below_target").
    """
    if thresholds is None:
        t_on, t_slight, t_mod = (
            _THRESHOLD_ON_TARGET,
            _THRESHOLD_SLIGHT,
            _THRESHOLD_MODERATE,
        )
    else:
        t_on, t_slight, t_mod = thresholds

    if abs_dev <= t_on:
        return "on_target"
    elif abs_dev <= t_slight:
        return "slightly_above" if deviation > 0 else "slightly_below"
    elif abs_dev <= t_mod:
        return "above_target" if deviation > 0 else "below_target"
    else:
        return "significantly_above" if deviation > 0 else "significantly_below"


def _rate_deviation(
    value: float,
    target: float,
    thresholds: tuple[float, float, float] | None = None,
    round_fn=round_db,
) -> DeviationResult:
    deviation = value - target
    rating = _classify_deviation(abs(deviation), deviation, thresholds)
    return DeviationResult(
        value=round_fn(value),
        target=round_fn(target),
        deviation=round_fn(deviation),
        rating=rating,
    )


def _rate_deviation_ref(
    value: float,
    reference: float,
    thresholds: tuple[float, float, float] | None = None,
    round_fn=round_db,
) -> DeviationResult:
    dev = _rate_deviation(value, reference, thresholds, round_fn=round_fn)
    return DeviationResult(
        value=dev.value,
        reference=dev.target,
        target=None,
        deviation=dev.deviation,
        rating=dev.rating,
    )


def _rate_range_deviation(
    value: float,
    target_range: tuple[float, float],
    thresholds: tuple[float, float, float] | None = None,
    round_fn=round_db,
) -> RangeDeviationResult:
    range_min, range_max = target_range

    if range_min <= value <= range_max:
        deviation = 0.0
        rating = "on_target"
    elif value < range_min:
        deviation = value - range_min
        rating = _classify_deviation(abs(deviation), deviation, thresholds)
    else:
        deviation = value - range_max
        rating = _classify_deviation(abs(deviation), deviation, thresholds)

    return RangeDeviationResult(
        value=round_fn(value),
        target_range=[range_min, range_max],
        deviation=round_fn(deviation),
        rating=rating,
    )


def _normalize_band_energies(band_db: dict[str, float]) -> dict[str, float]:
    if not band_db:
        return {}
    values = list(band_db.values())
    mean_db = float(np.mean(values))
    return {k: round(v - mean_db, 2) for k, v in band_db.items()}


def _check_mono_below(audio, cutoff_hz: float) -> MonoBelowResult:
    from scipy.signal import butter, sosfilt

    if audio.num_channels == 1:
        return MonoBelowResult(
            mono_below_hz=cutoff_hz,
            bass_correlation=1.0,
            has_stereo_bass=False,
            rating="on_target",
        )

    nyquist = audio.sample_rate / 2.0
    if cutoff_hz >= nyquist:
        bass_left = audio.left
        bass_right = audio.right
    else:
        sos = butter(4, cutoff_hz / nyquist, btype="low", output="sos")
        bass_left = sosfilt(sos, audio.left)
        bass_right = sosfilt(sos, audio.right)

    rms_left = float(np.sqrt(np.mean(bass_left**2)))
    rms_right = float(np.sqrt(np.mean(bass_right**2)))
    if rms_left < 1e-8 or rms_right < 1e-8:
        return MonoBelowResult(
            mono_below_hz=cutoff_hz,
            bass_correlation=1.0,
            has_stereo_bass=False,
            rating="on_target",
        )

    with np.errstate(invalid="ignore"):
        corr = np.corrcoef(bass_left, bass_right)[0, 1]
    if np.isnan(corr):
        corr = 1.0
    correlation = float(corr)

    has_stereo_bass = correlation < _BASS_MONO_THRESHOLD
    rating = "below_target" if has_stereo_bass else "on_target"

    return MonoBelowResult(
        mono_below_hz=cutoff_hz,
        bass_correlation=correlation,
        has_stereo_bass=has_stereo_bass,
        rating=rating,
    )


def _map_width_to_range(descriptor: str) -> tuple[float, float]:
    return _WIDTH_RANGES.get(descriptor, (0.0, 2.0))


def _unmeasurable_deviation() -> DeviationResult:
    return DeviationResult(rating="unmeasurable")


# ---------------------------------------------------------------------------
# Public Functions
# ---------------------------------------------------------------------------


def _silent_comparison_result() -> ProfileComparisonResult:
    return ProfileComparisonResult()


@wrap_errors("Comparison analysis failed")
def compare_to_profile(
    audio: AudioData, profile: ReferenceProfile
) -> ProfileComparisonResult:
    """Compare audio against a genre reference profile.

    Analyzes the audio across four dimensions (loudness, frequency, dynamics,
    stereo) and computes per-dimension deviations from the profile's targets.

    Args:
        audio: AudioData object to analyze.
        profile: ReferenceProfile with genre targets.

    Returns:
        ProfileComparisonResult with loudness, frequency, dynamics, stereo sections.

    Raises:
        AnalysisError: If audio has 0 samples or analysis fails.
    """
    mono = audio.mono

    if len(mono) == 0:
        raise AnalysisError("Comparison analysis failed: audio has 0 samples")

    if audio.is_near_silent:
        return _silent_comparison_result()

    # Cache key AND analyzer come from the same registry row, so they cannot
    # diverge (a renamed analyzer goes through the registry's fn, not the
    # module-level import below).
    spectral_spec = ANALYSIS_TYPES["spectral"]
    loudness_spec = ANALYSIS_TYPES["loudness"]
    dynamics_spec = ANALYSIS_TYPES["dynamics"]
    stereo_spec = ANALYSIS_TYPES["stereo"]
    spectrum = _cached_analysis(audio, spectral_spec.cache_key, spectral_spec.fn)
    loudness = _cached_analysis(audio, loudness_spec.cache_key, loudness_spec.fn)
    dynamics = _cached_analysis(audio, dynamics_spec.cache_key, dynamics_spec.fn)
    stereo = _cached_analysis(audio, stereo_spec.cache_key, stereo_spec.fn)

    # Loudness
    if loudness.integrated_lufs is not None:
        integrated_lufs_dev = _rate_range_deviation(
            loudness.integrated_lufs, profile.loudness.lufs_range
        )
    else:
        integrated_lufs_dev = RangeDeviationResult(rating="unmeasurable")

    if loudness.true_peak_dbtp is not None:
        true_peak_dev = _rate_deviation(
            loudness.true_peak_dbtp, profile.loudness.true_peak_max_dbtp
        )
    else:
        true_peak_dev = _unmeasurable_deviation()

    loudness_section = LoudnessProfileComparisonSection(
        integrated_lufs=integrated_lufs_dev, true_peak_dbtp=true_peak_dev
    )

    # Frequency
    freq_result: dict[str, DeviationResult] = {}
    if spectrum.octave_band_energy_db is not None:
        measured_norm = _normalize_band_energies(spectrum.octave_band_energy_db)
        for band_key, measured_val in measured_norm.items():
            target_val = profile.frequency.bands.get(band_key, 0.0)
            freq_result[band_key] = _rate_deviation(measured_val, target_val)
        for band_key in profile.frequency.bands:
            if band_key not in freq_result:
                freq_result[band_key] = _unmeasurable_deviation()
    else:
        for band_key in profile.frequency.bands:
            freq_result[band_key] = _unmeasurable_deviation()

    # Dynamics
    if dynamics.crest_factor_db is not None:
        crest_dev = _rate_range_deviation(
            dynamics.crest_factor_db, profile.loudness.crest_factor_range
        )
    else:
        crest_dev = RangeDeviationResult(rating="unmeasurable")

    dynamics_section = DynamicsComparisonSection(crest_factor_db=crest_dev)

    # Stereo
    width_range = _map_width_to_range(profile.stereo.width)
    if stereo.stereo_width is not None:
        width_dev = _rate_range_deviation(
            stereo.stereo_width, width_range, round_fn=round_ratio
        )
    else:
        width_dev = RangeDeviationResult(rating="unmeasurable")

    mono_below_result = _check_mono_below(audio, profile.stereo.mono_below_hz)

    stereo_section = StereoProfileComparisonSection(
        width=width_dev, mono_below=mono_below_result
    )

    return ProfileComparisonResult(
        loudness=loudness_section,
        frequency=freq_result,
        dynamics=dynamics_section,
        stereo=stereo_section,
    )


@wrap_errors("Comparison analysis failed")
def compare_to_reference(
    audio: AudioData, ref_audio: AudioData
) -> ReferenceComparisonResult:
    """Compare audio against a reference WAV file.

    Analyzes both audio files and computes per-dimension deviations between
    them. Frequency bands are normalized to relative values before comparison.

    Args:
        audio: AudioData object to analyze (the track being evaluated).
        ref_audio: AudioData object for the reference track.

    Returns:
        ReferenceComparisonResult with loudness, frequency, dynamics, stereo sections.

    Raises:
        AnalysisError: If either audio has 0 samples or analysis fails.
    """
    mono = audio.mono
    ref_mono = ref_audio.mono

    if len(mono) == 0 or len(ref_mono) == 0:
        raise AnalysisError("Comparison analysis failed: audio has 0 samples")

    if audio.is_near_silent or ref_audio.is_near_silent:
        return ReferenceComparisonResult()

    # Cache key AND analyzer come from the same registry row (see the
    # compare_to_profile twin above).
    spectral_spec = ANALYSIS_TYPES["spectral"]
    loudness_spec = ANALYSIS_TYPES["loudness"]
    dynamics_spec = ANALYSIS_TYPES["dynamics"]
    stereo_spec = ANALYSIS_TYPES["stereo"]
    spectrum_a = _cached_analysis(audio, spectral_spec.cache_key, spectral_spec.fn)
    spectrum_b = _cached_analysis(ref_audio, spectral_spec.cache_key, spectral_spec.fn)
    loudness_a = _cached_analysis(audio, loudness_spec.cache_key, loudness_spec.fn)
    loudness_b = _cached_analysis(ref_audio, loudness_spec.cache_key, loudness_spec.fn)
    dynamics_a = _cached_analysis(audio, dynamics_spec.cache_key, dynamics_spec.fn)
    dynamics_b = _cached_analysis(ref_audio, dynamics_spec.cache_key, dynamics_spec.fn)
    stereo_a = _cached_analysis(audio, stereo_spec.cache_key, stereo_spec.fn)
    stereo_b = _cached_analysis(ref_audio, stereo_spec.cache_key, stereo_spec.fn)

    # Loudness
    loudness_devs = {}
    for key in ("integrated_lufs", "true_peak_dbtp", "loudness_range_lu"):
        val_a = getattr(loudness_a, key)
        val_b = getattr(loudness_b, key)
        if val_a is not None and val_b is not None:
            loudness_devs[key] = _rate_deviation_ref(val_a, val_b)
        else:
            loudness_devs[key] = _unmeasurable_deviation()

    loudness_section = LoudnessReferenceComparisonSection(
        integrated_lufs=loudness_devs["integrated_lufs"],
        true_peak_dbtp=loudness_devs["true_peak_dbtp"],
        loudness_range_lu=loudness_devs["loudness_range_lu"],
    )

    # Frequency (normalized)
    freq_result: dict[str, DeviationResult] = {}
    bands_a = spectrum_a.octave_band_energy_db
    bands_b = spectrum_b.octave_band_energy_db

    if bands_a is not None and bands_b is not None:
        norm_a = _normalize_band_energies(bands_a)
        norm_b = _normalize_band_energies(bands_b)
        all_bands = sorted(set(norm_a.keys()) | set(norm_b.keys()))
        for band_key in all_bands:
            if band_key in norm_a and band_key in norm_b:
                freq_result[band_key] = _rate_deviation_ref(
                    norm_a[band_key], norm_b[band_key]
                )
            else:
                freq_result[band_key] = _unmeasurable_deviation()
    else:
        band_keys = (bands_a or bands_b or {}).keys()
        for band_key in band_keys:
            freq_result[band_key] = _unmeasurable_deviation()

    # Dynamics
    dynamics_devs = {}
    for key in ("rms_dbfs", "crest_factor_db", "dynamic_range_db"):
        val_a = getattr(dynamics_a, key)
        val_b = getattr(dynamics_b, key)
        if val_a is not None and val_b is not None:
            dynamics_devs[key] = _rate_deviation_ref(val_a, val_b)
        else:
            dynamics_devs[key] = _unmeasurable_deviation()

    dynamics_section = DynamicsReferenceComparisonSection(
        rms_dbfs=dynamics_devs["rms_dbfs"],
        crest_factor_db=dynamics_devs["crest_factor_db"],
        dynamic_range_db=dynamics_devs["dynamic_range_db"],
    )

    # Stereo
    stereo_devs = {}
    for key in ("correlation", "stereo_width"):
        val_a = getattr(stereo_a, key)
        val_b = getattr(stereo_b, key)
        if val_a is not None and val_b is not None:
            stereo_devs[key] = _rate_deviation_ref(val_a, val_b, round_fn=round_ratio)
        else:
            stereo_devs[key] = _unmeasurable_deviation()

    stereo_section = StereoReferenceComparisonSection(
        correlation=stereo_devs["correlation"],
        stereo_width=stereo_devs["stereo_width"],
    )

    return ReferenceComparisonResult(
        loudness=loudness_section,
        frequency=freq_result,
        dynamics=dynamics_section,
        stereo=stereo_section,
    )


@wrap_errors("Reference matching failed")
def match_to_reference(
    target_path: str,
    reference_path: str,
    output_path: str,
) -> MatchResult:
    """Match audio to a reference track using Matchering.

    Matchering is an optional GPLv3 dependency. If not installed, a
    DependencyMissingError is raised with install instructions.

    Args:
        target_path: Path to the target WAV file to be processed.
        reference_path: Path to the reference WAV file to match against.
        output_path: Path where the processed output WAV will be written.

    Returns:
        MatchResult with output_path and adjustments.

    Raises:
        DependencyMissingError: If Matchering is not installed.
        AudioLoadError: If target or reference file does not exist.
        AnalysisError: If processing or analysis fails.
    """
    output_path = validate_output_path(output_path)
    target_path = validate_input_path(target_path)
    reference_path = validate_input_path(reference_path)

    # GPL isolation: matchering imported inside function body only
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            import matchering as mg
    except ImportError:
        raise DependencyMissingError(
            package="Matchering",
            extra="matching",
            detail="Matchering provides automated spectral/loudness/width matching.",
        )

    if not os.path.isfile(target_path):
        raise AudioLoadError(f"Target file not found: {os.path.basename(target_path)}")
    if not os.path.isfile(reference_path):
        raise AudioLoadError(
            f"Reference file not found: {os.path.basename(reference_path)}"
        )

    # Same-file guard (Finding 3): never let the output clobber an input. Paths
    # are already resolved (validate_*); compare the final realpaths.
    real_target = os.path.realpath(target_path)
    real_reference = os.path.realpath(reference_path)
    if output_path == real_target or output_path == real_reference:
        raise AnalysisError(
            "Output path must differ from the target and reference files."
        )

    # Advisory lock prevents concurrent writes; flock auto-releases on crash.
    # Open the lock with O_NOFOLLOW so a symlink pre-placed at <output>.lock
    # cannot redirect the lock file outside the validated output directory.
    import fcntl

    lock_path = output_path + ".lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    created_output = False
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise AnalysisError(
                f"Output path is locked by another process: {os.path.basename(output_path)}. "
                "Try again shortly or choose a different output path."
            )

        # Atomically reserve the output name (Finding 3). O_CREAT|O_EXCL fails
        # if it already exists, closing the check-then-write TOCTOU of a prior
        # os.path.exists() guard; O_NOFOLLOW rejects a final-component symlink.
        try:
            out_fd = os.open(
                output_path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )
        except FileExistsError:
            raise AnalysisError(
                f"Output file already exists: {os.path.basename(output_path)}. "
                "Choose a different output path to avoid overwriting."
            )
        os.close(out_fd)
        created_output = True

        before_audio = load_audio(target_path)
        before_loudness = analyze_loudness(before_audio)
        before_spectrum = analyze_spectrum(before_audio)

        mg.process(
            target=target_path,
            reference=reference_path,
            results=[mg.pcm24(output_path)],
        )

        after_audio = load_audio(output_path)
        after_loudness = analyze_loudness(after_audio)
        after_spectrum = analyze_spectrum(after_audio)

        def _diff_metric(before_val, after_val) -> MetricDiff:
            if before_val is None or after_val is None:
                return MetricDiff(before=before_val, after=after_val, change=None)
            return MetricDiff(
                before=before_val, after=after_val, change=after_val - before_val
            )

        integrated_lufs_diff = _diff_metric(
            before_loudness.integrated_lufs, after_loudness.integrated_lufs
        )
        true_peak_diff = _diff_metric(
            before_loudness.true_peak_dbtp, after_loudness.true_peak_dbtp
        )

        before_bands = before_spectrum.octave_band_energy_db or {}
        after_bands = after_spectrum.octave_band_energy_db or {}
        all_bands = set(before_bands.keys()) | set(after_bands.keys())
        spectral_change: dict[str, MetricDiff] = {}
        for band in sorted(all_bands):
            spectral_change[band] = _diff_metric(
                before_bands.get(band), after_bands.get(band)
            )

        adjustments = MatchAdjustments(
            integrated_lufs=integrated_lufs_diff,
            true_peak_dbtp=true_peak_diff,
            spectral_change_db=spectral_change,
        )

        return MatchResult(output_path=output_path, adjustments=adjustments)

    except BaseException:
        # Remove the empty reserved stub if we created it but did not finish,
        # so a failed run does not leave a stale file that blocks the next one.
        if created_output:
            try:
                os.unlink(output_path)
            except OSError:
                pass
        raise
    finally:
        os.close(lock_fd)
        try:
            os.unlink(lock_path)
        except OSError:
            pass


__all__ = [
    "compare_to_profile",
    "compare_to_reference",
    "match_to_reference",
    "DeviationResult",
    "RangeDeviationResult",
    "MonoBelowResult",
    "ProfileComparisonResult",
    "ReferenceComparisonResult",
    "MatchResult",
    "MatchAdjustments",
    "MetricDiff",
    "LoudnessProfileComparisonSection",
    "DynamicsComparisonSection",
    "StereoProfileComparisonSection",
    "LoudnessReferenceComparisonSection",
    "DynamicsReferenceComparisonSection",
    "StereoReferenceComparisonSection",
]
