"""Analysis facade: one registry drives the CLI, the composite tools, and the MCP wrappers.

Before this module, the six analysis dimensions were wired three separate
times with three different idioms:

- ``server._run_full_analysis`` hardcoded the cache keys ("analyze_spectrum").
- ``cli.analyze._run_selected_analyses`` derived them from ``fn.__name__``.
- ``phantom.comparison`` hardcoded the same four keys its ``compare_*`` tools
  use to reuse prior analysis work.

They coincided only because the analyzer function names happened to match the
hardcoded keys. Renaming an analyzer would silently split the CLI and server
cache domains with every test still passing. This module makes the registry
the single source of truth: ``ANALYSIS_TYPES`` carries the cache key next to
the function, so callers never derive it from the name.

The registry also carries the MCP tool description and the CLI display title,
so the server's tool wrapper generator and the ``analyze`` CLI both consume
the same row.

Adding a dimension
------------------
New dimension = 1 analyzer module in ``src/phantom/`` + 1 ``AnalysisSpec``
row in ``ANALYSIS_TYPES``. The row then shows up automatically as:

- a key in ``run_analyses`` output and the shared ``StemDiagnosticResult``
  payload,
- a ``--<key>`` narrowing flag path in the ``analyze`` CLI (via
  ``cli.analyze._enabled_analyses``),
- a load -> analyze -> dump MCP tool registered by ``server`` (the wrapper
  generator iterates ``ANALYSIS_TYPES``).

No other file changes. The tool-schema snapshot test
(``tests/test_tool_schema.py``) gates the MCP surface: adding a dimension
adds a tool, which is an *additive* contract change and must be committed
deliberately with the snapshot updated in that same commit.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable

from pydantic import BaseModel, ConfigDict, field_validator

from phantom._cache import _cached_analysis
from phantom.audio import AudioData
from phantom.dynamics import analyze_dynamics, DynamicsResult
from phantom.loudness import analyze_loudness, LoudnessResult
from phantom.phase import analyze_phase, PhaseResult
from phantom.problems import detect_problems, ProblemsResult
from phantom.spectral import analyze_spectrum, SpectralResult
from phantom.stereo import analyze_stereo, StereoResult


@dataclass(frozen=True)
class AnalysisSpec:
    """One analysis dimension in the shared facade registry.

    Parameters
    ----------
    key:
        Public dimension key, used as the payload field name, the CLI
        ``--<flag>`` name, and the key in ``run_analyses`` output
        (e.g. ``"spectral"``).
    fn:
        Analyzer callable: ``fn(audio: AudioData) -> BaseModel``.
    title:
        Human display title for the CLI tables (e.g. ``"Spectral Analysis"``).
    cache_key:
        Shared cache namespace for this analysis. Must stay equal to the keys
        ``phantom.comparison`` uses internally so composite/compare tools
        reuse results across calls. Deliberately explicit, never derived from
        ``fn.__name__`` -- that is the B.1 drift this facade exists to remove.
    description:
        MCP tool description (the tool-wrapper generator uses it verbatim).
    """

    key: str
    fn: Callable[[AudioData], BaseModel]
    title: str
    cache_key: str
    description: str


ANALYSIS_TYPES: dict[str, AnalysisSpec] = {
    "spectral": AnalysisSpec(
        key="spectral",
        fn=analyze_spectrum,
        title="Spectral Analysis",
        cache_key="analyze_spectrum",
        description=(
            "Analyze frequency spectrum: centroid, rolloff, flatness, contrast, "
            "dissonance, octave band energy."
        ),
    ),
    "loudness": AnalysisSpec(
        key="loudness",
        fn=analyze_loudness,
        title="Loudness Analysis",
        cache_key="analyze_loudness",
        description=(
            "Measure EBU R128 loudness: integrated LUFS, true peak dBTP, "
            "loudness range, short-term and momentary LUFS."
        ),
    ),
    "dynamics": AnalysisSpec(
        key="dynamics",
        fn=analyze_dynamics,
        title="Dynamics Analysis",
        cache_key="analyze_dynamics",
        description=(
            "Measure dynamics: RMS, peak, crest factor, dynamic range, dynamic "
            "complexity."
        ),
    ),
    "stereo": AnalysisSpec(
        key="stereo",
        fn=analyze_stereo,
        title="Stereo Field Analysis",
        cache_key="analyze_stereo",
        description=(
            "Analyze stereo field: correlation, width, mid/side ratio, L/R "
            "balance, panorama distribution."
        ),
    ),
    "phase": AnalysisSpec(
        key="phase",
        fn=analyze_phase,
        title="Phase Coherence Analysis",
        cache_key="analyze_phase",
        description=(
            "Check phase coherence: overall and per-band correlation, polarity "
            "detection."
        ),
    ),
    "problems": AnalysisSpec(
        key="problems",
        fn=detect_problems,
        title="Problem Detection",
        cache_key="detect_problems",
        description=(
            "Scan for audio problems: clipping, DC offset, ISP, noise, hum, "
            "sibilance, mud, harshness, resonances."
        ),
    ),
}


def analysis_keys() -> tuple[str, ...]:
    """Return the dimension keys in registry (declaration) order."""
    return tuple(ANALYSIS_TYPES)


def run_analyses(
    audio: AudioData, keys: Iterable[str] | None = None
) -> dict[str, BaseModel]:
    """Run the requested analyses on *audio*, returning Pydantic instances.

    Every analyzer goes through the shared ``_cached_analysis`` under the
    registry's ``cache_key``, so the composite/compare tools, the CLI, and the
    MCP wrappers all populate and reuse the same cache entries.

    Parameters
    ----------
    audio:
        Decoded audio to analyze.
    keys:
        Subset of ``ANALYSIS_TYPES`` keys to run; defaults to all of them.
        Result keys follow the given order when *keys* is supplied (the CLI
        passes registry order) and registry order otherwise.

    Returns
    -------
    ``{key: model}`` where *model* is the analyzer's Pydantic result (not a
    dumped dict); callers dump or render it as they need.
    """
    ordered = list(keys) if keys is not None else list(ANALYSIS_TYPES)
    return {
        key: _cached_analysis(
            audio, ANALYSIS_TYPES[key].cache_key, ANALYSIS_TYPES[key].fn
        )
        for key in ordered
    }


# ---------------------------------------------------------------------------
# Shared stem payload model(s)
# ---------------------------------------------------------------------------


class StemDiagnosticResult(BaseModel):
    """Typed per-stem payload for the server composite tools.

    All six dimensions are required: ``full_diagnostic`` and ``batch_diagnostic``
    always run every analyzer. ``model_config = extra="forbid"`` makes a payload
    key that is not a field fail loudly at construction instead of being
    silently dropped, so the "add a dimension" workflow is explicitly: new
    analyzer module + registry row + a matching field here.

    The ``analyze`` CLI emits its own JSON shape from the individual results
    and does not route through this model, so its subset runs stay
    enabled-only with nested nulls intact.
    """

    model_config = ConfigDict(extra="forbid")

    file: str
    duration_seconds: float
    sample_rate: int
    channels: int
    spectral: SpectralResult
    loudness: LoudnessResult
    dynamics: DynamicsResult
    stereo: StereoResult
    phase: PhaseResult
    problems: ProblemsResult

    @field_validator("duration_seconds", mode="before")
    @classmethod
    def _round_duration(cls, v: float) -> float:
        return round(v, 3) if v is not None else v


class BatchDiagnosticResult(BaseModel):
    """Typed batch payload shared by ``batch_diagnostic`` and the CLI batch
    ``--json`` output. Error stems are held as plain dicts."""

    stems: dict[str, StemDiagnosticResult | dict]  # dict for error stems
    stem_count: int


# Re-export for the facade's callers.
__all__ = [
    "ANALYSIS_TYPES",
    "AnalysisSpec",
    "BatchDiagnosticResult",
    "StemDiagnosticResult",
    "analysis_keys",
    "run_analyses",
]
