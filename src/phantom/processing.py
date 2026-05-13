"""Corrective audio processing via Pedalboard.

Provides the Recipe system that maps detected audio problems to corrective
Pedalboard plugin chains, and apply_processing() for custom processing.

Pedalboard is an optional dependency. Functions raise DependencyMissingError
with install instructions if Pedalboard is not available.

Recipe chain order follows standard mixing signal chain: HPF first, then
notch filters, then parametric cuts, then shelf adjustments.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel

from phantom.exceptions import AnalysisError, DependencyMissingError
from phantom._utils import validate_input_path, validate_output_path
from phantom.audio import load_audio
from phantom.problems import ProblemsResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNFIXABLE_TYPES: frozenset[str] = frozenset(
    {"clipping", "inter_sample_peak", "noise_floor", "snr", "lossy_codec"}
)

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class FixComparison(BaseModel):
    """Comparison of a single problem type before and after processing."""

    problem_type: str
    before_severity: str
    after_severity: str | None  # None = resolved
    status: str  # "resolved", "improved", "unchanged", "worsened"


class FixResult(BaseModel):
    """Result of corrective audio processing."""

    output_path: str
    fixes_applied: list[str]
    before: ProblemsResult | None = None
    after: ProblemsResult | None = None
    improvements: list[FixComparison] = []
    regressions: list[FixComparison] = []


# ---------------------------------------------------------------------------
# Recipe dataclass
# ---------------------------------------------------------------------------


@dataclass
class Recipe:
    """A corrective processing chain for a specific problem type.

    Attributes:
        problem_type: The ProblemItem.type this recipe addresses.
        description: Human-readable description of the corrective action.
        build_chain: Callable that takes a ProblemItem.details dict and
            returns a list of Pedalboard plugin instances.
    """

    problem_type: str
    description: str
    build_chain: Callable[[dict], list]


# ---------------------------------------------------------------------------
# Recipe builder functions (private)
# ---------------------------------------------------------------------------


def _recipe_mud(details: dict) -> list:
    """Mud: HPF at 80Hz + low-shelf cut at 300Hz."""
    import pedalboard as pb

    return [
        pb.HighpassFilter(cutoff_frequency_hz=80),
        pb.LowShelfFilter(cutoff_frequency_hz=300, gain_db=-4.0, q=0.7),
    ]


def _recipe_harshness(details: dict) -> list:
    """Harshness: parametric cut at 3kHz."""
    import pedalboard as pb

    return [
        pb.PeakFilter(cutoff_frequency_hz=3000, gain_db=-4.0, q=1.5),
    ]


def _recipe_hum(details: dict) -> list:
    """Hum: deep notch at each detected harmonic frequency."""
    import pedalboard as pb

    frequencies = details.get("frequencies_hz", [60.0])
    return [
        pb.PeakFilter(cutoff_frequency_hz=freq, gain_db=-30.0, q=30.0)
        for freq in frequencies
    ]


def _recipe_sibilance(details: dict) -> list:
    """Sibilance: parametric cut at 7kHz."""
    import pedalboard as pb

    return [
        pb.PeakFilter(cutoff_frequency_hz=7000, gain_db=-5.0, q=0.7),
    ]


def _recipe_dc_offset(details: dict) -> list:
    """DC offset: subsonic HPF at 5Hz removes DC component."""
    import pedalboard as pb

    return [
        pb.HighpassFilter(cutoff_frequency_hz=5),
    ]


def _recipe_resonant_peak(details: dict) -> list:
    """Resonant peak: parametric cut at each detected resonance."""
    import pedalboard as pb

    resonances = details.get("resonances", [])
    return [
        pb.PeakFilter(
            cutoff_frequency_hz=r["frequency_hz"],
            gain_db=-6.0,
            q=r.get("q_factor", 10.0),
        )
        for r in resonances
    ]


# ---------------------------------------------------------------------------
# RECIPES mapping
# ---------------------------------------------------------------------------

RECIPES: dict[str, Recipe] = {
    "mud": Recipe("mud", "HPF + low-mid shelf cut", _recipe_mud),
    "harshness": Recipe("harshness", "Parametric cut at 2-4kHz", _recipe_harshness),
    "hum": Recipe("hum", "Notch filter at detected harmonics", _recipe_hum),
    "sibilance": Recipe("sibilance", "Parametric cut at 5-10kHz", _recipe_sibilance),
    "dc_offset": Recipe("dc_offset", "Subsonic HPF to remove DC", _recipe_dc_offset),
    "resonant_peak": Recipe(
        "resonant_peak",
        "Parametric cut at detected resonance",
        _recipe_resonant_peak,
    ),
}


# ---------------------------------------------------------------------------
# ALLOWED_OPERATIONS allowlist (T-23-01 mitigation)
# ---------------------------------------------------------------------------


def _build_allowed_operations() -> dict[str, type]:
    """Build the operations allowlist from pedalboard classes.

    Lazy-imports pedalboard so this dict is populated on first use,
    not at module import time.
    """
    import pedalboard as pb

    return {
        "HighpassFilter": pb.HighpassFilter,
        "LowpassFilter": pb.LowpassFilter,
        "PeakFilter": pb.PeakFilter,
        "HighShelfFilter": pb.HighShelfFilter,
        "LowShelfFilter": pb.LowShelfFilter,
        "Compressor": pb.Compressor,
        "Limiter": pb.Limiter,
        "Gain": pb.Gain,
        "NoiseGate": pb.NoiseGate,
    }


# Module-level sentinel; populated on first access via property-like pattern.
_ALLOWED_OPS_CACHE: dict[str, type] | None = None


def _get_allowed_operations() -> dict[str, type]:
    """Return the ALLOWED_OPERATIONS dict, building it on first call."""
    global _ALLOWED_OPS_CACHE  # noqa: PLW0603
    if _ALLOWED_OPS_CACHE is None:
        _ALLOWED_OPS_CACHE = _build_allowed_operations()
    return _ALLOWED_OPS_CACHE


class _AllowedOpsProxy:
    """Dict-like proxy that lazily builds the allowlist on first access."""

    def keys(self) -> set[str]:
        return _get_allowed_operations().keys()

    def __getitem__(self, key: str) -> type:
        return _get_allowed_operations()[key]

    def __contains__(self, key: object) -> bool:
        return key in _get_allowed_operations()

    def __len__(self) -> int:
        return len(_get_allowed_operations())

    def __iter__(self):
        return iter(_get_allowed_operations())


ALLOWED_OPERATIONS = _AllowedOpsProxy()


# ---------------------------------------------------------------------------
# Output path resolution
# ---------------------------------------------------------------------------


def _resolve_output_path(input_path: str, output_path: str | None) -> str:
    """Determine and validate the output file path.

    Default: input stem + '_fixed.wav'.
    Guard: raises AnalysisError if resolved output == resolved input (T-23-03).

    Args:
        input_path: Path to the input audio file.
        output_path: User-provided output path, or None for default.

    Returns:
        Resolved output path string.

    Raises:
        AnalysisError: If output path resolves to the same file as input.
    """
    if output_path is None:
        stem, _ext = os.path.splitext(input_path)
        output_path = f"{stem}_fixed.wav"

    # T-23-03: Same-path guard
    real_in = os.path.realpath(input_path)
    real_out = os.path.realpath(output_path)
    if real_in == real_out:
        raise AnalysisError(
            "Cannot overwrite the original file: output path resolves to the "
            "same location as input path. Use a different output path or let "
            "Phantom generate the default '_fixed' suffix."
        )

    return output_path


# ---------------------------------------------------------------------------
# apply_processing -- public function
# ---------------------------------------------------------------------------


def apply_processing(
    file_path: str,
    operations: list[dict],
    output_path: str,
) -> FixResult:
    """Apply a custom chain of audio processing operations.

    Each operation is a dict with a "type" key matching an entry in
    ALLOWED_OPERATIONS, plus constructor kwargs for the Pedalboard plugin.

    Args:
        file_path: Path to the input audio file.
        operations: List of operation dicts, each with "type" and plugin kwargs.
        output_path: Path for the processed output WAV file.

    Returns:
        FixResult with output_path and fixes_applied=["custom"].

    Raises:
        DependencyMissingError: If pedalboard is not installed.
        AnalysisError: If an operation type is invalid or processing fails.
    """
    # Step 0: Dependency guard
    try:
        import pedalboard as pb
        import soundfile as sf
    except ImportError:
        raise DependencyMissingError(
            package="Pedalboard",
            extra="processing",
            detail=(
                "Pedalboard provides audio effects processing for corrective fixes."
            ),
        )

    try:
        # Step 1: Validate paths (T-23-02, T-23-05)
        file_path = validate_input_path(file_path)
        output_path = _resolve_output_path(file_path, output_path)
        output_path = validate_output_path(output_path)

        # Step 2: Build plugin chain from operations (T-23-01)
        allowed = _get_allowed_operations()
        plugins = []
        for op in operations:
            op_copy = dict(op)
            op_type = op_copy.pop("type", None)
            if op_type not in allowed:
                raise AnalysisError(
                    f"Invalid operation type '{op_type}'. "
                    f"Allowed types: {sorted(allowed.keys())}"
                )
            plugin_cls = allowed[op_type]
            plugins.append(plugin_cls(**op_copy))

        board = pb.Pedalboard(plugins)

        # Step 3: Load audio, transpose for Pedalboard, process, transpose back
        audio = load_audio(file_path)
        pb_input = audio.samples.T  # (samples, channels) -> (channels, samples)
        pb_output = board(pb_input, float(audio.sample_rate))
        sf_output = pb_output.T  # (channels, samples) -> (samples, channels)

        # Step 4: Write output WAV
        sf.write(output_path, sf_output, audio.sample_rate)

        return FixResult(
            output_path=output_path,
            fixes_applied=["custom"],
        )

    except DependencyMissingError:
        raise
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Audio processing failed: {exc}") from exc
