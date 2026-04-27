"""Phantom MCP server.

Exposes all Phantom audio analysis functions as MCP tools accessible
over stdio transport. Start with: python -m phantom.server
"""

from __future__ import annotations

import json
import os
import re

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, field_validator

from phantom.audio import load_audio
from phantom.exceptions import PhantomError
from phantom.spectral import analyze_spectrum as _analyze_spectrum, SpectralResult
from phantom.loudness import analyze_loudness as _analyze_loudness, LoudnessResult
from phantom.dynamics import analyze_dynamics as _analyze_dynamics, DynamicsResult
from phantom.stereo import analyze_stereo as _analyze_stereo, StereoResult
from phantom.phase import analyze_phase as _analyze_phase, PhaseResult
from phantom.phase import compare_phase as _compare_phase
from phantom.problems import (
    detect_problems as _detect_problems,
    ProblemItem,
    build_summary,
    ProblemsResult,
)
from phantom.masking import analyze_masking as _analyze_masking
from phantom.masking import (
    analyze_masking_matrix as _analyze_masking_matrix,
    MaskingPair,
)
from phantom._profiles import load_profile as _load_profile
from phantom._profiles import list_profiles as _list_profiles
from phantom.comparison import compare_to_profile as _compare_to_profile
from phantom.comparison import compare_to_reference as _compare_to_reference
from phantom.comparison import match_to_reference as _match_to_reference
from phantom.separation import separate_stems as _separate_stems


# ---------------------------------------------------------------------------
# Composite response models
# ---------------------------------------------------------------------------


class FullDiagnosticResult(BaseModel):
    """Typed response for the full_diagnostic server tool."""

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


class BatchStemResult(BaseModel):
    """Typed result for a single stem in batch_diagnostic."""

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
    """Typed response for the batch_diagnostic server tool."""

    stems: dict[str, BatchStemResult | dict]  # dict for error stems
    stem_count: int


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
        if os.environ.get("PHANTOM_DEBUG"):
            error_info["message"] = str(exc)
        else:
            error_info["message"] = (
                "Internal analysis error — check server logs for details."
            )
    error_info["context"] = context if context else {}
    return ToolError(json.dumps(error_info))


mcp = FastMCP("phantom")


def _phantom_tool(fn):
    """Wrap an MCP tool function with standard Phantom error handling."""
    import functools
    import inspect

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        sig = inspect.signature(fn)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        context = {k: v for k, v in bound.arguments.items() if isinstance(v, str)}
        try:
            return fn(*args, **kwargs)
        except PhantomError as e:
            raise _to_tool_error(e, context)
        except ToolError:
            raise
        except Exception as e:
            raise _to_tool_error(e, context)

    return wrapper


# ---------------------------------------------------------------------------
# Individual analysis tools (Tools 1-7)
# ---------------------------------------------------------------------------


@mcp.tool
@_phantom_tool
def analyze_spectrum(file_path: str) -> dict:
    """Analyze frequency spectrum: centroid, rolloff, flatness, contrast, dissonance, octave band energy."""
    audio = load_audio(file_path)
    return _analyze_spectrum(audio).model_dump()


@mcp.tool
@_phantom_tool
def analyze_loudness(file_path: str) -> dict:
    """Measure EBU R128 loudness: integrated LUFS, true peak dBTP, loudness range, short-term and momentary LUFS."""
    audio = load_audio(file_path)
    return _analyze_loudness(audio).model_dump()


@mcp.tool
@_phantom_tool
def analyze_dynamics(file_path: str) -> dict:
    """Measure dynamics: RMS, peak, crest factor, dynamic range, dynamic complexity."""
    audio = load_audio(file_path)
    return _analyze_dynamics(audio).model_dump()


@mcp.tool
@_phantom_tool
def analyze_stereo(file_path: str) -> dict:
    """Analyze stereo field: correlation, width, mid/side ratio, L/R balance, panorama distribution."""
    audio = load_audio(file_path)
    return _analyze_stereo(audio).model_dump()


@mcp.tool
@_phantom_tool
def analyze_phase(file_path: str) -> dict:
    """Check phase coherence: overall and per-band correlation, polarity detection."""
    audio = load_audio(file_path)
    return _analyze_phase(audio).model_dump()


# ---------------------------------------------------------------------------
# Two-file analysis tools (Tools 6, 8, 10)
# ---------------------------------------------------------------------------


@mcp.tool
@_phantom_tool
def compare_phase(file_path_a: str, file_path_b: str) -> dict:
    """Compare phase between two audio files: cross-correlation, delay detection, polarity check."""
    audio_a = load_audio(file_path_a)
    audio_b = load_audio(file_path_b)
    return _compare_phase(audio_a, audio_b).model_dump()


@mcp.tool
@_phantom_tool
def detect_problems(file_path: str) -> dict:
    """Scan for audio problems: clipping, DC offset, ISP, noise, hum, sibilance, mud, harshness, resonances."""
    audio = load_audio(file_path)
    return _detect_problems(audio).model_dump()


@mcp.tool
@_phantom_tool
def analyze_masking(file_path_a: str, file_path_b: str) -> dict:
    """Analyze frequency masking between two stems with per-octave-band severity."""
    audio_a = load_audio(file_path_a)
    audio_b = load_audio(file_path_b)
    return _analyze_masking(audio_a, audio_b).model_dump()


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
def compare_to_reference(file_path: str, reference_path: str) -> dict:
    """Compare audio against a reference WAV file with normalized spectral curves."""
    audio = load_audio(file_path)
    ref_audio = load_audio(reference_path)
    return _compare_to_reference(audio, ref_audio).model_dump()


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
# Composite tools (Tools 15-17)
# ---------------------------------------------------------------------------


def _run_full_analysis(audio) -> dict:
    """Run all six analysis types on an AudioData object.

    Returns a dict with keys: spectral, loudness, dynamics, stereo,
    phase, problems. Values are Pydantic model instances (not dumped dicts).
    Caller adds file-level metadata (file, duration, sample_rate, channels).
    """
    return {
        "spectral": _analyze_spectrum(audio),
        "loudness": _analyze_loudness(audio),
        "dynamics": _analyze_dynamics(audio),
        "stereo": _analyze_stereo(audio),
        "phase": _analyze_phase(audio),
        "problems": _detect_problems(audio),
    }


@mcp.tool
@_phantom_tool
def full_diagnostic(file_path: str) -> dict:
    """Run all six analysis types on a single audio file: spectral, loudness, dynamics, stereo, phase, and problems."""
    audio = load_audio(file_path)
    analysis = _run_full_analysis(audio)
    result = FullDiagnosticResult(
        file=os.path.basename(file_path),
        duration_seconds=audio.duration,
        sample_rate=audio.sample_rate,
        channels=audio.num_channels,
        **analysis,
    )
    return result.model_dump()


@mcp.tool
def batch_diagnostic(file_paths: list[str]) -> dict:
    """Run full diagnostic on multiple stems. Flags sample rate mismatches as dealbreaker severity."""
    try:
        MAX_BATCH = 50
        if len(file_paths) > MAX_BATCH:
            raise ToolError(
                json.dumps(
                    {
                        "error_type": "ValidationError",
                        "message": f"Too many files: {len(file_paths)}. Maximum batch size is {MAX_BATCH}.",
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
        if len(set(file_paths)) != len(file_paths):
            raise ToolError(
                json.dumps(
                    {
                        "error_type": "ValidationError",
                        "message": "Duplicate file paths are not supported.",
                        "context": {},
                    }
                )
            )

        results: dict[str, BatchStemResult | dict] = {}
        sample_rates = {}
        for path in file_paths:
            stem_name = path
            try:
                audio = load_audio(path)
                sample_rates[stem_name] = audio.sample_rate
                analysis = _run_full_analysis(audio)
                results[stem_name] = BatchStemResult(
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
            mismatch_detail = {name: int(rate) for name, rate in sample_rates.items()}
            for stem_name, stem_result in results.items():
                if isinstance(stem_result, BatchStemResult):
                    mismatch = ProblemItem(
                        type="sample_rate_mismatch",
                        severity="dealbreaker",
                        message=f"Sample rate mismatch across stems: {mismatch_detail}",
                        details={"sample_rates": mismatch_detail},
                    )
                    all_problems = [mismatch] + list(stem_result.problems.problems)
                    rebuilt = ProblemsResult(
                        problems=all_problems,
                        clean=False,
                        summary=build_summary(all_problems),
                    )
                    results[stem_name] = stem_result.model_copy(
                        update={"problems": rebuilt}
                    )

        batch_result = BatchDiagnosticResult(
            stems=results,
            stem_count=len(file_paths),
        )
        return batch_result.model_dump()
    except ToolError:
        raise
    except Exception as e:
        raise _to_tool_error(e, {"file_paths": file_paths})


@mcp.tool
def multi_stem_masking(file_paths: list[str]) -> dict:
    """Analyze frequency masking across all stem pairs. Returns pairs ranked by masking severity."""
    try:
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

        stems = [load_audio(p) for p in file_paths]
        matrix_result = _analyze_masking_matrix(stems)
        result = MultiStemMaskingResult(
            pairs=matrix_result.pairs,
            stem_count=matrix_result.stem_count,
            pair_count=matrix_result.pair_count,
            stem_paths={
                f"stem_{i}": os.path.basename(p) for i, p in enumerate(file_paths)
            },
        )
        return result.model_dump()
    except PhantomError as e:
        raise _to_tool_error(e, {"file_paths": file_paths})
    except ToolError:
        raise
    except Exception as e:
        raise _to_tool_error(e, {"file_paths": file_paths})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main():
    """Entry point for phantom-mcp CLI."""
    import sys

    if "--version" in sys.argv:
        from phantom import __version__

        print(f"phantom-mcp {__version__}")
        return
    if "--tools" in sys.argv:
        tools = sorted(t.name for t in mcp._tool_manager._tools.values())
        for name in tools:
            print(name)
        return
    mcp.run()


if __name__ == "__main__":
    main()
