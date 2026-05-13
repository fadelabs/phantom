"""Reference comparison analysis — profile, reference, and matching.

Submodules:
    comparison.profile  — compare_to_profile (genre reference profiles)
    comparison.reference — compare_to_reference (WAV-to-WAV)
    comparison.match    — match_to_reference (Matchering, GPLv3 boundary)
"""

from phantom.comparison._common import (
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
    _check_mono_below,  # noqa: F401 — re-exported for internal use
    _classify_deviation,  # noqa: F401 — re-exported for internal use
    _normalize_band_energies,  # noqa: F401 — re-exported for internal use
    _rate_deviation,  # noqa: F401 — re-exported for internal use
    _rate_deviation_ref,  # noqa: F401 — re-exported for internal use
    _rate_range_deviation,  # noqa: F401 — re-exported for internal use
    _unmeasurable_deviation,  # noqa: F401 — re-exported for internal use
)
from phantom.comparison.profile import compare_to_profile
from phantom.comparison.reference import compare_to_reference
from phantom.comparison.match import match_to_reference

__all__ = [
    "compare_to_profile",
    "compare_to_reference",
    "match_to_reference",
    "DeviationResult",
    "RangeDeviationResult",
    "MonoBelowResult",
    "ProfileComparisonResult",
    "ReferenceComparisonResult",
    "MatchResult",
    "MatchAdjustments",
    "MetricDiff",
    "LoudnessProfileComparisonSection",
    "DynamicsComparisonSection",
    "StereoProfileComparisonSection",
    "LoudnessReferenceComparisonSection",
    "DynamicsReferenceComparisonSection",
    "StereoReferenceComparisonSection",
]
