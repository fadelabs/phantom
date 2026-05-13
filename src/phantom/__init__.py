"""Phantom: AI audio engineering system."""

__version__ = "1.2.1"

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

__all__ = [
    "AudioData",
    "load_audio",
    "analyze_spectrum",
    "analyze_loudness",
    "analyze_dynamics",
    "analyze_stereo",
    "analyze_masking",
    "analyze_masking_matrix",
    "analyze_phase",
    "compare_phase",
    "compare_to_profile",
    "compare_to_reference",
    "detect_problems",
    "build_summary",
    "load_profile",
    "list_profiles",
    "match_to_reference",
    "ReferenceProfile",
    "separate_stems",
    "PhantomError",
    "PathSecurityError",
    "AudioLoadError",
    "AnalysisError",
    "DependencyMissingError",
    "ProfileLoadError",
    "__version__",
    # Response models
    "SpectralResult",
    "LoudnessResult",
    "DynamicsResult",
    "StereoResult",
    "PanoramaDistribution",
    "PhaseResult",
    "PhaseCompareResult",
    "ProblemsResult",
    "ProblemItem",
    "ProblemSummary",
    "MaskingResult",
    "MaskingBand",
    "MaskingMatrixResult",
    "MaskingPair",
    "DeviationResult",
    "RangeDeviationResult",
    "MonoBelowResult",
    "LoudnessProfileComparisonSection",
    "DynamicsComparisonSection",
    "StereoProfileComparisonSection",
    "LoudnessReferenceComparisonSection",
    "DynamicsReferenceComparisonSection",
    "StereoReferenceComparisonSection",
    "MetricDiff",
    "MatchAdjustments",
    "ProfileComparisonResult",
    "ReferenceComparisonResult",
    "MatchResult",
    "SeparationResult",
]
