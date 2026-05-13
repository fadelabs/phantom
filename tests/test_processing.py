"""Tests for the corrective audio processing module.

Covers: Recipe system, apply_processing, output path logic,
dependency guard, and unfixable problem type skipping.
"""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
import soundfile as sf

from phantom.exceptions import AnalysisError, DependencyMissingError


# ---------------------------------------------------------------------------
# TestRecipes -- FIX-01: Recipe maps problem type to Pedalboard chain
# ---------------------------------------------------------------------------


class TestRecipes:
    """Each fixable problem type maps to a Recipe with correct plugin chain."""

    def test_recipes_dict_has_six_entries(self):
        from phantom.processing import RECIPES

        assert len(RECIPES) == 6
        expected = {"mud", "harshness", "hum", "sibilance", "dc_offset", "resonant_peak"}
        assert set(RECIPES.keys()) == expected

    def test_recipe_mud_returns_two_plugins(self):
        import pedalboard as pb
        from phantom.processing import RECIPES

        chain = RECIPES["mud"].build_chain({})
        assert len(chain) == 2
        assert isinstance(chain[0], pb.HighpassFilter)
        assert isinstance(chain[1], pb.LowShelfFilter)
        # Verify parameters
        assert chain[0].cutoff_frequency_hz == pytest.approx(80.0)
        assert chain[1].cutoff_frequency_hz == pytest.approx(300.0)
        assert chain[1].gain_db == pytest.approx(-4.0)

    def test_recipe_harshness_returns_one_peak_filter(self):
        import pedalboard as pb
        from phantom.processing import RECIPES

        chain = RECIPES["harshness"].build_chain({})
        assert len(chain) == 1
        assert isinstance(chain[0], pb.PeakFilter)
        assert chain[0].cutoff_frequency_hz == pytest.approx(3000.0)
        assert chain[0].gain_db == pytest.approx(-4.0)
        assert chain[0].q == pytest.approx(1.5)

    def test_recipe_hum_creates_notch_per_frequency(self):
        import pedalboard as pb
        from phantom.processing import RECIPES

        details = {"frequencies_hz": [60.0, 120.0, 180.0]}
        chain = RECIPES["hum"].build_chain(details)
        assert len(chain) == 3
        for plugin in chain:
            assert isinstance(plugin, pb.PeakFilter)
            assert plugin.gain_db == pytest.approx(-30.0)
            assert plugin.q == pytest.approx(30.0)
        assert chain[0].cutoff_frequency_hz == pytest.approx(60.0)
        assert chain[1].cutoff_frequency_hz == pytest.approx(120.0)
        assert chain[2].cutoff_frequency_hz == pytest.approx(180.0)

    def test_recipe_sibilance_returns_one_peak_filter(self):
        import pedalboard as pb
        from phantom.processing import RECIPES

        chain = RECIPES["sibilance"].build_chain({})
        assert len(chain) == 1
        assert isinstance(chain[0], pb.PeakFilter)
        assert chain[0].cutoff_frequency_hz == pytest.approx(7000.0)
        assert chain[0].gain_db == pytest.approx(-5.0)

    def test_recipe_dc_offset_returns_highpass(self):
        import pedalboard as pb
        from phantom.processing import RECIPES

        chain = RECIPES["dc_offset"].build_chain({})
        assert len(chain) == 1
        assert isinstance(chain[0], pb.HighpassFilter)
        assert chain[0].cutoff_frequency_hz == pytest.approx(5.0)

    def test_recipe_resonant_peak_uses_detected_values(self):
        import pedalboard as pb
        from phantom.processing import RECIPES

        details = {
            "resonances": [{"frequency_hz": 301.5, "q_factor": 15.2}]
        }
        chain = RECIPES["resonant_peak"].build_chain(details)
        assert len(chain) == 1
        assert isinstance(chain[0], pb.PeakFilter)
        assert chain[0].cutoff_frequency_hz == pytest.approx(301.5)
        assert chain[0].gain_db == pytest.approx(-6.0)
        assert chain[0].q == pytest.approx(15.2)

    def test_recipe_dataclass_fields(self):
        from phantom.processing import RECIPES

        recipe = RECIPES["mud"]
        assert recipe.problem_type == "mud"
        assert isinstance(recipe.description, str)
        assert len(recipe.description) > 0
        assert callable(recipe.build_chain)


# ---------------------------------------------------------------------------
# TestUnfixable -- FIX-09: Unfixable problem types are skipped gracefully
# ---------------------------------------------------------------------------


class TestUnfixable:
    """Unfixable problem types have no recipe entry."""

    def test_unfixable_types_frozenset(self):
        from phantom.processing import UNFIXABLE_TYPES

        expected = {"clipping", "inter_sample_peak", "noise_floor", "snr", "lossy_codec"}
        assert UNFIXABLE_TYPES == expected

    def test_unfixable_types_not_in_recipes(self):
        from phantom.processing import RECIPES, UNFIXABLE_TYPES

        for ptype in UNFIXABLE_TYPES:
            assert ptype not in RECIPES


# ---------------------------------------------------------------------------
# TestOutputPath -- FIX-03: Output path uses _fixed suffix, never overwrites input
# ---------------------------------------------------------------------------


class TestOutputPath:
    """Output path logic: default suffix, custom path, same-path guard."""

    def test_default_output_path_adds_fixed_suffix(self):
        from phantom.processing import _resolve_output_path

        result = _resolve_output_path("/audio/song.wav", None)
        assert result == "/audio/song_fixed.wav"

    def test_custom_output_path_used(self):
        from phantom.processing import _resolve_output_path

        result = _resolve_output_path("/audio/song.wav", "/output/custom.wav")
        assert result == "/output/custom.wav"

    def test_same_path_raises_analysis_error(self, tmp_path):
        from phantom.processing import _resolve_output_path

        # Create a real file so realpath resolution works
        wav = tmp_path / "song.wav"
        wav.touch()
        with pytest.raises(AnalysisError, match="output.*input"):
            _resolve_output_path(str(wav), str(wav))


# ---------------------------------------------------------------------------
# TestModels -- FixResult and FixComparison Pydantic models
# ---------------------------------------------------------------------------


class TestModels:
    """FixResult and FixComparison Pydantic models are correctly defined."""

    def test_fix_comparison_fields(self):
        from phantom.processing import FixComparison

        fc = FixComparison(
            problem_type="mud",
            before_severity="warning",
            after_severity=None,
            status="resolved",
        )
        assert fc.problem_type == "mud"
        assert fc.before_severity == "warning"
        assert fc.after_severity is None
        assert fc.status == "resolved"

    def test_fix_result_fields(self):
        from phantom.processing import FixResult

        fr = FixResult(
            output_path="/out/file.wav",
            fixes_applied=["mud", "harshness"],
            before=None,
            after=None,
            improvements=[],
            regressions=[],
        )
        assert fr.output_path == "/out/file.wav"
        assert fr.fixes_applied == ["mud", "harshness"]
        assert fr.before is None
        assert fr.after is None
        assert fr.improvements == []
        assert fr.regressions == []


# ---------------------------------------------------------------------------
# TestDependencyGuard -- FIX-05: DependencyMissingError when pedalboard unavailable
# ---------------------------------------------------------------------------


class TestDependencyGuard:
    """DependencyMissingError raised when pedalboard is not installed."""

    def test_apply_processing_raises_without_pedalboard(self, monkeypatch):
        import builtins
        import sys

        # Remove pedalboard from sys.modules
        monkeypatch.delitem(sys.modules, "pedalboard", raising=False)

        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "pedalboard":
                raise ImportError("No module named 'pedalboard'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _mock_import)

        from phantom.processing import apply_processing

        with pytest.raises(DependencyMissingError) as exc_info:
            apply_processing("any.wav", [{"type": "Gain", "gain_db": 0.0}], "out.wav")
        assert "Pedalboard" in str(exc_info.value)
        assert "processing" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TestApplyProcessing -- apply_processing function
# ---------------------------------------------------------------------------


class TestApplyProcessing:
    """apply_processing validates operations, processes audio, returns FixResult."""

    def test_invalid_operation_type_raises(self, tmp_path):
        """Invalid operation type raises AnalysisError."""
        # Create a valid WAV file
        sr = 44100
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        samples_2d = np.column_stack([samples, samples])
        input_path = str(tmp_path / "input.wav")
        sf.write(input_path, samples_2d, sr)

        from phantom.processing import apply_processing

        output_path = str(tmp_path / "output.wav")
        with pytest.raises(AnalysisError, match="Evil"):
            apply_processing(input_path, [{"type": "Evil"}], output_path)

    def test_valid_operation_produces_output(self, tmp_path):
        """Valid operations produce a WAV file and return FixResult."""
        sr = 44100
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        samples_2d = np.column_stack([samples, samples])
        input_path = str(tmp_path / "input.wav")
        output_path = str(tmp_path / "output.wav")
        sf.write(input_path, samples_2d, sr)

        from phantom.processing import apply_processing, FixResult

        result = apply_processing(
            input_path,
            [{"type": "HighpassFilter", "cutoff_frequency_hz": 80}],
            output_path,
        )
        assert isinstance(result, FixResult)
        assert result.output_path == output_path
        assert os.path.isfile(output_path)
        assert "custom" in result.fixes_applied

    def test_output_is_valid_audio(self, tmp_path):
        """Output WAV is readable and has same duration/channels as input."""
        sr = 44100
        duration = 0.5
        n = int(sr * duration)
        t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        samples_2d = np.column_stack([samples, samples])
        input_path = str(tmp_path / "input.wav")
        output_path = str(tmp_path / "output.wav")
        sf.write(input_path, samples_2d, sr)

        from phantom.processing import apply_processing

        apply_processing(
            input_path,
            [{"type": "Gain", "gain_db": -1.0}],
            output_path,
        )
        out_data, out_sr = sf.read(output_path, dtype="float32", always_2d=True)
        assert out_sr == sr
        assert out_data.shape[1] == 2  # stereo preserved
        assert out_data.shape[0] == n  # same length

    def test_output_path_same_as_input_raises(self, tmp_path):
        """Raises AnalysisError if output_path resolves to input_path."""
        sr = 44100
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        samples_2d = np.column_stack([samples, samples])
        path = str(tmp_path / "song.wav")
        sf.write(path, samples_2d, sr)

        from phantom.processing import apply_processing

        with pytest.raises(AnalysisError, match="output.*input"):
            apply_processing(path, [{"type": "Gain", "gain_db": 0.0}], path)

    def test_allowed_operations_dict_exists(self):
        """ALLOWED_OPERATIONS maps string names to classes."""
        from phantom.processing import ALLOWED_OPERATIONS

        expected_keys = {
            "HighpassFilter",
            "LowpassFilter",
            "PeakFilter",
            "HighShelfFilter",
            "LowShelfFilter",
            "Compressor",
            "Limiter",
            "Gain",
            "NoiseGate",
        }
        assert set(ALLOWED_OPERATIONS.keys()) == expected_keys
