"""Phantom: AI audio engineering system."""

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _metadata_version

    __version__ = _metadata_version("phantom-audio")
except PackageNotFoundError:
    __version__ = "unknown"

from phantom.audio import AudioData, load_audio
from phantom.exceptions import (
    AnalysisError,
    AudioLoadError,
    DependencyMissingError,
    PathSecurityError,
    PhantomError,
    ProfileLoadError,
)
from phantom.loudness import analyze_loudness, LoudnessResult
from phantom.spectral import analyze_spectrum, SpectralResult
from phantom.dynamics import analyze_dynamics, DynamicsResult
from phantom.stereo import analyze_stereo, StereoResult, PanoramaDistribution
from phantom.phase import analyze_phase, compare_phase, PhaseResult, PhaseCompareResult
from phantom.problems import (
    detect_problems,
    build_summary,
    ProblemsResult,
    ProblemItem,
    ProblemSummary,
)
from phantom.masking import (
    analyze_masking,
    analyze_masking_matrix,
    MaskingResult,
    MaskingBand,
    MaskingMatrixResult,
    MaskingPair,
)
from phantom._profiles import ReferenceProfile, load_profile, list_profiles
from phantom.comparison import (
    compare_to_profile,
    compare_to_reference,
    match_to_reference,
    DeviationResult,
    RangeDeviationResult,
    MonoBelowResult,
    LoudnessProfileComparisonSection,
    DynamicsComparisonSection,
    StereoProfileComparisonSection,
    LoudnessReferenceComparisonSection,
    DynamicsReferenceComparisonSection,
    StereoReferenceComparisonSection,
    MetricDiff,
    MatchAdjustments,
    ProfileComparisonResult,
    ReferenceComparisonResult,
    MatchResult,
)
from phantom.separation import separate_stems, SeparationResult
from phantom.processing import fix_audio, apply_processing, FixResult, FixComparison

__all__ = [
    "AnalysisError",
    "AudioData",
    "AudioLoadError",
    "DependencyMissingError",
    "DeviationResult",
    "DynamicsComparisonSection",
    "DynamicsReferenceComparisonSection",
    "DynamicsResult",
    "FixComparison",
    "FixResult",
    "LoudnessProfileComparisonSection",
    "LoudnessReferenceComparisonSection",
    "LoudnessResult",
    "MaskingBand",
    "MaskingMatrixResult",
    "MaskingPair",
    "MaskingResult",
    "MatchAdjustments",
    "MatchResult",
    "MetricDiff",
    "MonoBelowResult",
    "PanoramaDistribution",
    "PathSecurityError",
    "PhantomError",
    "PhaseCompareResult",
    "PhaseResult",
    "ProblemItem",
    "ProblemSummary",
    "ProblemsResult",
    "ProfileComparisonResult",
    "ProfileLoadError",
    "RangeDeviationResult",
    "ReferenceComparisonResult",
    "ReferenceProfile",
    "SeparationResult",
    "SpectralResult",
    "StereoProfileComparisonSection",
    "StereoReferenceComparisonSection",
    "StereoResult",
    "analyze_dynamics",
    "analyze_loudness",
    "analyze_masking",
    "analyze_masking_matrix",
    "analyze_phase",
    "analyze_spectrum",
    "analyze_stereo",
    "apply_processing",
    "build_summary",
    "compare_phase",
    "compare_to_profile",
    "compare_to_reference",
    "detect_problems",
    "fix_audio",
    "list_profiles",
    "load_audio",
    "load_profile",
    "match_to_reference",
    "separate_stems",
]
