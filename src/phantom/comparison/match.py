"""Matchering wrapper: match audio to a reference track (GPLv3 boundary)."""

from __future__ import annotations

import os

from phantom.audio import load_audio
from phantom.exceptions import AnalysisError, AudioLoadError, DependencyMissingError
from phantom._utils import validate_input_path, validate_output_path
from phantom.spectral import analyze_spectrum
from phantom.loudness import analyze_loudness

from phantom.comparison._common import MatchAdjustments, MatchResult, MetricDiff


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

    try:
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

    if os.path.exists(output_path):
        raise AnalysisError(
            f"Output file already exists: {os.path.basename(output_path)}. "
            "Choose a different output path to avoid overwriting."
        )

    try:
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

    except DependencyMissingError:
        raise
    except FileNotFoundError:
        raise
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Reference matching failed: {exc}") from exc
