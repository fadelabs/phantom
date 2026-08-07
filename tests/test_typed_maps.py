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

    def test_subscript_is_deliberately_unsupported(self) -> None:
        m = PerBandCorrelation(sub=0.9)
        with pytest.raises(TypeError):
            m["sub"]  # noqa: B018


class TestOctaveBandEnergyDb:
    def test_full_dump_matches_band_label_order(self) -> None:
        energies = {label: -10.0 * i for i, label in enumerate(_BAND_LABELS)}
        result = SpectralResult(octave_band_energy_db=energies)
        dumped = result.model_dump()["octave_band_energy_db"]
        assert list(dumped) == list(_BAND_LABELS)
        assert dumped == energies

    def test_extra_key_passes_through(self) -> None:
        # Non-canonical keys (custom profiles, the "31.25" test-key idiom)
        # survive as extras with their values intact.
        m = OctaveBandEnergyDb.model_validate({"250_hz": -8.1, "31.25": -40.12})
        dumped = m.model_dump()
        assert dumped == {"250_hz": -8.1, "31.25": -40.12}

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
        for key, dev in m.items():
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
