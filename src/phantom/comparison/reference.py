"""Reference-based comparison: compare audio against a reference WAV file."""

from __future__ import annotations

from phantom.audio import AudioData
from phantom.exceptions import AnalysisError
from phantom._rounding import round_ratio
from phantom._utils import is_near_silent
from phantom.spectral import analyze_spectrum
from phantom.loudness import analyze_loudness
from phantom.dynamics import analyze_dynamics
from phantom.stereo import analyze_stereo

from phantom.comparison._common import (
    DeviationResult,
    DynamicsReferenceComparisonSection,
    LoudnessReferenceComparisonSection,
    ReferenceComparisonResult,
    StereoReferenceComparisonSection,
    _normalize_band_energies,
    _rate_deviation_ref,
    _unmeasurable_deviation,
)


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

    if is_near_silent(mono) or is_near_silent(ref_mono):
        return ReferenceComparisonResult()

    try:
        spectrum_a = analyze_spectrum(audio)
        spectrum_b = analyze_spectrum(ref_audio)
        loudness_a = analyze_loudness(audio)
        loudness_b = analyze_loudness(ref_audio)
        dynamics_a = analyze_dynamics(audio)
        dynamics_b = analyze_dynamics(ref_audio)
        stereo_a = analyze_stereo(audio)
        stereo_b = analyze_stereo(ref_audio)

        # Loudness
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
                    freq_result[band_key] = _unmeasurable_deviation("reference")
        else:
            band_keys = (bands_a or bands_b or {}).keys()
            for band_key in band_keys:
                freq_result[band_key] = _unmeasurable_deviation("reference")

        # Dynamics
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

        # Stereo
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
