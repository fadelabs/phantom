"""Serialization round-trip tests for Pydantic response models.

Per D-04: Verify that model.model_dump() produces the exact same dict
structure MCP clients currently receive. Catches field name mismatches
or unexpected nesting before reaching clients.
"""

from __future__ import annotations

import pytest

from phantom.spectral import SpectralResult
from phantom.loudness import LoudnessResult
from phantom.dynamics import DynamicsResult
from phantom.stereo import StereoResult, PanoramaDistribution
from phantom.phase import PhaseResult, PhaseCompareResult
from phantom.problems import ProblemsResult, ProblemItem, ProblemSummary
from phantom.masking import MaskingResult, MaskingBand, MaskingMatrixResult, MaskingPair
from phantom.comparison import (
    DeviationResult,
    RangeDeviationResult,
    MonoBelowResult,
    ProfileComparisonResult,
    ReferenceComparisonResult,
    MatchResult,
    LoudnessProfileComparisonSection,
    DynamicsComparisonSection,
    StereoProfileComparisonSection,
    LoudnessReferenceComparisonSection,
    DynamicsReferenceComparisonSection,
    StereoReferenceComparisonSection,
    MetricDiff,
    MatchAdjustments,
    _rate_deviation,
)
from phantom._rounding import round_hz, round_ratio
from phantom.separation import SeparationResult


# ---------------------------------------------------------------------------
# SpectralResult
# ---------------------------------------------------------------------------


class TestSpectralResultSerialization:
    def test_keys_match_expected(self):
        result = SpectralResult(
            spectral_centroid_hz=440.0,
            spectral_rolloff_hz=8000.0,
            spectral_flatness=0.1234,
            spectral_contrast=[1.2345, 2.3456],
            dissonance=0.4568,
            octave_band_energy_db={"31.25": -40.12, "62.5": -35.68},
        )
        d = result.model_dump()
        assert set(d.keys()) == {
            "spectral_centroid_hz",
            "spectral_rolloff_hz",
            "spectral_flatness",
            "spectral_contrast",
            "dissonance",
            "octave_band_energy_db",
        }

    def test_precision_enforcement(self):
        result = SpectralResult(
            spectral_centroid_hz=440.123456,
            spectral_rolloff_hz=8000.789012,
            spectral_flatness=0.123456789,
            dissonance=0.987654321,
            spectral_contrast=[1.23456789, 2.34567890],
            octave_band_energy_db={"31.25": -40.123456},
        )
        d = result.model_dump()
        # Hz fields: 1dp
        assert d["spectral_centroid_hz"] == 440.1
        assert d["spectral_rolloff_hz"] == 8000.8
        # Ratio fields: 4dp
        assert d["spectral_flatness"] == 0.1235
        assert d["dissonance"] == 0.9877
        # Contrast list: 4dp (ratio_list)
        assert d["spectral_contrast"] == [1.2346, 2.3457]
        # dB dict: 2dp
        assert d["octave_band_energy_db"]["31.25"] == -40.12

    def test_none_fields_serialize(self):
        result = SpectralResult()
        d = result.model_dump()
        assert d["spectral_centroid_hz"] is None
        assert d["spectral_rolloff_hz"] is None
        assert d["spectral_flatness"] is None
        assert d["spectral_contrast"] is None
        assert d["dissonance"] is None
        assert d["octave_band_energy_db"] is None


# ---------------------------------------------------------------------------
# LoudnessResult
# ---------------------------------------------------------------------------


class TestLoudnessResultSerialization:
    def test_keys_match_expected(self):
        result = LoudnessResult(
            integrated_lufs=-14.0,
            true_peak_dbtp=-1.0,
            loudness_range_lu=8.0,
            short_term_lufs=[-14.0, -13.5],
            momentary_lufs=[-12.0, -11.5],
        )
        d = result.model_dump()
        assert set(d.keys()) == {
            "integrated_lufs",
            "true_peak_dbtp",
            "loudness_range_lu",
            "short_term_lufs",
            "momentary_lufs",
        }

    def test_precision_enforcement(self):
        result = LoudnessResult(
            integrated_lufs=-14.12345,
            true_peak_dbtp=-1.56789,
            loudness_range_lu=8.99999,
            short_term_lufs=[-14.12345, -13.56789],
            momentary_lufs=[-12.12345, -11.56789],
        )
        d = result.model_dump()
        # All dB: 2dp
        assert d["integrated_lufs"] == -14.12
        assert d["true_peak_dbtp"] == -1.57
        assert d["loudness_range_lu"] == 9.0
        # Lists: 2dp each element
        assert d["short_term_lufs"] == [-14.12, -13.57]
        assert d["momentary_lufs"] == [-12.12, -11.57]

    def test_none_fields_serialize(self):
        result = LoudnessResult()
        d = result.model_dump()
        assert d["integrated_lufs"] is None
        assert d["true_peak_dbtp"] is None
        assert d["loudness_range_lu"] is None
        assert d["short_term_lufs"] is None
        assert d["momentary_lufs"] is None


# ---------------------------------------------------------------------------
# DynamicsResult
# ---------------------------------------------------------------------------


class TestDynamicsResultSerialization:
    def test_keys_match_expected(self):
        result = DynamicsResult(
            rms_dbfs=-18.0,
            peak_dbfs=-0.5,
            crest_factor_db=17.5,
            crest_factor_is_low=False,
            dynamic_range_db=12.0,
            dynamic_complexity=0.3456,
            loudness_db=-14.0,
        )
        d = result.model_dump()
        assert set(d.keys()) == {
            "rms_dbfs",
            "peak_dbfs",
            "crest_factor_db",
            "crest_factor_is_low",
            "dynamic_range_db",
            "dynamic_complexity",
            "loudness_db",
        }

    def test_precision_enforcement(self):
        result = DynamicsResult(
            rms_dbfs=-18.12345,
            peak_dbfs=-0.56789,
            crest_factor_db=17.54321,
            crest_factor_is_low=True,
            dynamic_range_db=12.98765,
            dynamic_complexity=0.345678,
            loudness_db=-14.12345,
        )
        d = result.model_dump()
        # dB fields: 2dp
        assert d["rms_dbfs"] == -18.12
        assert d["peak_dbfs"] == -0.57
        assert d["crest_factor_db"] == 17.54
        assert d["dynamic_range_db"] == 12.99
        assert d["loudness_db"] == -14.12
        # Ratio: 4dp
        assert d["dynamic_complexity"] == 0.3457
        # Bool unchanged
        assert d["crest_factor_is_low"] is True

    def test_none_fields_serialize(self):
        result = DynamicsResult()
        d = result.model_dump()
        assert d["rms_dbfs"] is None
        assert d["peak_dbfs"] is None
        assert d["crest_factor_db"] is None
        assert d["crest_factor_is_low"] is None
        assert d["dynamic_range_db"] is None
        assert d["dynamic_complexity"] is None
        assert d["loudness_db"] is None


# ---------------------------------------------------------------------------
# StereoResult / PanoramaDistribution
# ---------------------------------------------------------------------------


class TestPanoramaDistributionSerialization:
    def test_keys_match_expected(self):
        result = PanoramaDistribution(left=30.0, center=40.0, right=30.0)
        d = result.model_dump()
        assert set(d.keys()) == {"left", "center", "right"}

    def test_precision_enforcement(self):
        result = PanoramaDistribution(left=30.12345, center=40.56789, right=29.30866)
        d = result.model_dump()
        # Percentages: 1dp
        assert d["left"] == 30.1
        assert d["center"] == 40.6
        assert d["right"] == 29.3


class TestStereoResultSerialization:
    def test_keys_match_expected(self):
        result = StereoResult(
            correlation=0.9,
            stereo_width=0.3,
            mid_side_ratio_db=6.0,
            balance_db=-0.5,
            panorama_pct=PanoramaDistribution(left=30.0, center=40.0, right=30.0),
        )
        d = result.model_dump()
        assert set(d.keys()) == {
            "correlation",
            "stereo_width",
            "mid_side_ratio_db",
            "balance_db",
            "panorama_pct",
        }

    def test_precision_enforcement(self):
        result = StereoResult(
            correlation=0.912345,
            stereo_width=0.312345,
            mid_side_ratio_db=6.12345,
            balance_db=-0.56789,
            panorama_pct=PanoramaDistribution(left=30.12, center=40.56, right=29.32),
        )
        d = result.model_dump()
        # Ratio: 4dp
        assert d["correlation"] == 0.9123
        assert d["stereo_width"] == 0.3123
        # dB: 2dp
        assert d["mid_side_ratio_db"] == 6.12
        assert d["balance_db"] == -0.57
        # Nested panorama: 1dp
        assert d["panorama_pct"]["left"] == 30.1
        assert d["panorama_pct"]["center"] == 40.6
        assert d["panorama_pct"]["right"] == 29.3

    def test_none_fields_serialize(self):
        result = StereoResult()
        d = result.model_dump()
        assert d["correlation"] is None
        assert d["stereo_width"] is None
        assert d["mid_side_ratio_db"] is None
        assert d["balance_db"] is None
        assert d["panorama_pct"] is None

    def test_nested_panorama_is_dict(self):
        """model_dump() should serialize nested PanoramaDistribution as a dict."""
        result = StereoResult(
            panorama_pct=PanoramaDistribution(left=25.0, center=50.0, right=25.0),
        )
        d = result.model_dump()
        assert isinstance(d["panorama_pct"], dict)
        assert d["panorama_pct"]["left"] == 25.0
        assert d["panorama_pct"]["center"] == 50.0
        assert d["panorama_pct"]["right"] == 25.0


# ---------------------------------------------------------------------------
# PhaseResult
# ---------------------------------------------------------------------------


class TestPhaseResultSerialization:
    def test_keys_match_expected(self):
        result = PhaseResult(
            phase_correlation=0.95,
            per_band_correlation={"low": 0.99, "mid": 0.85},
            polarity_inverted=False,
        )
        d = result.model_dump()
        assert set(d.keys()) == {
            "phase_correlation",
            "per_band_correlation",
            "polarity_inverted",
        }

    def test_precision_enforcement(self):
        result = PhaseResult(
            phase_correlation=0.951234567,
            per_band_correlation={"low": 0.991234567, "mid": 0.856789012},
            polarity_inverted=False,
        )
        d = result.model_dump()
        # Ratio: 4dp
        assert d["phase_correlation"] == 0.9512
        assert d["per_band_correlation"]["low"] == 0.9912
        assert d["per_band_correlation"]["mid"] == 0.8568

    def test_none_fields_serialize(self):
        result = PhaseResult()
        d = result.model_dump()
        assert d["phase_correlation"] is None
        assert d["per_band_correlation"] is None
        assert d["polarity_inverted"] is None


# ---------------------------------------------------------------------------
# PhaseCompareResult
# ---------------------------------------------------------------------------


class TestPhaseCompareResultSerialization:
    def test_keys_match_expected(self):
        result = PhaseCompareResult(
            delay_samples=10,
            delay_ms=0.23,
            correlation=0.95,
            polarity_inverted=False,
        )
        d = result.model_dump()
        assert set(d.keys()) == {
            "delay_samples",
            "delay_ms",
            "correlation",
            "polarity_inverted",
        }

    def test_precision_enforcement(self):
        result = PhaseCompareResult(
            delay_samples=10,
            delay_ms=0.23456,
            correlation=0.951234567,
            polarity_inverted=True,
        )
        d = result.model_dump()
        # delay_ms uses round_db (2dp)
        assert d["delay_ms"] == 0.23
        # correlation: 4dp (ratio)
        assert d["correlation"] == 0.9512
        # int unchanged
        assert d["delay_samples"] == 10
        # bool unchanged
        assert d["polarity_inverted"] is True

    def test_none_fields_serialize(self):
        result = PhaseCompareResult()
        d = result.model_dump()
        assert d["delay_samples"] is None
        assert d["delay_ms"] is None
        assert d["correlation"] is None
        assert d["polarity_inverted"] is None


# ---------------------------------------------------------------------------
# ProblemsResult / ProblemItem / ProblemSummary
# ---------------------------------------------------------------------------


class TestProblemItemSerialization:
    def test_keys_match_expected(self):
        item = ProblemItem(
            type="clipping",
            severity="dealbreaker",
            message="Clipping detected at 5 locations",
            details={"count": 5, "locations": [100, 200]},
        )
        d = item.model_dump()
        assert set(d.keys()) == {"type", "severity", "message", "details"}

    def test_details_dict_preserved(self):
        item = ProblemItem(
            type="dc_offset",
            severity="moderate",
            message="DC offset of 0.01",
            details={"offset": 0.01, "channel": "left"},
        )
        d = item.model_dump()
        assert d["details"] == {"offset": 0.01, "channel": "left"}


class TestProblemSummarySerialization:
    def test_keys_match_expected(self):
        summary = ProblemSummary(
            dealbreaker=1, significant=2, moderate=0, minor=3, total=6
        )
        d = summary.model_dump()
        assert set(d.keys()) == {
            "dealbreaker",
            "significant",
            "moderate",
            "minor",
            "total",
        }

    def test_defaults_serialize(self):
        summary = ProblemSummary()
        d = summary.model_dump()
        assert d == {
            "dealbreaker": 0,
            "significant": 0,
            "moderate": 0,
            "minor": 0,
            "total": 0,
        }


class TestProblemsResultSerialization:
    def test_keys_match_expected(self):
        result = ProblemsResult(
            problems=[
                ProblemItem(
                    type="clipping",
                    severity="dealbreaker",
                    message="Clipping detected",
                    details={"count": 5},
                )
            ],
            clean=False,
            summary=ProblemSummary(dealbreaker=1, total=1),
        )
        d = result.model_dump()
        assert set(d.keys()) == {"problems", "clean", "summary"}

    def test_nested_structures_serialize_as_dicts(self):
        item = ProblemItem(
            type="hum",
            severity="moderate",
            message="Mains hum at 60Hz",
            details={"frequency": 60},
        )
        result = ProblemsResult(
            problems=[item],
            clean=False,
            summary=ProblemSummary(moderate=1, total=1),
        )
        d = result.model_dump()
        assert isinstance(d["problems"], list)
        assert isinstance(d["problems"][0], dict)
        assert d["problems"][0]["type"] == "hum"
        assert isinstance(d["summary"], dict)
        assert d["summary"]["moderate"] == 1

    def test_clean_default_serialization(self):
        result = ProblemsResult()
        d = result.model_dump()
        assert d["problems"] == []
        assert d["clean"] is True
        assert d["summary"]["total"] == 0


# ---------------------------------------------------------------------------
# MaskingBand / MaskingResult
# ---------------------------------------------------------------------------


class TestMaskingBandSerialization:
    def test_keys_match_expected(self):
        band = MaskingBand(band="250-500", severity="moderate", overlap_score=0.45)
        d = band.model_dump()
        assert set(d.keys()) == {"band", "severity", "overlap_score"}

    def test_precision_enforcement(self):
        band = MaskingBand(band="250-500", severity="moderate", overlap_score=0.456789)
        d = band.model_dump()
        # Ratio: 4dp
        assert d["overlap_score"] == 0.4568


class TestMaskingResultSerialization:
    def test_keys_match_expected(self):
        result = MaskingResult(
            bands=[
                MaskingBand(band="250-500", severity="moderate", overlap_score=0.45)
            ],
            overall_severity="moderate",
            overall_score=0.45,
        )
        d = result.model_dump()
        assert set(d.keys()) == {"bands", "overall_severity", "overall_score"}

    def test_nested_bands_serialize(self):
        result = MaskingResult(
            bands=[
                MaskingBand(band="250-500", severity="moderate", overlap_score=0.45),
                MaskingBand(band="500-1000", severity="minor", overlap_score=0.2),
            ],
            overall_severity="moderate",
            overall_score=0.45,
        )
        d = result.model_dump()
        assert len(d["bands"]) == 2
        assert isinstance(d["bands"][0], dict)
        assert d["bands"][0]["band"] == "250-500"

    def test_precision_enforcement(self):
        result = MaskingResult(
            overall_severity="significant",
            overall_score=0.789012345,
        )
        d = result.model_dump()
        # Ratio: 4dp -- round(0.789012345, 4) == 0.7890; trailing zero dropped by Python
        assert d["overall_score"] == 0.789


# ---------------------------------------------------------------------------
# MaskingPair / MaskingMatrixResult
# ---------------------------------------------------------------------------


class TestMaskingPairSerialization:
    def test_keys_match_expected(self):
        pair = MaskingPair(
            stem_a="stem_0",
            stem_b="stem_1",
            overall_severity="moderate",
            overall_score=0.45,
            bands=[
                MaskingBand(band="250-500", severity="moderate", overlap_score=0.45)
            ],
        )
        d = pair.model_dump()
        assert set(d.keys()) == {
            "stem_a",
            "stem_b",
            "overall_severity",
            "overall_score",
            "bands",
        }

    def test_precision_enforcement(self):
        pair = MaskingPair(
            stem_a="stem_0",
            stem_b="stem_1",
            overall_severity="moderate",
            overall_score=0.456789,
            bands=[],
        )
        d = pair.model_dump()
        assert d["overall_score"] == 0.4568


class TestMaskingMatrixResultSerialization:
    def test_keys_match_expected(self):
        result = MaskingMatrixResult(pairs=[], stem_count=3, pair_count=0)
        d = result.model_dump()
        assert set(d.keys()) == {"pairs", "stem_count", "pair_count"}

    def test_nested_pairs_serialize(self):
        pair = MaskingPair(
            stem_a="stem_0",
            stem_b="stem_1",
            overall_severity="moderate",
            overall_score=0.5,
            bands=[MaskingBand(band="250-500", severity="moderate", overlap_score=0.5)],
        )
        result = MaskingMatrixResult(pairs=[pair], stem_count=2, pair_count=1)
        d = result.model_dump()
        assert len(d["pairs"]) == 1
        assert isinstance(d["pairs"][0], dict)
        assert d["pairs"][0]["stem_a"] == "stem_0"
        assert isinstance(d["pairs"][0]["bands"][0], dict)


# ---------------------------------------------------------------------------
# DeviationResult
# ---------------------------------------------------------------------------


class TestDeviationResultSerialization:
    def test_keys_match_expected(self):
        result = DeviationResult(
            value=-14.0,
            target=-14.0,
            reference=-14.0,
            deviation=0.0,
            rating="on_target",
        )
        d = result.model_dump()
        assert set(d.keys()) == {
            "value",
            "target",
            "reference",
            "deviation",
            "rating",
        }

    def test_no_auto_rounding_on_construction(self):
        """DeviationResult should NOT auto-round values -- rounding is caller's responsibility."""
        result = DeviationResult(
            value=-14.12345,
            target=-14.56789,
            reference=-13.98765,
            deviation=0.44444,
            rating="close",
        )
        # Values should be stored as-is (no field_validator rounding)
        assert result.value == -14.12345
        assert result.target == -14.56789
        assert result.reference == -13.98765
        assert result.deviation == 0.44444

    def test_rate_deviation_with_round_hz(self):
        """_rate_deviation with round_fn=round_hz should round to 1dp."""
        result = _rate_deviation(440.123, 440.0, round_fn=round_hz)
        assert result.value == 440.1
        assert result.target == 440.0
        assert result.deviation == pytest.approx(0.1, abs=0.01)

    def test_rate_deviation_with_round_ratio(self):
        """_rate_deviation with round_fn=round_ratio should round to 4dp."""
        result = _rate_deviation(0.12345, 0.5, round_fn=round_ratio)
        assert result.value == 0.1235
        assert result.target == 0.5
        assert result.deviation == pytest.approx(-0.3765, abs=0.0001)

    def test_rate_deviation_default_rounds_db(self):
        """_rate_deviation with default round_fn rounds to 2dp (dB)."""
        result = _rate_deviation(-14.12345, -14.0)
        assert result.value == -14.12
        assert result.target == -14.0
        assert result.deviation == pytest.approx(-0.12, abs=0.01)

    def test_none_fields_serialize(self):
        result = DeviationResult()
        d = result.model_dump()
        assert d["value"] is None
        assert d["target"] is None
        assert d["reference"] is None
        assert d["deviation"] is None
        assert d["rating"] == "unmeasurable"


# ---------------------------------------------------------------------------
# RangeDeviationResult
# ---------------------------------------------------------------------------


class TestRangeDeviationResultSerialization:
    def test_keys_match_expected(self):
        result = RangeDeviationResult(
            value=8.0,
            target_range=[6.0, 10.0],
            deviation=0.0,
            rating="on_target",
        )
        d = result.model_dump()
        assert set(d.keys()) == {"value", "target_range", "deviation", "rating"}

    def test_no_auto_rounding_on_value_and_deviation(self):
        """RangeDeviationResult should NOT auto-round value/deviation -- caller's responsibility."""
        result = RangeDeviationResult(
            value=8.12345,
            target_range=[6.12345, 10.56789],
            deviation=-1.23456,
            rating="close",
        )
        # value and deviation are stored as-is (no field_validator)
        assert result.value == 8.12345
        assert result.deviation == -1.23456
        # target_range still has its own validator (2dp rounding)
        d = result.model_dump()
        assert d["target_range"] == [6.12, 10.57]

    def test_none_fields_serialize(self):
        result = RangeDeviationResult()
        d = result.model_dump()
        assert d["value"] is None
        assert d["target_range"] is None
        assert d["deviation"] is None
        assert d["rating"] == "unmeasurable"


# ---------------------------------------------------------------------------
# MonoBelowResult
# ---------------------------------------------------------------------------


class TestMonoBelowResultSerialization:
    def test_keys_match_expected(self):
        result = MonoBelowResult(
            mono_below_hz=120.0,
            bass_correlation=0.99,
            has_stereo_bass=False,
            rating="good",
        )
        d = result.model_dump()
        assert set(d.keys()) == {
            "mono_below_hz",
            "bass_correlation",
            "has_stereo_bass",
            "rating",
        }

    def test_precision_enforcement(self):
        result = MonoBelowResult(
            mono_below_hz=120.56789,
            bass_correlation=0.991234567,
            has_stereo_bass=True,
            rating="warning",
        )
        d = result.model_dump()
        # Hz: 1dp
        assert d["mono_below_hz"] == 120.6
        # Ratio: 4dp
        assert d["bass_correlation"] == 0.9912
        # Bool unchanged
        assert d["has_stereo_bass"] is True


# ---------------------------------------------------------------------------
# ProfileComparisonResult
# ---------------------------------------------------------------------------


class TestProfileComparisonResultSerialization:
    def test_keys_match_expected(self):
        result = ProfileComparisonResult(
            loudness=LoudnessProfileComparisonSection(
                integrated_lufs=RangeDeviationResult(
                    value=-12.0,
                    target_range=[-14.0, -8.0],
                    deviation=0.0,
                    rating="on_target",
                ),
                true_peak_dbtp=DeviationResult(
                    value=-1.0, target=-1.0, deviation=0.0, rating="on_target"
                ),
            ),
            frequency={
                "500_hz": DeviationResult(
                    value=0.0, target=0.0, deviation=0.0, rating="on_target"
                )
            },
            dynamics=DynamicsComparisonSection(
                crest_factor_db=RangeDeviationResult(
                    value=10.0,
                    target_range=[6.0, 12.0],
                    deviation=0.0,
                    rating="on_target",
                ),
            ),
            stereo=StereoProfileComparisonSection(
                width=RangeDeviationResult(
                    value=0.5,
                    target_range=[0.3, 0.7],
                    deviation=0.0,
                    rating="on_target",
                ),
                mono_below=MonoBelowResult(
                    mono_below_hz=120.0,
                    bass_correlation=0.99,
                    has_stereo_bass=False,
                    rating="on_target",
                ),
            ),
        )
        d = result.model_dump()
        assert set(d.keys()) == {"loudness", "frequency", "dynamics", "stereo"}

    def test_typed_loudness_section_serializes(self):
        """Typed loudness section model_dump produces nested dict with correct keys."""
        section = LoudnessProfileComparisonSection(
            integrated_lufs=RangeDeviationResult(
                value=-12.0,
                target_range=[-14.0, -8.0],
                deviation=0.0,
                rating="on_target",
            ),
            true_peak_dbtp=DeviationResult(
                value=-1.0, target=-1.0, deviation=0.0, rating="on_target"
            ),
        )
        result = ProfileComparisonResult(loudness=section)
        d = result.model_dump()
        assert "integrated_lufs" in d["loudness"]
        assert "true_peak_dbtp" in d["loudness"]
        assert d["loudness"]["integrated_lufs"]["value"] == -12.0

    def test_none_fields_serialize(self):
        result = ProfileComparisonResult()
        d = result.model_dump()
        assert d["loudness"] is None
        assert d["frequency"] is None
        assert d["dynamics"] is None
        assert d["stereo"] is None

    def test_serialization_round_trip(self):
        """ProfileComparisonResult -> model_dump() -> reconstruct -> identical."""
        section = LoudnessProfileComparisonSection(
            integrated_lufs=RangeDeviationResult(
                value=-12.0,
                target_range=[-14.0, -8.0],
                deviation=0.0,
                rating="on_target",
            ),
            true_peak_dbtp=DeviationResult(
                value=-1.0, target=-1.0, deviation=0.0, rating="on_target"
            ),
        )
        original = ProfileComparisonResult(loudness=section)
        d = original.model_dump()
        reconstructed = ProfileComparisonResult(**d)
        assert reconstructed.model_dump() == d


# ---------------------------------------------------------------------------
# ReferenceComparisonResult
# ---------------------------------------------------------------------------


class TestReferenceComparisonResultSerialization:
    def test_keys_match_expected(self):
        result = ReferenceComparisonResult(
            loudness=LoudnessReferenceComparisonSection(
                integrated_lufs=DeviationResult(
                    value=-14.0, reference=-14.0, deviation=0.0, rating="on_target"
                ),
                true_peak_dbtp=DeviationResult(
                    value=-1.0, reference=-1.0, deviation=0.0, rating="on_target"
                ),
                loudness_range_lu=DeviationResult(
                    value=8.0, reference=8.0, deviation=0.0, rating="on_target"
                ),
            ),
            frequency={
                "500_hz": DeviationResult(
                    value=0.0, reference=0.0, deviation=0.0, rating="on_target"
                )
            },
            dynamics=DynamicsReferenceComparisonSection(
                rms_dbfs=DeviationResult(
                    value=-18.0, reference=-18.0, deviation=0.0, rating="on_target"
                ),
                crest_factor_db=DeviationResult(
                    value=10.0, reference=10.0, deviation=0.0, rating="on_target"
                ),
                dynamic_range_db=DeviationResult(
                    value=20.0, reference=20.0, deviation=0.0, rating="on_target"
                ),
            ),
            stereo=StereoReferenceComparisonSection(
                correlation=DeviationResult(
                    value=0.9, reference=0.9, deviation=0.0, rating="on_target"
                ),
                stereo_width=DeviationResult(
                    value=0.5, reference=0.5, deviation=0.0, rating="on_target"
                ),
            ),
        )
        d = result.model_dump()
        assert set(d.keys()) == {"loudness", "frequency", "dynamics", "stereo"}

    def test_none_fields_serialize(self):
        result = ReferenceComparisonResult()
        d = result.model_dump()
        assert d["loudness"] is None
        assert d["frequency"] is None
        assert d["dynamics"] is None
        assert d["stereo"] is None

    def test_serialization_round_trip(self):
        """ReferenceComparisonResult -> model_dump() -> reconstruct -> identical."""
        original = ReferenceComparisonResult(
            loudness=LoudnessReferenceComparisonSection(
                integrated_lufs=DeviationResult(
                    value=-14.0, reference=-14.0, deviation=0.0, rating="on_target"
                ),
                true_peak_dbtp=DeviationResult(
                    value=-1.0, reference=-1.0, deviation=0.0, rating="on_target"
                ),
                loudness_range_lu=DeviationResult(
                    value=8.0, reference=8.0, deviation=0.0, rating="on_target"
                ),
            ),
        )
        d = original.model_dump()
        reconstructed = ReferenceComparisonResult(**d)
        assert reconstructed.model_dump() == d


# ---------------------------------------------------------------------------
# SeparationResult
# ---------------------------------------------------------------------------


class TestSeparationResultSerialization:
    def test_keys_match_expected(self):
        result = SeparationResult(
            stems={"vocals": "/out/vocals.wav", "drums": "/out/drums.wav"}
        )
        d = result.model_dump()
        assert set(d.keys()) == {"stems"}

    def test_stems_dict_preserved(self):
        stems_data = {
            "vocals": "/out/vocals.wav",
            "drums": "/out/drums.wav",
            "bass": "/out/bass.wav",
            "other": "/out/other.wav",
        }
        result = SeparationResult(stems=stems_data)
        d = result.model_dump()
        assert d["stems"] == stems_data


# ---------------------------------------------------------------------------
# MatchResult
# ---------------------------------------------------------------------------


class TestMatchResultSerialization:
    def test_keys_match_expected(self):
        result = MatchResult(
            output_path="/out/matched.wav",
            adjustments=MatchAdjustments(
                integrated_lufs=MetricDiff(before=-14.0, after=-13.5, change=0.5),
                true_peak_dbtp=MetricDiff(before=-1.0, after=-0.8, change=0.2),
                spectral_change_db={},
            ),
        )
        d = result.model_dump()
        assert set(d.keys()) == {"output_path", "adjustments"}

    def test_nested_adjustments_preserved(self):
        adjustments = MatchAdjustments(
            integrated_lufs=MetricDiff(before=-14.0, after=-13.5, change=0.5),
            true_peak_dbtp=MetricDiff(before=-1.0, after=-0.8, change=0.2),
            spectral_change_db={
                "500_hz": MetricDiff(before=-10.0, after=-9.5, change=0.5)
            },
        )
        result = MatchResult(output_path="/out/matched.wav", adjustments=adjustments)
        d = result.model_dump()
        assert d["output_path"] == "/out/matched.wav"
        assert d["adjustments"]["integrated_lufs"]["before"] == -14.0
        assert d["adjustments"]["spectral_change_db"]["500_hz"]["change"] == 0.5


# ---------------------------------------------------------------------------
# MetricDiff
# ---------------------------------------------------------------------------


class TestMetricDiffSerialization:
    def test_keys_match_expected(self):
        result = MetricDiff(before=-14.0, after=-13.5, change=0.5)
        d = result.model_dump()
        assert set(d.keys()) == {"before", "after", "change"}

    def test_precision_enforcement(self):
        """MetricDiff should round before/after/change to 2dp."""
        result = MetricDiff(before=-14.12345, after=-13.56789, change=0.55556)
        d = result.model_dump()
        assert d["before"] == -14.12
        assert d["after"] == -13.57
        assert d["change"] == 0.56

    def test_none_fields_serialize(self):
        result = MetricDiff()
        d = result.model_dump()
        assert d["before"] is None
        assert d["after"] is None
        assert d["change"] is None


# ---------------------------------------------------------------------------
# LoudnessProfileComparisonSection
# ---------------------------------------------------------------------------


class TestLoudnessProfileComparisonSectionSerialization:
    def test_model_dump_produces_expected_keys(self):
        """LoudnessProfileComparisonSection.model_dump() has integrated_lufs and true_peak_dbtp."""
        section = LoudnessProfileComparisonSection(
            integrated_lufs=RangeDeviationResult(
                value=-12.0,
                target_range=[-14.0, -8.0],
                deviation=0.0,
                rating="on_target",
            ),
            true_peak_dbtp=DeviationResult(
                value=-1.0, target=-1.0, deviation=0.0, rating="on_target"
            ),
        )
        d = section.model_dump()
        assert set(d.keys()) == {"integrated_lufs", "true_peak_dbtp"}
        assert "value" in d["integrated_lufs"]
        assert "target_range" in d["integrated_lufs"]
        assert "value" in d["true_peak_dbtp"]
        assert "target" in d["true_peak_dbtp"]


# ---------------------------------------------------------------------------
# StereoProfileComparisonSection
# ---------------------------------------------------------------------------


class TestStereoProfileComparisonSectionSerialization:
    def test_model_dump_produces_expected_keys(self):
        """StereoProfileComparisonSection has width and mono_below."""
        section = StereoProfileComparisonSection(
            width=RangeDeviationResult(
                value=0.5, target_range=[0.3, 0.7], deviation=0.0, rating="on_target"
            ),
            mono_below=MonoBelowResult(
                mono_below_hz=120.0,
                bass_correlation=0.99,
                has_stereo_bass=False,
                rating="on_target",
            ),
        )
        d = section.model_dump()
        assert set(d.keys()) == {"width", "mono_below"}
        assert "target_range" in d["width"]
        assert "mono_below_hz" in d["mono_below"]


# ---------------------------------------------------------------------------
# Round-trip: construct -> dump -> reconstruct
# ---------------------------------------------------------------------------


class TestRoundTripReconstruction:
    """Verify that model_dump() output can reconstruct the model."""

    def test_spectral_round_trip(self):
        original = SpectralResult(
            spectral_centroid_hz=440.1,
            spectral_rolloff_hz=8000.8,
            spectral_flatness=0.1235,
            dissonance=0.4568,
            octave_band_energy_db={"31.25": -40.12},
        )
        d = original.model_dump()
        reconstructed = SpectralResult(**d)
        assert reconstructed.model_dump() == d

    def test_loudness_round_trip(self):
        original = LoudnessResult(
            integrated_lufs=-14.12,
            true_peak_dbtp=-1.57,
            loudness_range_lu=9.0,
            short_term_lufs=[-14.12, -13.57],
            momentary_lufs=[-12.12, -11.57],
        )
        d = original.model_dump()
        reconstructed = LoudnessResult(**d)
        assert reconstructed.model_dump() == d

    def test_dynamics_round_trip(self):
        original = DynamicsResult(
            rms_dbfs=-18.12,
            peak_dbfs=-0.57,
            crest_factor_db=17.54,
            crest_factor_is_low=True,
            dynamic_range_db=12.99,
            dynamic_complexity=0.3457,
            loudness_db=-14.12,
        )
        d = original.model_dump()
        reconstructed = DynamicsResult(**d)
        assert reconstructed.model_dump() == d

    def test_stereo_round_trip(self):
        original = StereoResult(
            correlation=0.9123,
            stereo_width=0.3123,
            mid_side_ratio_db=6.12,
            balance_db=-0.57,
            panorama_pct=PanoramaDistribution(left=30.1, center=40.6, right=29.3),
        )
        d = original.model_dump()
        reconstructed = StereoResult(**d)
        assert reconstructed.model_dump() == d

    def test_phase_round_trip(self):
        original = PhaseResult(
            phase_correlation=0.9512,
            per_band_correlation={"low": 0.9912, "mid": 0.8568},
            polarity_inverted=False,
        )
        d = original.model_dump()
        reconstructed = PhaseResult(**d)
        assert reconstructed.model_dump() == d

    def test_problems_round_trip(self):
        original = ProblemsResult(
            problems=[
                ProblemItem(
                    type="clipping",
                    severity="dealbreaker",
                    message="Clipping detected",
                    details={"count": 5},
                )
            ],
            clean=False,
            summary=ProblemSummary(dealbreaker=1, total=1),
        )
        d = original.model_dump()
        reconstructed = ProblemsResult(**d)
        assert reconstructed.model_dump() == d

    def test_masking_round_trip(self):
        original = MaskingResult(
            bands=[
                MaskingBand(band="250-500", severity="moderate", overlap_score=0.4568)
            ],
            overall_severity="moderate",
            overall_score=0.4568,
        )
        d = original.model_dump()
        reconstructed = MaskingResult(**d)
        assert reconstructed.model_dump() == d
