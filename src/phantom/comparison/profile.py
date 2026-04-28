"""Profile-based comparison: compare audio against a genre reference profile."""

from __future__ import annotations

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom._profiles import ReferenceProfile
from phantom._rounding import round_ratio
from phantom._utils import is_near_silent
from phantom.spectral import analyze_spectrum
from phantom.loudness import analyze_loudness
from phantom.dynamics import analyze_dynamics
from phantom.stereo import analyze_stereo

from phantom.comparison._common import (
    DeviationResult,
    DynamicsComparisonSection,
    LoudnessProfileComparisonSection,
    ProfileComparisonResult,
    RangeDeviationResult,
    StereoProfileComparisonSection,
    _check_mono_below,
    _map_width_to_range,
    _normalize_band_energies,
    _rate_deviation,
    _rate_range_deviation,
    _unmeasurable_deviation,
)


def _silent_comparison_result() -> ProfileComparisonResult:
    return ProfileComparisonResult()


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

    if is_near_silent(mono):
        return _silent_comparison_result()

    try:
        spectrum = analyze_spectrum(audio)
        loudness = analyze_loudness(audio)
        dynamics = analyze_dynamics(audio)
        stereo = analyze_stereo(audio)

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

    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Comparison analysis failed: {exc}") from exc
