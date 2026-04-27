"""Reference comparison analysis functions.

Provides compare_to_profile() for comparing audio against a genre reference
profile and compare_to_reference() for comparing two WAV files directly.
Both functions return per-dimension deviation reports with significance ratings.

No overall match score is computed (per D-03).
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
from pydantic import BaseModel, field_validator
from scipy.signal import butter, sosfilt

from phantom.audio import AudioData, load_audio
from phantom.exceptions import AnalysisError, AudioLoadError, DependencyMissingError
from phantom._profiles import ReferenceProfile
from phantom._rounding import round_db, round_hz, round_ratio
from phantom._utils import is_near_silent, validate_input_path, validate_output_path
from phantom.spectral import analyze_spectrum
from phantom.loudness import analyze_loudness
from phantom.dynamics import analyze_dynamics
from phantom.stereo import analyze_stereo

# ---------------------------------------------------------------------------
# Module-level constants (per D-02)
# ---------------------------------------------------------------------------

# Universal deviation thresholds in dB (per D-02)
_THRESHOLD_ON_TARGET = 1.0  # within +/- 1 dB
_THRESHOLD_SLIGHT = 3.0  # 1-3 dB
_THRESHOLD_MODERATE = 6.0  # 3-6 dB
# > 6 dB = significant

# Stereo width descriptor-to-range mapping (per D-11)
_WIDTH_RANGES: dict[str, tuple[float, float]] = {
    "narrow": (0.0, 0.3),
    "moderate": (0.3, 0.7),
    "wide": (0.7, 1.2),
}

# Bass correlation threshold for "effectively mono" (per D-13)
_BASS_MONO_THRESHOLD = 0.95


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class DeviationResult(BaseModel):
    """Deviation of a measured value from a target or reference.

    Rounding is the caller's responsibility -- pass pre-rounded values or use
    ``_rate_deviation(round_fn=...)`` / ``_rate_deviation_ref(round_fn=...)``.
    """

    value: Optional[float] = None
    target: Optional[float] = None
    reference: Optional[float] = None
    deviation: Optional[float] = None
    rating: str = "unmeasurable"


class RangeDeviationResult(BaseModel):
    """Deviation of a measured value from a target range.

    Rounding is the caller's responsibility -- pass pre-rounded values or use
    ``_rate_range_deviation(round_fn=...)``.
    """

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


# -- Typed comparison section sub-models --


class LoudnessProfileComparisonSection(BaseModel):
    """Typed loudness section for profile comparison."""

    integrated_lufs: RangeDeviationResult
    true_peak_dbtp: DeviationResult


class DynamicsComparisonSection(BaseModel):
    """Typed dynamics section for profile/reference comparison."""

    crest_factor_db: RangeDeviationResult | DeviationResult


class StereoProfileComparisonSection(BaseModel):
    """Typed stereo section for profile comparison."""

    width: RangeDeviationResult
    mono_below: MonoBelowResult


class LoudnessReferenceComparisonSection(BaseModel):
    """Typed loudness section for reference comparison."""

    integrated_lufs: DeviationResult
    true_peak_dbtp: DeviationResult
    loudness_range_lu: DeviationResult


class DynamicsReferenceComparisonSection(BaseModel):
    """Typed dynamics section for reference comparison."""

    rms_dbfs: DeviationResult
    crest_factor_db: DeviationResult
    dynamic_range_db: DeviationResult


class StereoReferenceComparisonSection(BaseModel):
    """Typed stereo section for reference comparison."""

    correlation: DeviationResult
    stereo_width: DeviationResult


class MetricDiff(BaseModel):
    """Before/after/change for a single metric."""

    before: Optional[float] = None
    after: Optional[float] = None
    change: Optional[float] = None

    @field_validator("before", "after", "change", mode="before")
    @classmethod
    def _round(cls, v):
        return round_db(v)


class MatchAdjustments(BaseModel):
    """Typed adjustments from Matchering reference matching."""

    integrated_lufs: MetricDiff
    true_peak_dbtp: MetricDiff
    spectral_change_db: dict[str, MetricDiff]


class ProfileComparisonResult(BaseModel):
    """Result of comparing audio to a genre reference profile."""

    loudness: Optional[LoudnessProfileComparisonSection] = None
    frequency: Optional[dict[str, DeviationResult]] = None
    dynamics: Optional[DynamicsComparisonSection] = None
    stereo: Optional[StereoProfileComparisonSection] = None


class ReferenceComparisonResult(BaseModel):
    """Result of comparing audio to a reference WAV file."""

    loudness: Optional[LoudnessReferenceComparisonSection] = None
    frequency: Optional[dict[str, DeviationResult]] = None
    dynamics: Optional[DynamicsReferenceComparisonSection] = None
    stereo: Optional[StereoReferenceComparisonSection] = None


class MatchResult(BaseModel):
    """Result of Matchering reference matching."""

    output_path: str
    adjustments: MatchAdjustments


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _rate_deviation(
    value: float,
    target: float,
    thresholds: tuple[float, float, float] | None = None,
    round_fn=round_db,
) -> DeviationResult:
    """Classify deviation of a measured value from a target value.

    Args:
        value: Measured value.
        target: Target/reference value.
        thresholds: Optional (on_target, slight, moderate) thresholds.
            Defaults to (_THRESHOLD_ON_TARGET, _THRESHOLD_SLIGHT, _THRESHOLD_MODERATE).
        round_fn: Rounding function to apply (default: round_db for 2dp).
            Pass round_hz for Hz values, round_ratio for dimensionless ratios.

    Returns:
        DeviationResult with value, target, deviation, rating.
    """
    if thresholds is None:
        t_on, t_slight, t_mod = (
            _THRESHOLD_ON_TARGET,
            _THRESHOLD_SLIGHT,
            _THRESHOLD_MODERATE,
        )
    else:
        t_on, t_slight, t_mod = thresholds

    deviation = value - target
    abs_dev = abs(deviation)

    if abs_dev <= t_on:
        rating = "on_target"
    elif abs_dev <= t_slight:
        rating = "slightly_above" if deviation > 0 else "slightly_below"
    elif abs_dev <= t_mod:
        rating = "above_target" if deviation > 0 else "below_target"
    else:
        rating = "significantly_above" if deviation > 0 else "significantly_below"

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
    """Like _rate_deviation but uses 'reference' field instead of 'target'.

    Used by compare_to_reference for WAV-to-WAV comparison.
    """
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
    """Classify deviation of a measured value from a target range.

    Args:
        value: Measured value.
        target_range: (min, max) acceptable range.
        thresholds: Optional (on_target, slight, moderate) thresholds.
        round_fn: Rounding function to apply (default: round_db for 2dp).

    Returns:
        RangeDeviationResult with value, target_range, deviation, rating.
    """
    range_min, range_max = target_range

    if range_min <= value <= range_max:
        deviation = 0.0
        rating = "on_target"
    elif value < range_min:
        deviation = value - range_min
        # Classify using same thresholds as _rate_deviation
        abs_dev = abs(deviation)
        if thresholds is None:
            t_on, t_slight, t_mod = (
                _THRESHOLD_ON_TARGET,
                _THRESHOLD_SLIGHT,
                _THRESHOLD_MODERATE,
            )
        else:
            t_on, t_slight, t_mod = thresholds

        if abs_dev <= t_on:
            rating = "on_target"
        elif abs_dev <= t_slight:
            rating = "slightly_below"
        elif abs_dev <= t_mod:
            rating = "below_target"
        else:
            rating = "significantly_below"
    else:
        deviation = value - range_max
        abs_dev = abs(deviation)
        if thresholds is None:
            t_on, t_slight, t_mod = (
                _THRESHOLD_ON_TARGET,
                _THRESHOLD_SLIGHT,
                _THRESHOLD_MODERATE,
            )
        else:
            t_on, t_slight, t_mod = thresholds

        if abs_dev <= t_on:
            rating = "on_target"
        elif abs_dev <= t_slight:
            rating = "slightly_above"
        elif abs_dev <= t_mod:
            rating = "above_target"
        else:
            rating = "significantly_above"

    return RangeDeviationResult(
        value=round_fn(value),
        target_range=[range_min, range_max],
        deviation=round_fn(deviation),
        rating=rating,
    )


def _normalize_band_energies(band_db: dict[str, float]) -> dict[str, float]:
    """Normalize octave band energies relative to their mean.

    Subtracts the mean dB value across all bands, producing relative offsets
    from the file's own average spectral shape (per D-06).

    Args:
        band_db: Dict mapping band labels to dB values.

    Returns:
        Dict with same keys, values as relative offsets from mean.
    """
    if not band_db:
        return {}

    values = list(band_db.values())
    mean_db = float(np.mean(values))

    return {k: round(v - mean_db, 2) for k, v in band_db.items()}


def _check_mono_below(audio: AudioData, cutoff_hz: float) -> MonoBelowResult:
    """Detect stereo content below a frequency cutoff.

    For mono audio, returns perfect correlation (no stereo bass possible).
    For stereo audio, applies a Butterworth low-pass filter and computes
    the correlation between filtered left and right channels.

    Args:
        audio: AudioData object (mono or stereo).
        cutoff_hz: Frequency cutoff in Hz.

    Returns:
        MonoBelowResult with mono_below_hz, bass_correlation, has_stereo_bass, rating.
    """
    # Mono audio: no stereo bass possible
    if audio.num_channels == 1:
        return MonoBelowResult(
            mono_below_hz=cutoff_hz,
            bass_correlation=1.0,
            has_stereo_bass=False,
            rating="on_target",
        )

    # Stereo audio: filter and correlate
    nyquist = audio.sample_rate / 2.0
    if cutoff_hz >= nyquist:
        # Cutoff at or above Nyquist -- use full signal
        bass_left = audio.left
        bass_right = audio.right
    else:
        sos = butter(4, cutoff_hz / nyquist, btype="low", output="sos")
        bass_left = sosfilt(sos, audio.left)
        bass_right = sosfilt(sos, audio.right)

    # Guard against near-silent bass
    rms_left = float(np.sqrt(np.mean(bass_left**2)))
    rms_right = float(np.sqrt(np.mean(bass_right**2)))
    if rms_left < 1e-8 or rms_right < 1e-8:
        return MonoBelowResult(
            mono_below_hz=cutoff_hz,
            bass_correlation=1.0,
            has_stereo_bass=False,
            rating="on_target",
        )

    # Compute correlation
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
    """Map a stereo width descriptor to a numeric range.

    Args:
        descriptor: One of "narrow", "moderate", "wide".

    Returns:
        Tuple of (min, max) width values.
    """
    return _WIDTH_RANGES.get(descriptor, (0.0, 2.0))


def _silent_comparison_result() -> ProfileComparisonResult:
    """Return a comparison result for near-silent audio.

    All dimension sections are set to None, matching the pattern used by
    other analysis modules.
    """
    return ProfileComparisonResult()


def _unmeasurable_deviation(key_name: str = "target") -> DeviationResult:
    """Return a deviation result for unmeasurable values (None from analysis).

    Args:
        key_name: "target" for profile comparison, "reference" for WAV comparison.
    """
    return DeviationResult(rating="unmeasurable")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compare_to_profile(
    audio: AudioData, profile: ReferenceProfile
) -> ProfileComparisonResult:
    """Compare audio against a genre reference profile.

    Analyzes the audio across four dimensions (loudness, frequency, dynamics,
    stereo) and computes per-dimension deviations from the profile's targets.
    Each deviation includes a raw numeric value, target/range, and a
    significance rating string.

    No overall match score is computed (per D-03).

    Args:
        audio: AudioData object to analyze.
        profile: ReferenceProfile with genre targets.

    Returns:
        ProfileComparisonResult with loudness, frequency, dynamics, stereo sections.
        Each section contains per-metric deviation dicts.

    Raises:
        AnalysisError: If audio has 0 samples or analysis fails.
    """
    mono = audio.mono

    # Empty samples guard
    if len(mono) == 0:
        raise AnalysisError("Comparison analysis failed: audio has 0 samples")

    # Near-silence guard
    if is_near_silent(mono):
        return _silent_comparison_result()

    try:
        # Run all analysis functions
        spectrum = analyze_spectrum(audio)
        loudness = analyze_loudness(audio)
        dynamics = analyze_dynamics(audio)
        stereo = analyze_stereo(audio)

        # -- Loudness section --
        if loudness.integrated_lufs is not None:
            integrated_lufs_dev = _rate_range_deviation(
                loudness.integrated_lufs,
                profile.loudness.lufs_range,
            )
        else:
            integrated_lufs_dev = RangeDeviationResult(rating="unmeasurable")

        if loudness.true_peak_dbtp is not None:
            true_peak_dev = _rate_deviation(
                loudness.true_peak_dbtp,
                profile.loudness.true_peak_max_dbtp,
            )
        else:
            true_peak_dev = _unmeasurable_deviation()

        loudness_section = LoudnessProfileComparisonSection(
            integrated_lufs=integrated_lufs_dev,
            true_peak_dbtp=true_peak_dev,
        )

        # -- Frequency section --
        freq_result: dict[str, DeviationResult] = {}

        if spectrum.octave_band_energy_db is not None:
            measured_norm = _normalize_band_energies(spectrum.octave_band_energy_db)
            for band_key, measured_val in measured_norm.items():
                target_val = profile.frequency.bands.get(band_key, 0.0)
                freq_result[band_key] = _rate_deviation(measured_val, target_val)
            # S-WR-05: Emit unmeasurable for profile bands not in measurement
            for band_key in profile.frequency.bands:
                if band_key not in freq_result:
                    freq_result[band_key] = _unmeasurable_deviation()
        else:
            # All bands unmeasurable
            for band_key in profile.frequency.bands:
                freq_result[band_key] = _unmeasurable_deviation()

        # -- Dynamics section --
        if dynamics.crest_factor_db is not None:
            crest_dev = _rate_range_deviation(
                dynamics.crest_factor_db,
                profile.loudness.crest_factor_range,
            )
        else:
            crest_dev = RangeDeviationResult(rating="unmeasurable")

        dynamics_section = DynamicsComparisonSection(
            crest_factor_db=crest_dev,
        )

        # -- Stereo section --
        width_range = _map_width_to_range(profile.stereo.width)
        if stereo.stereo_width is not None:
            width_dev = _rate_range_deviation(
                stereo.stereo_width,
                width_range,
                round_fn=round_ratio,
            )
        else:
            width_dev = RangeDeviationResult(rating="unmeasurable")

        mono_below_result = _check_mono_below(audio, profile.stereo.mono_below_hz)

        stereo_section = StereoProfileComparisonSection(
            width=width_dev,
            mono_below=mono_below_result,
        )

        return ProfileComparisonResult(
            loudness=loudness_section,
            frequency=freq_result,
            dynamics=dynamics_section,
            stereo=stereo_section,
        )

    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Comparison analysis failed: {exc}") from exc


def compare_to_reference(
    audio: AudioData, ref_audio: AudioData
) -> ReferenceComparisonResult:
    """Compare audio against a reference WAV file.

    Analyzes both audio files and computes per-dimension deviations between
    them. Frequency bands are normalized to relative values before comparison
    (per COMP-04/D-06).

    No overall match score is computed (per D-03).

    Args:
        audio: AudioData object to analyze (the track being evaluated).
        ref_audio: AudioData object for the reference track.

    Returns:
        ReferenceComparisonResult with loudness, frequency, dynamics, stereo sections.
        Each section contains per-metric deviation dicts using "reference" key.

    Raises:
        AnalysisError: If either audio has 0 samples or analysis fails.
    """
    mono = audio.mono
    ref_mono = ref_audio.mono

    # Empty samples guard
    if len(mono) == 0 or len(ref_mono) == 0:
        raise AnalysisError("Comparison analysis failed: audio has 0 samples")

    # Near-silence guard on either
    if is_near_silent(mono) or is_near_silent(ref_mono):
        return ReferenceComparisonResult()

    try:
        # Run all analysis on both files
        spectrum_a = analyze_spectrum(audio)
        spectrum_b = analyze_spectrum(ref_audio)
        loudness_a = analyze_loudness(audio)
        loudness_b = analyze_loudness(ref_audio)
        dynamics_a = analyze_dynamics(audio)
        dynamics_b = analyze_dynamics(ref_audio)
        stereo_a = analyze_stereo(audio)
        stereo_b = analyze_stereo(ref_audio)

        # -- Loudness section --
        loudness_devs = {}
        for key in ("integrated_lufs", "true_peak_dbtp", "loudness_range_lu"):
            val_a = getattr(loudness_a, key)
            val_b = getattr(loudness_b, key)
            if val_a is not None and val_b is not None:
                loudness_devs[key] = _rate_deviation_ref(val_a, val_b)
            else:
                loudness_devs[key] = _unmeasurable_deviation("reference")

        loudness_section = LoudnessReferenceComparisonSection(
            integrated_lufs=loudness_devs["integrated_lufs"],
            true_peak_dbtp=loudness_devs["true_peak_dbtp"],
            loudness_range_lu=loudness_devs["loudness_range_lu"],
        )

        # -- Frequency section (normalized, per COMP-04/D-06) --
        freq_result: dict[str, DeviationResult] = {}

        bands_a = spectrum_a.octave_band_energy_db
        bands_b = spectrum_b.octave_band_energy_db

        if bands_a is not None and bands_b is not None:
            norm_a = _normalize_band_energies(bands_a)
            norm_b = _normalize_band_energies(bands_b)
            # S-WR-06: Use union of bands from both files
            all_bands = sorted(set(norm_a.keys()) | set(norm_b.keys()))
            for band_key in all_bands:
                if band_key in norm_a and band_key in norm_b:
                    freq_result[band_key] = _rate_deviation_ref(
                        norm_a[band_key], norm_b[band_key]
                    )
                else:
                    freq_result[band_key] = _unmeasurable_deviation("reference")
        else:
            # Use keys from whichever is available, or default set
            band_keys = (bands_a or bands_b or {}).keys()
            for band_key in band_keys:
                freq_result[band_key] = _unmeasurable_deviation("reference")

        # -- Dynamics section --
        dynamics_devs = {}
        for key in ("rms_dbfs", "crest_factor_db", "dynamic_range_db"):
            val_a = getattr(dynamics_a, key)
            val_b = getattr(dynamics_b, key)
            if val_a is not None and val_b is not None:
                dynamics_devs[key] = _rate_deviation_ref(val_a, val_b)
            else:
                dynamics_devs[key] = _unmeasurable_deviation("reference")

        dynamics_section = DynamicsReferenceComparisonSection(
            rms_dbfs=dynamics_devs["rms_dbfs"],
            crest_factor_db=dynamics_devs["crest_factor_db"],
            dynamic_range_db=dynamics_devs["dynamic_range_db"],
        )

        # -- Stereo section --
        stereo_devs = {}
        for key in ("correlation", "stereo_width"):
            val_a = getattr(stereo_a, key)
            val_b = getattr(stereo_b, key)
            if val_a is not None and val_b is not None:
                stereo_devs[key] = _rate_deviation_ref(
                    val_a, val_b, round_fn=round_ratio
                )
            else:
                stereo_devs[key] = _unmeasurable_deviation("reference")

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

    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Comparison analysis failed: {exc}") from exc


def match_to_reference(
    target_path: str,
    reference_path: str,
    output_path: str,
) -> MatchResult:
    """Match audio to a reference track using Matchering.

    Runs Matchering to automatically adjust the target track's spectral balance,
    loudness, and stereo width to match the reference track. Produces a processed
    output WAV file and returns a summary of before/after measurement changes.

    Matchering is an optional dependency. If not installed, a
    DependencyMissingError is raised with install instructions.

    Args:
        target_path: Path to the target WAV file to be processed.
        reference_path: Path to the reference WAV file to match against.
        output_path: Path where the processed output WAV will be written.

    Returns:
        MatchResult with output_path and adjustments. The adjustments dict
        contains before/after measurement diffs for integrated_lufs,
        true_peak_dbtp, and per-band spectral changes.

    Raises:
        DependencyMissingError: If Matchering is not installed.
        PathSecurityError: If output_path is outside PHANTOM_OUTPUT_DIR (when set).
        FileNotFoundError: If target or reference file does not exist.
        AnalysisError: If Matchering processing or analysis fails.
    """
    # Step 0: Validate paths against security restrictions
    output_path = validate_output_path(output_path)
    target_path = validate_input_path(target_path)
    reference_path = validate_input_path(reference_path)

    # Step 1: Guard -- import matchering inside function body (not at module level)
    try:
        import matchering as mg  # noqa: F811
    except ImportError:
        raise DependencyMissingError(
            package="Matchering",
            extra="matching",
            detail="Matchering provides automated spectral/loudness/width matching.",
        )

    # Step 2: Validate file paths
    if not os.path.isfile(target_path):
        raise AudioLoadError(f"Target file not found: {os.path.basename(target_path)}")
    if not os.path.isfile(reference_path):
        raise AudioLoadError(
            f"Reference file not found: {os.path.basename(reference_path)}"
        )

    # X-WR-04: Prevent accidental overwrite of existing files
    if os.path.exists(output_path):
        raise AnalysisError(
            f"Output file already exists: {os.path.basename(output_path)}. "
            "Choose a different output path to avoid overwriting."
        )

    try:
        # Step 3: Before analysis -- capture pre-matching measurements
        before_audio = load_audio(target_path)
        before_loudness = analyze_loudness(before_audio)
        before_spectrum = analyze_spectrum(before_audio)

        # Step 4: Run Matchering
        mg.process(
            target=target_path,
            reference=reference_path,
            results=[mg.pcm24(output_path)],
        )

        # Step 5: After analysis -- capture post-matching measurements
        after_audio = load_audio(output_path)
        after_loudness = analyze_loudness(after_audio)
        after_spectrum = analyze_spectrum(after_audio)

        # Step 6: Build adjustment summary
        def _diff_metric(before_val, after_val) -> MetricDiff:
            """Compute before/after/change for a single metric."""
            if before_val is None or after_val is None:
                return MetricDiff(before=before_val, after=after_val, change=None)
            return MetricDiff(
                before=before_val,
                after=after_val,
                change=after_val - before_val,
            )

        integrated_lufs_diff = _diff_metric(
            before_loudness.integrated_lufs,
            after_loudness.integrated_lufs,
        )
        true_peak_diff = _diff_metric(
            before_loudness.true_peak_dbtp,
            after_loudness.true_peak_dbtp,
        )

        # Per-band spectral changes
        before_bands = before_spectrum.octave_band_energy_db or {}
        after_bands = after_spectrum.octave_band_energy_db or {}
        all_bands = set(before_bands.keys()) | set(after_bands.keys())
        spectral_change: dict[str, MetricDiff] = {}
        for band in sorted(all_bands):
            spectral_change[band] = _diff_metric(
                before_bands.get(band),
                after_bands.get(band),
            )

        adjustments = MatchAdjustments(
            integrated_lufs=integrated_lufs_diff,
            true_peak_dbtp=true_peak_diff,
            spectral_change_db=spectral_change,
        )

        # Step 7: Return result
        return MatchResult(
            output_path=output_path,
            adjustments=adjustments,
        )

    except DependencyMissingError:
        raise
    except FileNotFoundError:
        raise
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Reference matching failed: {exc}") from exc
