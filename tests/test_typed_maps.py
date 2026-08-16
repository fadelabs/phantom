"""Tests for the typed per-band maps and typed details (C.2).

The maps replaced raw string-keyed dicts: serialization must stay
byte-identical (same keys, same nesting, same values), values must be
reachable through typed attributes, and unset bands must be omitted from
dumps exactly as they were from the raw dicts.
"""

from __future__ import annotations

import pytest

from phantom._bands import OctaveBandEnergyDb, _BAND_LABELS
from phantom.comparison import DeviationResult, FrequencyDeviationMap
from phantom.phase import PerBandCorrelation, PhaseResult
from phantom.spectral import SpectralResult


class TestPerBandCorrelation:
    def test_full_dump_matches_band_order(self) -> None:
        result = PhaseResult(
            per_band_correlation={
                "sub": 0.9,
                "low": 0.85,
                "low_mid": 0.7,
                "mid": 0.5,
                "high": 0.3,
                "air": 0.2,
            }
        )
        dumped = result.model_dump()["per_band_correlation"]
        assert list(dumped) == ["sub", "low", "low_mid", "mid", "high", "air"]
        assert dumped["air"] == 0.2

    def test_partial_map_omits_unset_bands(self) -> None:
        # A low sample rate filters bands above Nyquist: the dump carries
        # only the present keys, as the raw dict did.
        result = PhaseResult(per_band_correlation={"sub": 1.0, "low": 1.0})
        assert result.model_dump()["per_band_correlation"] == {
            "sub": 1.0,
            "low": 1.0,
        }

    def test_typed_attribute_access(self) -> None:
        m = PerBandCorrelation(sub=0.9, mid=0.4)
        assert m.sub == 0.9
        assert m.mid == 0.4
        assert m.low_mid is None

    def test_subscript_reads_by_serialized_key(self) -> None:
        m = PerBandCorrelation(sub=0.9, mid=0.4)
        assert m["sub"] == 0.9
        assert m["mid"] == 0.4

    def test_subscript_missing_key_raises_key_error(self) -> None:
        m = PerBandCorrelation(sub=0.9)
        with pytest.raises(KeyError):
            m["air"]


class TestOctaveBandEnergyDb:
    def test_full_dump_matches_band_label_order(self) -> None:
        energies = {label: -10.0 * i for i, label in enumerate(_BAND_LABELS)}
        result = SpectralResult(octave_band_energy_db=energies)
        dumped = result.model_dump()["octave_band_energy_db"]
        assert list(dumped) == list(_BAND_LABELS)
        assert dumped == energies

    def test_extra_key_passes_through(self) -> None:
        # Non-canonical keys (custom profiles, the "31.25" test-key idiom)
        # survive as extras with their values intact, readable by subscript.
        m = OctaveBandEnergyDb.model_validate({"250_hz": -8.1, "31.25": -40.12})
        dumped = m.model_dump()
        assert dumped == {"250_hz": -8.1, "31.25": -40.12}
        assert m["31.25"] == -40.12

    def test_rounding_orders_before_coercion(self) -> None:
        # SpectralResult's _ROUND_FIELDS rounds the incoming dB dict; the
        # typed map carries the rounded value.
        result = SpectralResult(octave_band_energy_db={"250_hz": -12.3456})
        assert result.model_dump()["octave_band_energy_db"] == {"250_hz": -12.35}

    def test_value_round_trip_through_json(self) -> None:
        m = OctaveBandEnergyDb(band_250_hz=-8.1, band_31_hz=-44.95)
        import json

        assert json.loads(m.model_dump_json()) == {"250_hz": -8.1, "31_hz": -44.95}


class TestFrequencyDeviationMap:
    def test_values_stay_typed_in_read_views(self) -> None:
        m = FrequencyDeviationMap.model_validate(
            {
                "250_hz": {
                    "value": -2.0,
                    "target": 0.0,
                    "deviation": -2.0,
                    "rating": "slightly_below",
                }
            }
        )
        band_dev = m.get("250_hz")
        assert isinstance(band_dev, DeviationResult)
        assert band_dev.rating == "slightly_below"
        for dev in m.values():
            assert isinstance(dev, DeviationResult)

    def test_dump_reduces_values_to_plain_dicts(self) -> None:
        m = FrequencyDeviationMap(band_250_hz=DeviationResult(value=-2.0))
        dumped = m.model_dump()
        assert dumped == {
            "250_hz": {
                "value": -2.0,
                "target": None,
                "reference": None,
                "deviation": None,
                "rating": "unmeasurable",
            }
        }


class TestProblemDetails:
    def test_dump_omits_unset_keys_and_keeps_order(self) -> None:
        from phantom.problems import ProblemItem

        item = ProblemItem(
            type="snr",
            severity="minor",
            message="snr low",
            details={
                "snr_db": 55.3,
                "signal_rms_dbfs": -20.1,
                "noise_floor_dbfs": -75.4,
                "quality": "acceptable",
            },
        )
        dumped = item.model_dump()
        assert list(dumped["details"]) == [
            "snr_db",
            "signal_rms_dbfs",
            "noise_floor_dbfs",
            "quality",
        ]
        assert dumped["details"] == {
            "snr_db": 55.3,
            "signal_rms_dbfs": -20.1,
            "noise_floor_dbfs": -75.4,
            "quality": "acceptable",
        }

    def test_partial_details_accepted(self) -> None:
        from phantom.problems import ProblemItem

        # Mono dc_offset carries no channel; construction with a partial
        # detail dict is the norm.
        item = ProblemItem(
            type="dc_offset",
            severity="minor",
            message="dc",
            details={"dc_offset": 0.05},
        )
        assert item.details.dc_offset == 0.05
        assert item.details.channel is None
        assert item.model_dump()["details"] == {"dc_offset": 0.05}

    def test_unknown_key_passes_through(self) -> None:
        from phantom.problems import ProblemItem

        # Forward-compatible detail vocabulary passes through as extras.
        item = ProblemItem(
            type="clipping",
            severity="dealbreaker",
            message="x",
            details={"clipped_samples": 5, "cluster": "main"},
        )
        assert item.details.clipped_samples == 5
        assert item.details.cluster == "main"
        assert item.model_dump()["details"] == {
            "clipped_samples": 5,
            "cluster": "main",
        }

    def test_typed_attribute_access_on_detected_problem(self) -> None:
        from phantom.problems import ProblemDetails

        d = ProblemDetails.model_validate(
            {"clipped_samples": 5, "clipped_percent": 0.5}
        )
        assert d.clipped_samples == 5
        assert d.clipped_percent == 0.5
        assert d.snr_db is None


class TestDictStyleCompat:
    """Subscript access and dict equality (C.2 follow-up): existing square-
    bracket and ==-against-dict call sites keep working. isinstance(x, dict)
    stays False -- the one accepted break."""

    def test_dict_equality_both_directions(self) -> None:
        m = OctaveBandEnergyDb.model_validate({"250_hz": -8.1})
        assert m == {"250_hz": -8.1}
        assert {"250_hz": -8.1} == m

    def test_dict_inequality(self) -> None:
        assert PerBandCorrelation(sub=0.9) != {"sub": 0.8}

    def test_dict_equality_uses_serialized_view_for_models(self) -> None:
        m = FrequencyDeviationMap(band_250_hz=DeviationResult(value=-2.0))
        assert m == {
            "250_hz": {
                "value": -2.0,
                "target": None,
                "reference": None,
                "deviation": None,
                "rating": "unmeasurable",
            }
        }

    def test_model_equality_by_serialized_view(self) -> None:
        a = OctaveBandEnergyDb(band_250_hz=-8.1)
        b = OctaveBandEnergyDb.model_validate({"250_hz": -8.1})
        assert a == b

    def test_details_dict_comparison_and_subscript(self) -> None:
        from phantom.problems import ProblemItem

        item = ProblemItem(
            type="dc_offset",
            severity="minor",
            message="dc",
            details={"dc_offset": 0.05, "channel": "left"},
        )
        assert item.details == {"dc_offset": 0.05, "channel": "left"}
        assert item.details["dc_offset"] == 0.05

    def test_missing_key_dict_comparison_is_false(self) -> None:
        assert PerBandCorrelation(sub=0.9) != {"sub": 0.9, "low": 0.9}

    def test_isinstance_dict_remains_false(self) -> None:
        """The one accepted break: maps are typed models, not dicts."""
        assert not isinstance(OctaveBandEnergyDb(band_250_hz=-8.1), dict)
        assert not isinstance(PerBandCorrelation(sub=0.9), dict)
