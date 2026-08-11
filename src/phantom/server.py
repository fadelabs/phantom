"""Phantom MCP server.

Exposes all Phantom audio analysis functions as MCP tools accessible
over stdio transport. Start with: python -m phantom.server
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel

from phantom._utils import _get_env_int
from phantom.audio import load_audio
from phantom.exceptions import PhantomError
from phantom.facade import (
    ANALYSIS_TYPES,
    BatchDiagnosticResult,
    StemDiagnosticResult,
    run_analyses,
)
from phantom.phase import compare_phase as _compare_phase
from phantom.problems import inject_sample_rate_mismatch
from phantom.masking import analyze_masking as _analyze_masking
from phantom.masking import (
    analyze_masking_matrix as _analyze_masking_matrix,
    MaskingPair,
)
from phantom.live_metrics import read_live_metrics as _read_live_metrics
from phantom._profiles import load_profile as _load_profile
from phantom._profiles import list_profiles as _list_profiles
from phantom.comparison import compare_to_profile as _compare_to_profile
from phantom.comparison import compare_to_reference as _compare_to_reference
from phantom.comparison import match_to_reference as _match_to_reference
from phantom.separation import separate_stems as _separate_stems
from phantom.processing import (
    fix_audio as _fix_audio,
    apply_processing as _apply_processing,
)


# ---------------------------------------------------------------------------
# Composite response models
# ---------------------------------------------------------------------------


class MultiStemMaskingResult(BaseModel):
    """Typed response for the multi_stem_masking server tool."""

    pairs: list[MaskingPair]
    stem_count: int = 0
    pair_count: int = 0
    stem_paths: dict[str, str]


# Regex pattern for stripping file paths (Unix and Windows) from error messages
_PATH_REGEX = re.compile(r"([A-Za-z]:\\[^\s:,)]+\\|/[^\s:,)]+/)+")


def _to_tool_error(exc: Exception, context: dict | None = None) -> ToolError:
    """Convert an exception to a ToolError with structured JSON message.

    Error schema (SRV-09): {"error_type": str, "message": str, "context": dict}
    PhantomError subclasses pass through musician-friendly messages.
    All other exceptions get a generic message to avoid leaking internal paths.
    """
    error_info: dict = {
        "error_type": type(exc).__name__,
    }
    if isinstance(exc, PhantomError):
        msg = str(exc)
        # Strip any remaining absolute paths (Unix and Windows) from PhantomError messages
        msg = _PATH_REGEX.sub("", msg)
        error_info["message"] = msg
    else:
        error_info["message"] = (
            "Internal analysis error — check server logs for details."
        )
        if os.environ.get("PHANTOM_DEBUG"):
            print(
                f"[phantom-debug] {type(exc).__name__}: {exc}",
                file=sys.stderr,
            )
    # Redact absolute paths from context values too — they are captured verbatim
    # from tool arguments and would otherwise leak full paths into shared
    # logs/transcripts even though `message` is already redacted.
    if context:
        error_info["context"] = {
            k: (_PATH_REGEX.sub("", v) if isinstance(v, str) else v)
            for k, v in context.items()
        }
    else:
        error_info["context"] = {}
    return ToolError(json.dumps(error_info))


mcp = FastMCP("phantom")


def _phantom_tool(fn):
    """Wrap an MCP tool function with standard Phantom error handling."""
    import functools
    import inspect

    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            sig = inspect.signature(fn)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            context = {k: v for k, v in bound.arguments.items() if isinstance(v, str)}
            try:
                return await fn(*args, **kwargs)
            except PhantomError as e:
                raise _to_tool_error(e, context) from e
            except ToolError:
                raise
            except Exception as e:
                raise _to_tool_error(e, context) from e

        return async_wrapper

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        context = {k: v for k, v in bound.arguments.items() if isinstance(v, str)}
        try:
            return fn(*args, **kwargs)
        except PhantomError as e:
            raise _to_tool_error(e, context) from e
        except ToolError:
            raise
        except Exception as e:
            raise _to_tool_error(e, context) from e

    return wrapper


# ---------------------------------------------------------------------------
# Generated load -> analyze -> dump tools
# ---------------------------------------------------------------------------
#
# Nine tools share the identical shape "load N audio files, call the analyzer,
# model_dump()". Instead of nine hand-written wrappers, one registry row drives
# a tiny factory. The six single-file dimensions come from the facade registry;
# the three two-file tools are listed below. The tool-schema snapshot test
# (tests/test_tool_schema.py) gates the generated surface: any change to a
# tool's name, description, or input schema fails loudly.


def _make_unary_tool(name: str, fn, description: str):
    """Generate a load(file_path) -> fn(audio) -> dump tool."""

    def wrapper(file_path: str) -> dict:
        audio = load_audio(file_path)
        return fn(audio).model_dump()

    wrapper.__name__ = name
    wrapper.__doc__ = description
    return wrapper


def _make_pair_tool(name: str, fn, description: str):
    """Generate a load(a/b) -> fn(audio_a, audio_b) -> dump tool."""

    def wrapper(file_path_a: str, file_path_b: str) -> dict:
        audio_a = load_audio(file_path_a)
        audio_b = load_audio(file_path_b)
        return fn(audio_a, audio_b).model_dump()

    wrapper.__name__ = name
    wrapper.__doc__ = description
    return wrapper


def _make_reference_tool(name: str, fn, description: str):
    """Generate a load(file_path, reference_path) -> fn -> dump tool."""

    def wrapper(file_path: str, reference_path: str) -> dict:
        audio = load_audio(file_path)
        ref_audio = load_audio(reference_path)
        return fn(audio, ref_audio).model_dump()

    wrapper.__name__ = name
    wrapper.__doc__ = description
    return wrapper


def _peek_aggregate_decoded_bytes(file_paths: list[str]) -> int:
    """Sum header-declared decoded float32 bytes across files (AUD-03).

    Reads only file headers (sf.info, no decode). Files whose header cannot
    be read contribute zero and defer to load_audio for a precise error.
    """
    import soundfile as sf

    total = 0
    for p in file_paths:
        try:
            info = sf.info(p)
        except Exception:
            continue
        total += info.frames * info.channels * 4
    return total


def _validate_batch_inputs(file_paths: list[str]) -> list[str]:
    """Validate a batch request: size, non-empty, uniqueness, aggregate size.

    Returns the normalized paths. Raises ToolError with the standard error
    schema on the first rejection.
    """
    MAX_BATCH = 50
    if len(file_paths) > MAX_BATCH:
        raise ToolError(
            json.dumps(
                {
                    "error_type": "ValidationError",
                    "message": (
                        f"Too many files: {len(file_paths)}. Maximum batch size "
                        f"is {MAX_BATCH}."
                    ),
                    "context": {
                        "file_count": len(file_paths),
                        "max_batch": MAX_BATCH,
                    },
                }
            )
        )
    if not file_paths:
        raise ToolError(
            json.dumps(
                {
                    "error_type": "ValidationError",
                    "message": "At least 1 file path required.",
                    "context": {},
                }
            )
        )
    normalized_paths = [os.path.normpath(p) for p in file_paths]
    if len(set(normalized_paths)) != len(normalized_paths):
        raise ToolError(
            json.dumps(
                {
                    "error_type": "ValidationError",
                    "message": "Duplicate file paths (after normalization) are not supported.",
                    "context": {},
                }
            )
        )
    # Aggregate work guard (AUD-03): the per-file caps bound each decode,
    # but a full batch at the caps would still decode ~100 GB total.
    max_aggregate = _get_env_int("PHANTOM_MAX_AGGREGATE_BYTES", 4_000_000_000)
    total_decoded = _peek_aggregate_decoded_bytes(file_paths)
    if total_decoded > max_aggregate:
        raise ToolError(
            json.dumps(
                {
                    "error_type": "ValidationError",
                    "message": (
                        f"Combined stem size (~{total_decoded // 1_000_000} MB decoded) "
                        "exceeds the aggregate limit. Reduce the number of files "
                        "or trim them."
                    ),
                    "context": {"max_aggregate_bytes": max_aggregate},
                }
            )
        )
    return normalized_paths


_GENERATED_TOOLS: list[tuple[str, str, Callable, str]] = [
    (spec.cache_key, "unary", spec.fn, spec.description)
    for spec in ANALYSIS_TYPES.values()
] + [
    (
        "compare_phase",
        "pair",
        _compare_phase,
        "Compare phase between two audio files: cross-correlation, delay detection, polarity check.",
    ),
    (
        "analyze_masking",
        "pair",
        _analyze_masking,
        "Analyze frequency masking between two stems with per-octave-band severity.",
    ),
    (
        "compare_to_reference",
        "reference",
        _compare_to_reference,
        "Compare audio against a reference WAV file with normalized spectral curves.",
    ),
]

_MAKERS = {
    "unary": _make_unary_tool,
    "pair": _make_pair_tool,
    "reference": _make_reference_tool,
}

for _name, _shape, _fn, _description in _GENERATED_TOOLS:
    mcp.tool(_phantom_tool(_MAKERS[_shape](_name, _fn, _description)))


# ---------------------------------------------------------------------------
# Profile and reference tools (Tools 9-14)
# ---------------------------------------------------------------------------


@mcp.tool
@_phantom_tool
def compare_to_profile(file_path: str, profile_name: str) -> dict:
    """Compare audio against a genre reference profile for loudness, frequency, dynamics, and stereo deviations."""
    audio = load_audio(file_path)
    profile = _load_profile(profile_name)
    return _compare_to_profile(audio, profile).model_dump()


@mcp.tool
@_phantom_tool
def list_profiles() -> list[str]:
    """List all available genre reference profile names."""
    return _list_profiles()


@mcp.tool
@_phantom_tool
def load_profile(name: str) -> dict:
    """Load a genre reference profile by name. Returns profile data as JSON."""
    profile = _load_profile(name)
    return profile.model_dump()


@mcp.tool
@_phantom_tool
def separate_stems(file_path: str, output_dir: str) -> dict:
    """Separate audio into stems (vocals, drums, bass, other) via Demucs. Requires phantom-audio[separation]."""
    return _separate_stems(file_path, output_dir).model_dump()


@mcp.tool
@_phantom_tool
def match_to_reference(target_path: str, reference_path: str, output_path: str) -> dict:
    """Match target audio to reference spectral/loudness/width characteristics via Matchering. Requires phantom-audio[matching]."""
    return _match_to_reference(target_path, reference_path, output_path).model_dump()


# ---------------------------------------------------------------------------
# Processing tools (Tools 18-19)
# ---------------------------------------------------------------------------


@mcp.tool
@_phantom_tool
def fix_audio(
    file_path: str,
    problems: list[str] | None = None,
    output_path: str | None = None,
) -> dict:
    """Fix detected audio problems using corrective processing. Requires phantom-audio[processing]."""
    return _fix_audio(
        file_path, problems=problems, output_path=output_path
    ).model_dump()


@mcp.tool
@_phantom_tool
def apply_processing(
    file_path: str,
    operations: list[dict],
    output_path: str,
) -> dict:
    """Apply custom audio processing chain. Requires phantom-audio[processing]."""
    return _apply_processing(file_path, operations, output_path).model_dump()


# ---------------------------------------------------------------------------
# Composite tools (Tools 15-17)
# ---------------------------------------------------------------------------


def _run_full_analysis(audio) -> dict:
    """Run all six analysis types on an AudioData object.

    Delegates to ``phantom.facade.run_analyses``, which routes every analyzer
    through the shared ``analysis_cache`` under the registry's canonical cache
    keys (P-01). Returns ``{dimension_key: Pydantic model}``; caller adds
    file-level metadata (file, duration, sample_rate, channels).
    """
    return run_analyses(audio)


@mcp.tool
@_phantom_tool
def full_diagnostic(file_path: str) -> dict:
    """Run all six analysis types on a single audio file: spectral, loudness, dynamics, stereo, phase, and problems."""
    audio = load_audio(file_path)
    analysis = _run_full_analysis(audio)
    result = StemDiagnosticResult(
        file=os.path.basename(file_path),
        duration_seconds=audio.duration,
        sample_rate=audio.sample_rate,
        channels=audio.num_channels,
        **analysis,
    )
    return result.model_dump()


@mcp.tool
@_phantom_tool
def batch_diagnostic(file_paths: list[str]) -> dict:
    """Run full diagnostic on multiple stems. Flags sample rate mismatches as dealbreaker severity."""
    normalized_paths = _validate_batch_inputs(file_paths)

    results: dict[str, StemDiagnosticResult | dict] = {}
    sample_rates = {}
    for path, stem_name in zip(file_paths, normalized_paths):
        try:
            audio = load_audio(path)
            sample_rates[stem_name] = audio.sample_rate
            analysis = _run_full_analysis(audio)
            results[stem_name] = StemDiagnosticResult(
                file=os.path.basename(path),
                duration_seconds=audio.duration,
                sample_rate=audio.sample_rate,
                channels=audio.num_channels,
                **analysis,
            )
        except PhantomError as e:
            msg = _PATH_REGEX.sub("", str(e))
            results[stem_name] = {"error": msg, "error_type": type(e).__name__}
        except Exception as e:
            results[stem_name] = {
                "error": "Internal analysis error — check server logs for details.",
                "error_type": type(e).__name__,
            }

    # SRV-04: Flag sample rate mismatches as dealbreaker
    unique_rates = set(sample_rates.values())
    if len(unique_rates) > 1:
        for stem_name, stem_result in results.items():
            if isinstance(stem_result, StemDiagnosticResult):
                rebuilt = inject_sample_rate_mismatch(
                    stem_result.problems, sample_rates
                )
                results[stem_name] = stem_result.model_copy(
                    update={"problems": rebuilt}
                )

    batch_result = BatchDiagnosticResult(
        stems=results,
        stem_count=len(file_paths),
    )
    return batch_result.model_dump()


@mcp.tool
@_phantom_tool
def multi_stem_masking(file_paths: list[str]) -> dict:
    """Analyze frequency masking across all stem pairs. Returns pairs ranked by masking severity."""
    MAX_STEMS = 20
    if len(file_paths) > MAX_STEMS:
        raise ToolError(
            json.dumps(
                {
                    "error_type": "ValidationError",
                    "message": f"Too many stems: {len(file_paths)}. Maximum is {MAX_STEMS}.",
                    "context": {
                        "file_count": len(file_paths),
                        "max_stems": MAX_STEMS,
                    },
                }
            )
        )
    if len(file_paths) < 2:
        raise ToolError(
            json.dumps(
                {
                    "error_type": "ValidationError",
                    "message": "At least 2 file paths required for masking analysis.",
                    "context": {},
                }
            )
        )

    # Aggregate memory guard: this tool holds every stem in memory at once, so
    # the per-file size/duration limits in load_audio aren't sufficient. Peek
    # each header and reject if the combined decoded size would be excessive
    # (default 4 GB, override via PHANTOM_MAX_AGGREGATE_BYTES).
    import soundfile as sf

    max_aggregate = _get_env_int("PHANTOM_MAX_AGGREGATE_BYTES", 4_000_000_000)
    total_bytes = 0
    for p in file_paths:
        try:
            info = sf.info(p)
        except Exception:
            continue  # defer to load_audio below for a precise error
        total_bytes += info.frames * info.channels * 4  # float32 decoded
    if total_bytes > max_aggregate:
        raise ToolError(
            json.dumps(
                {
                    "error_type": "ValidationError",
                    "message": (
                        f"Combined stem size (~{total_bytes // 1_000_000} MB decoded) "
                        "exceeds the aggregate limit. Reduce the number or length of stems."
                    ),
                    "context": {"max_aggregate_bytes": max_aggregate},
                }
            )
        )

    stems = [load_audio(p) for p in file_paths]
    matrix_result = _analyze_masking_matrix(stems)

    # Adaptive default: scale with stem count, floor of 10, capped at total pairs
    stem_count = matrix_result.stem_count
    pair_count = matrix_result.pair_count
    default_top_n = min(pair_count, max(10, stem_count))

    # Env var overrides the adaptive default when explicitly set
    env_val = os.environ.get("PHANTOM_MASKING_TOP_N")
    if env_val is not None and env_val.strip():
        top_n = _get_env_int("PHANTOM_MASKING_TOP_N", default_top_n)
    else:
        top_n = default_top_n

    result = MultiStemMaskingResult(
        pairs=matrix_result.pairs[:top_n],
        stem_count=matrix_result.stem_count,
        pair_count=matrix_result.pair_count,
        stem_paths={f"stem_{i}": os.path.basename(p) for i, p in enumerate(file_paths)},
    )
    return result.model_dump()


# ---------------------------------------------------------------------------
# Live metrics (Phantom Link)
# ---------------------------------------------------------------------------


@mcp.tool
@_phantom_tool
def read_live_metrics(instance_id: str | None = None) -> dict:
    """Read the Phantom Studio plugin's live meter snapshot (loudness, true peak, stereo, band energy, verdicts). Omit instance_id for the most recent instance."""
    return _read_live_metrics(instance_id).model_dump()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _startup_preflight() -> None:
    """Log version and optional extras status to stderr on startup."""
    from phantom import __version__
    from phantom._diagnostics import (
        OPTIONAL_DEPS,
        separation_plugin_status,
        try_import,
    )

    if os.environ.get("PHANTOM_QUIET"):
        return

    extras = {}
    sep_ok, _ = separation_plugin_status()
    extras["separation"] = "OK" if sep_ok else "missing"
    for pkg, extra_name in OPTIONAL_DEPS.items():
        ok, _ = try_import(pkg)
        extras[extra_name] = "OK" if ok else "missing"

    extras_str = " ".join(f"{k}={v}" for k, v in extras.items())
    print(f"[phantom-mcp] v{__version__} | {extras_str}", file=sys.stderr)


def main():
    """Entry point for phantom-mcp CLI."""
    if "--version" in sys.argv:
        from phantom import __version__

        print(f"phantom-mcp {__version__}")
        return
    if "--tools" in sys.argv:
        import asyncio

        try:
            tools = sorted(t.name for t in asyncio.run(mcp.list_tools()))
        except (AttributeError, TypeError):
            print(
                "Cannot list tools — FastMCP version may be incompatible",
                file=sys.stderr,
            )
            sys.exit(1)
        for name in tools:
            print(name)
        return
    _startup_preflight()
    mcp.run()


if __name__ == "__main__":
    main()
