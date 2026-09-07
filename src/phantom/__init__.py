"""Phantom: AI audio engineering system."""

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _metadata_version

    __version__ = _metadata_version("phantom-audio")
except PackageNotFoundError:
    __version__ = "unknown"

from phantom._profiles import ReferenceProfile, list_profiles, load_profile
from phantom.audio import AudioData, load_audio
from phantom.comparison import (
    DeviationResult,
    DynamicsComparisonSection,
    DynamicsReferenceComparisonSection,
    LoudnessProfileComparisonSection,
    LoudnessReferenceComparisonSection,
    MatchAdjustments,
    MatchResult,
    MetricDiff,
    MonoBelowResult,
    ProfileComparisonResult,
    RangeDeviationResult,
    ReferenceComparisonResult,
    StereoProfileComparisonSection,
    StereoReferenceComparisonSection,
    compare_to_profile,
    compare_to_reference,
    match_to_reference,
)
from phantom.dynamics import DynamicsResult, analyze_dynamics
from phantom.exceptions import (
    AnalysisError,
    AudioLoadError,
    DependencyMissingError,
    PathSecurityError,
    PhantomError,
    ProfileLoadError,
)
from phantom.loudness import LoudnessResult, analyze_loudness
from phantom.masking import (
    MaskingBand,
    MaskingMatrixResult,
    MaskingPair,
    MaskingResult,
    analyze_masking,
    analyze_masking_matrix,
)
from phantom.phase import PhaseCompareResult, PhaseResult, analyze_phase, compare_phase
from phantom.problems import (
    ProblemItem,
    ProblemsResult,
    ProblemSummary,
    build_summary,
    detect_problems,
)
from phantom.processing import FixComparison, FixResult, apply_processing, fix_audio
from phantom.separation import SeparationResult, separate_stems
from phantom.spectral import SpectralResult, analyze_spectrum
from phantom.stereo import PanoramaDistribution, StereoResult, analyze_stereo

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
