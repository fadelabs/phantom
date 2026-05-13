"""Corrective audio processing via Pedalboard.

Provides the Recipe system that maps detected audio problems to corrective
Pedalboard plugin chains, fix_audio() for automatic problem correction,
and apply_processing() for custom processing chains.

Pedalboard is an optional dependency. Functions raise DependencyMissingError
with install instructions if Pedalboard is not available.

Recipe chain order follows standard mixing signal chain: HPF first, then
notch filters, then parametric cuts, then shelf adjustments.
"""

from __future__ import annotations

import os
from collections.abc import KeysView
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel

from phantom.exceptions import AnalysisError, DependencyMissingError
from phantom._utils import validate_input_path, validate_output_path
from phantom.audio import load_audio
from phantom.problems import ProblemItem, ProblemsResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNFIXABLE_TYPES: frozenset[str] = frozenset(
    {"clipping", "inter_sample_peak", "noise_floor", "snr", "lossy_codec"}
)

# Severity ordering: higher int = worse severity.
# Used by _compare_results to classify improvement vs regression.
_SEVERITY_ORDER: dict[str, int] = {
    "minor": 0,
    "moderate": 1,
    "significant": 2,
    "dealbreaker": 3,
}

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
    plugins: list = []
    for r in resonances:
        freq = r.get("frequency_hz")
        if freq is None:
            continue  # Skip malformed resonance entry
        plugins.append(
            pb.PeakFilter(
                cutoff_frequency_hz=freq,
                gain_db=-6.0,
                q=r.get("q_factor", 10.0),
            )
        )
    return plugins


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

    def keys(self) -> KeysView[str]:
        """Return dict_keys view of allowed operation names."""
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


# ---------------------------------------------------------------------------
# Before/after comparison helper
# ---------------------------------------------------------------------------


def _get_severity_rank(severity: str) -> int:
    """Return the numeric rank for a severity string.

    Raises AnalysisError on unknown values so that contract violations
    surface immediately rather than being silently treated as lowest severity.
    """
    rank = _SEVERITY_ORDER.get(severity)
    if rank is None:
        raise AnalysisError(
            f"Unknown severity '{severity}' in problem comparison. "
            f"Expected one of: {sorted(_SEVERITY_ORDER.keys())}"
        )
    return rank


def _compare_results(
    before: ProblemsResult,
    after: ProblemsResult,
) -> tuple[list[FixComparison], list[FixComparison]]:
    """Compare before and after problem detection results.

    For each problem in ``before.problems``:
    - Not in after -> resolved (improvement)
    - In after with lower severity -> improved (improvement)
    - In after with same severity -> unchanged (neither)
    - In after with higher severity -> worsened (regression)

    Args:
        before: ProblemsResult from before processing.
        after: ProblemsResult from after processing.

    Returns:
        Tuple of (improvements, regressions) lists of FixComparison.
    """
    # Build lookup: problem type -> severity for after results
    after_by_type: dict[str, str] = {}
    for p in after.problems:
        after_by_type[p.type] = p.severity

    improvements: list[FixComparison] = []
    regressions: list[FixComparison] = []

    for p in before.problems:
        if p.type not in after_by_type:
            # Resolved
            improvements.append(
                FixComparison(
                    problem_type=p.type,
                    before_severity=p.severity,
                    after_severity=None,
                    status="resolved",
                )
            )
        else:
            after_sev = after_by_type[p.type]
            before_rank = _get_severity_rank(p.severity)
            after_rank = _get_severity_rank(after_sev)

            if after_rank < before_rank:
                improvements.append(
                    FixComparison(
                        problem_type=p.type,
                        before_severity=p.severity,
                        after_severity=after_sev,
                        status="improved",
                    )
                )
            elif after_rank > before_rank:
                regressions.append(
                    FixComparison(
                        problem_type=p.type,
                        before_severity=p.severity,
                        after_severity=after_sev,
                        status="worsened",
                    )
                )
            # else: unchanged -- not added to either list

    return improvements, regressions


# ---------------------------------------------------------------------------
# Chain builder from detected problems
# ---------------------------------------------------------------------------


def _plugin_sort_key(plugin: object) -> tuple[int, float]:
    """Return a sort key for signal chain ordering.

    Order: HPF/LPF first (0), then notch filters Q>10 (1),
    then peak filters Q<=10 (2), then shelf filters (3).
    Secondary sort by frequency (ascending).
    """
    import pedalboard as pb

    freq = getattr(plugin, "cutoff_frequency_hz", 0.0)

    if isinstance(plugin, (pb.HighpassFilter, pb.LowpassFilter)):
        return (0, freq)
    if isinstance(plugin, pb.PeakFilter):
        q = getattr(plugin, "q", 1.0)
        if q > 10:
            return (1, freq)  # Notch
        return (2, freq)  # Parametric
    if isinstance(plugin, (pb.LowShelfFilter, pb.HighShelfFilter)):
        return (3, freq)
    return (4, freq)


def _build_chain_from_problems(problems: list[ProblemItem]) -> list:
    """Build a sorted Pedalboard plugin chain from detected problems.

    Iterates fixable problems, looks up recipes, flattens into a single
    plugin list, then sorts by signal chain priority: HPF/LPF first,
    then notch (Q>10), then peak (Q<=10), then shelf.

    Args:
        problems: List of ProblemItem instances from detect_problems.

    Returns:
        List of Pedalboard plugin instances, sorted by signal chain order.
    """
    plugins: list = []

    for p in problems:
        if p.type in UNFIXABLE_TYPES:
            continue
        recipe = RECIPES.get(p.type)
        if recipe is None:
            continue
        plugins.extend(recipe.build_chain(p.details))

    if not plugins:
        return []

    plugins.sort(key=_plugin_sort_key)
    return plugins


# ---------------------------------------------------------------------------
# fix_audio -- public function
# ---------------------------------------------------------------------------

# Module-level import for detect_problems so tests can monkeypatch it.
# Already imported ProblemItem and ProblemsResult at the top; this adds
# the function reference used by fix_audio at runtime.
from phantom.problems import detect_problems  # noqa: E402


def fix_audio(
    file_path: str,
    problems: list[str] | None = None,
    output_path: str | None = None,
) -> FixResult:
    """Fix detected audio problems using recipe-based processing.

    High-level public API that orchestrates the full corrective pipeline:
    load audio, detect problems, look up recipes, build Pedalboard chain,
    process, write output, re-detect problems, compare before/after.

    Args:
        file_path: Path to the input audio file.
        problems: Optional list of problem type strings to fix. If None,
            fixes all detected fixable problems.
        output_path: Path for the processed output WAV file. If None,
            uses input stem + '_fixed.wav'.

    Returns:
        FixResult with output_path, fixes_applied, before/after
        ProblemsResult, improvements, and regressions.

    Raises:
        DependencyMissingError: If pedalboard is not installed.
        FileNotFoundError: If input file does not exist.
        AnalysisError: If processing fails.
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
        # Step 1: Validate paths
        file_path = validate_input_path(file_path)
        output_path = _resolve_output_path(file_path, output_path)
        output_path = validate_output_path(output_path)

        # Step 2: Load audio and detect problems (before)
        audio = load_audio(file_path)
        before = detect_problems(audio)

        # Step 3: Filter to fixable problems
        fixable = [
            p
            for p in before.problems
            if p.type not in UNFIXABLE_TYPES and p.type in RECIPES
        ]

        # Step 4: Apply user filter if specified (T-23-06)
        if problems is not None:
            allowed_set = set(problems)
            fixable = [p for p in fixable if p.type in allowed_set]

        # Step 5: Build plugin chain
        chain = _build_chain_from_problems(fixable)
        fixes_applied = [p.type for p in fixable]

        # Step 6: Process audio
        if chain:
            board = pb.Pedalboard(chain)
            pb_input = audio.samples.T  # (samples, channels) -> (channels, samples)
            pb_output = board(pb_input, float(audio.sample_rate))
            sf_output = pb_output.T  # (channels, samples) -> (samples, channels)
            sf.write(output_path, sf_output, audio.sample_rate)
        else:
            # No fixable problems -- write copy of audio unchanged
            sf.write(output_path, audio.samples, audio.sample_rate)

        # Step 7: Detect problems on output (after)
        after_audio = load_audio(output_path)
        after = detect_problems(after_audio)

        # Step 8: Compare before/after
        improvements, regressions = _compare_results(before, after)

        return FixResult(
            output_path=output_path,
            fixes_applied=fixes_applied,
            before=before,
            after=after,
            improvements=improvements,
            regressions=regressions,
        )

    except DependencyMissingError:
        raise
    except FileNotFoundError:
        raise
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError(f"Audio processing failed: {exc}") from exc
