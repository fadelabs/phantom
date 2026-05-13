"""Tests for the corrective audio processing module.

Covers: Recipe system, apply_processing, output path logic,
dependency guard, and unfixable problem type skipping.
"""

from __future__ import annotations

import os

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
        expected = {
            "mud",
            "harshness",
            "hum",
            "sibilance",
            "dc_offset",
            "resonant_peak",
        }
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

        details = {"resonances": [{"frequency_hz": 301.5, "q_factor": 15.2}]}
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

        expected = {
            "clipping",
            "inter_sample_peak",
            "noise_floor",
            "snr",
            "lossy_codec",
        }
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


# ---------------------------------------------------------------------------
# TestCompareResults -- Before/after comparison classification
# ---------------------------------------------------------------------------


class TestCompareResults:
    """_compare_results classifies each problem as resolved/improved/unchanged/worsened."""

    def test_resolved_when_problem_gone(self):
        """Problem in before but not in after -> status='resolved'."""
        from phantom.processing import _compare_results
        from phantom.problems import ProblemsResult, ProblemItem

        before = ProblemsResult(
            problems=[
                ProblemItem(
                    type="mud", severity="moderate", message="Mud detected", details={}
                )
            ],
            clean=False,
        )
        after = ProblemsResult(problems=[], clean=True)

        improvements, regressions = _compare_results(before, after)
        assert len(improvements) == 1
        assert len(regressions) == 0
        assert improvements[0].problem_type == "mud"
        assert improvements[0].status == "resolved"
        assert improvements[0].before_severity == "moderate"
        assert improvements[0].after_severity is None

    def test_improved_when_severity_decreased(self):
        """Same problem type with lower severity after -> status='improved'."""
        from phantom.processing import _compare_results
        from phantom.problems import ProblemsResult, ProblemItem

        before = ProblemsResult(
            problems=[
                ProblemItem(
                    type="harshness",
                    severity="significant",
                    message="Harsh",
                    details={},
                )
            ],
            clean=False,
        )
        after = ProblemsResult(
            problems=[
                ProblemItem(
                    type="harshness",
                    severity="minor",
                    message="Mild harshness",
                    details={},
                )
            ],
            clean=False,
        )

        improvements, regressions = _compare_results(before, after)
        assert len(improvements) == 1
        assert improvements[0].status == "improved"
        assert improvements[0].before_severity == "significant"
        assert improvements[0].after_severity == "minor"

    def test_unchanged_when_same_severity(self):
        """Same problem type with same severity -> status='unchanged'."""
        from phantom.processing import _compare_results
        from phantom.problems import ProblemsResult, ProblemItem

        before = ProblemsResult(
            problems=[
                ProblemItem(type="mud", severity="moderate", message="Mud", details={})
            ],
            clean=False,
        )
        after = ProblemsResult(
            problems=[
                ProblemItem(
                    type="mud", severity="moderate", message="Mud still", details={}
                )
            ],
            clean=False,
        )

        improvements, regressions = _compare_results(before, after)
        assert len(improvements) == 0
        assert len(regressions) == 0

    def test_worsened_when_severity_increased(self):
        """Same problem with higher severity after -> status='worsened', in regressions."""
        from phantom.processing import _compare_results
        from phantom.problems import ProblemsResult, ProblemItem

        before = ProblemsResult(
            problems=[
                ProblemItem(type="mud", severity="moderate", message="Mud", details={})
            ],
            clean=False,
        )
        after = ProblemsResult(
            problems=[
                ProblemItem(
                    type="mud",
                    severity="dealbreaker",
                    message="Mud worsened",
                    details={},
                )
            ],
            clean=False,
        )

        improvements, regressions = _compare_results(before, after)
        assert len(improvements) == 0
        assert len(regressions) == 1
        assert regressions[0].problem_type == "mud"
        assert regressions[0].status == "worsened"
        assert regressions[0].after_severity == "dealbreaker"

    def test_multiple_problems_mixed_status(self):
        """Multiple problems with different status outcomes."""
        from phantom.processing import _compare_results
        from phantom.problems import ProblemsResult, ProblemItem

        before = ProblemsResult(
            problems=[
                ProblemItem(type="mud", severity="moderate", message="Mud", details={}),
                ProblemItem(
                    type="harshness",
                    severity="significant",
                    message="Harsh",
                    details={},
                ),
                ProblemItem(type="hum", severity="moderate", message="Hum", details={}),
            ],
            clean=False,
        )
        after = ProblemsResult(
            problems=[
                # mud resolved (not present)
                ProblemItem(
                    type="harshness", severity="minor", message="Mild harsh", details={}
                ),
                ProblemItem(
                    type="hum", severity="dealbreaker", message="Hum worse", details={}
                ),
            ],
            clean=False,
        )

        improvements, regressions = _compare_results(before, after)
        # mud resolved + harshness improved = 2 improvements
        assert len(improvements) == 2
        types_improved = {c.problem_type for c in improvements}
        assert types_improved == {"mud", "harshness"}
        # hum worsened = 1 regression
        assert len(regressions) == 1
        assert regressions[0].problem_type == "hum"

    def test_severity_order_dealbreaker_highest(self):
        """Severity ordering: dealbreaker > significant > moderate > minor."""
        from phantom.processing import _SEVERITY_ORDER

        assert _SEVERITY_ORDER["dealbreaker"] > _SEVERITY_ORDER["significant"]
        assert _SEVERITY_ORDER["significant"] > _SEVERITY_ORDER["moderate"]
        assert _SEVERITY_ORDER["moderate"] > _SEVERITY_ORDER["minor"]


# ---------------------------------------------------------------------------
# TestBuildChainFromProblems -- Signal chain ordering
# ---------------------------------------------------------------------------


class TestBuildChainFromProblems:
    """_build_chain_from_problems orders plugins in signal chain priority."""

    def test_single_problem_returns_recipe_chain(self):
        """Single fixable problem returns its recipe's plugin chain."""
        import pedalboard as pb
        from phantom.processing import _build_chain_from_problems
        from phantom.problems import ProblemItem

        problems = [
            ProblemItem(type="mud", severity="moderate", message="Mud", details={})
        ]
        chain = _build_chain_from_problems(problems)
        assert len(chain) == 2  # HPF + LowShelf from mud recipe
        assert isinstance(chain[0], pb.HighpassFilter)
        assert isinstance(chain[1], pb.LowShelfFilter)

    def test_unfixable_problems_skipped(self):
        """Unfixable problem types produce no plugins."""
        from phantom.processing import _build_chain_from_problems
        from phantom.problems import ProblemItem

        problems = [
            ProblemItem(
                type="clipping", severity="dealbreaker", message="Clipped", details={}
            )
        ]
        chain = _build_chain_from_problems(problems)
        assert len(chain) == 0

    def test_hpf_ordered_before_peak_filters(self):
        """HPF plugins come before peak/shelf plugins in chain."""
        import pedalboard as pb
        from phantom.processing import _build_chain_from_problems
        from phantom.problems import ProblemItem

        # harshness (PeakFilter) + mud (HPF + LowShelf) -- HPF should come first
        problems = [
            ProblemItem(
                type="harshness", severity="moderate", message="Harsh", details={}
            ),
            ProblemItem(type="mud", severity="moderate", message="Mud", details={}),
        ]
        chain = _build_chain_from_problems(problems)
        # Find first HPF index and first PeakFilter index
        hpf_indices = [
            i for i, p in enumerate(chain) if isinstance(p, pb.HighpassFilter)
        ]
        peak_indices = [i for i, p in enumerate(chain) if isinstance(p, pb.PeakFilter)]
        assert len(hpf_indices) > 0
        assert len(peak_indices) > 0
        assert hpf_indices[0] < peak_indices[0]

    def test_notch_before_peak_in_chain(self):
        """Notch filters (Q>10) come before peak filters (Q<=10)."""
        import pedalboard as pb
        from phantom.processing import _build_chain_from_problems
        from phantom.problems import ProblemItem

        # hum (notch Q=30) + harshness (peak Q=1.5)
        problems = [
            ProblemItem(
                type="harshness", severity="moderate", message="Harsh", details={}
            ),
            ProblemItem(
                type="hum",
                severity="moderate",
                message="Hum",
                details={"frequencies_hz": [60.0]},
            ),
        ]
        chain = _build_chain_from_problems(problems)
        # Find notch (Q>10) and peak (Q<=10) positions
        notch_indices = [
            i for i, p in enumerate(chain) if isinstance(p, pb.PeakFilter) and p.q > 10
        ]
        peak_indices = [
            i for i, p in enumerate(chain) if isinstance(p, pb.PeakFilter) and p.q <= 10
        ]
        assert len(notch_indices) > 0
        assert len(peak_indices) > 0
        assert notch_indices[0] < peak_indices[0]

    def test_empty_for_no_fixable_problems(self):
        """No fixable problems returns empty chain."""
        from phantom.processing import _build_chain_from_problems
        from phantom.problems import ProblemItem

        problems = [
            ProblemItem(
                type="clipping", severity="dealbreaker", message="Clipped", details={}
            ),
            ProblemItem(
                type="noise_floor", severity="minor", message="Noisy", details={}
            ),
        ]
        chain = _build_chain_from_problems(problems)
        assert chain == []

    def test_multiple_recipes_flattened(self):
        """Multiple fixable problems flatten into single chain."""
        from phantom.processing import _build_chain_from_problems
        from phantom.problems import ProblemItem

        problems = [
            ProblemItem(type="mud", severity="moderate", message="Mud", details={}),
            ProblemItem(
                type="harshness", severity="moderate", message="Harsh", details={}
            ),
        ]
        chain = _build_chain_from_problems(problems)
        # mud=2 plugins + harshness=1 plugin = 3 total
        assert len(chain) == 3


# ---------------------------------------------------------------------------
# TestFixAudio -- End-to-end fix_audio function
# ---------------------------------------------------------------------------


class TestFixAudio:
    """fix_audio orchestrates detect_problems -> recipe -> process -> compare."""

    @pytest.fixture()
    def stereo_wav(self, tmp_path):
        """Create a stereo WAV file with a 440Hz sine."""
        sr = 44100
        duration = 0.5
        n = int(sr * duration)
        t = np.linspace(0, duration, n, endpoint=False, dtype=np.float32)
        samples = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        samples_2d = np.column_stack([samples, samples])
        path = str(tmp_path / "input.wav")
        sf.write(path, samples_2d, sr)
        return path

    def test_fix_audio_returns_fix_result(self, stereo_wav, tmp_path, monkeypatch):
        """fix_audio returns a FixResult with all required fields."""
        from phantom.processing import fix_audio, FixResult
        from phantom.problems import ProblemsResult

        # Mock detect_problems to return no problems (clean audio)
        monkeypatch.setattr(
            "phantom.processing.detect_problems",
            lambda audio: ProblemsResult(problems=[], clean=True),
        )

        output = str(tmp_path / "output.wav")
        result = fix_audio(stereo_wav, output_path=output)
        assert isinstance(result, FixResult)
        assert result.output_path == output
        assert isinstance(result.before, ProblemsResult)
        assert isinstance(result.after, ProblemsResult)
        assert isinstance(result.improvements, list)
        assert isinstance(result.regressions, list)

    def test_fix_audio_no_problems_writes_copy(self, stereo_wav, tmp_path, monkeypatch):
        """When no fixable problems detected, output is a copy of input."""
        from phantom.processing import fix_audio
        from phantom.problems import ProblemsResult

        monkeypatch.setattr(
            "phantom.processing.detect_problems",
            lambda audio: ProblemsResult(problems=[], clean=True),
        )

        output = str(tmp_path / "output.wav")
        result = fix_audio(stereo_wav, output_path=output)
        assert os.path.isfile(output)
        assert result.fixes_applied == []

    def test_fix_audio_with_detected_problem(self, stereo_wav, tmp_path, monkeypatch):
        """fix_audio with detected fixable problem applies recipe and reports fix."""
        from phantom.processing import fix_audio
        from phantom.problems import ProblemsResult, ProblemItem

        before_result = ProblemsResult(
            problems=[
                ProblemItem(
                    type="mud", severity="moderate", message="Mud detected", details={}
                )
            ],
            clean=False,
        )
        after_result = ProblemsResult(problems=[], clean=True)
        call_count = {"n": 0}

        def mock_detect(audio):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return before_result
            return after_result

        monkeypatch.setattr("phantom.processing.detect_problems", mock_detect)

        output = str(tmp_path / "output.wav")
        result = fix_audio(stereo_wav, output_path=output)
        assert "mud" in result.fixes_applied
        assert os.path.isfile(output)
        # detect_problems called twice: before and after
        assert call_count["n"] == 2

    def test_fix_audio_problems_filter(self, stereo_wav, tmp_path, monkeypatch):
        """problems parameter filters which problem types to fix."""
        from phantom.processing import fix_audio
        from phantom.problems import ProblemsResult, ProblemItem

        before_result = ProblemsResult(
            problems=[
                ProblemItem(type="mud", severity="moderate", message="Mud", details={}),
                ProblemItem(
                    type="harshness",
                    severity="significant",
                    message="Harsh",
                    details={},
                ),
            ],
            clean=False,
        )
        after_result = ProblemsResult(problems=[], clean=True)
        call_count = {"n": 0}

        def mock_detect(audio):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return before_result
            return after_result

        monkeypatch.setattr("phantom.processing.detect_problems", mock_detect)

        output = str(tmp_path / "output.wav")
        # Only fix harshness, not mud
        result = fix_audio(stereo_wav, problems=["harshness"], output_path=output)
        assert "harshness" in result.fixes_applied
        assert "mud" not in result.fixes_applied

    def test_fix_audio_problems_filter_no_match(
        self, stereo_wav, tmp_path, monkeypatch
    ):
        """problems filter that matches no detected problems -> no processing."""
        from phantom.processing import fix_audio
        from phantom.problems import ProblemsResult, ProblemItem

        before_result = ProblemsResult(
            problems=[
                ProblemItem(type="mud", severity="moderate", message="Mud", details={})
            ],
            clean=False,
        )
        after_result = ProblemsResult(problems=[], clean=True)
        call_count = {"n": 0}

        def mock_detect(audio):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return before_result
            return after_result

        monkeypatch.setattr("phantom.processing.detect_problems", mock_detect)

        output = str(tmp_path / "output.wav")
        result = fix_audio(stereo_wav, problems=["harshness"], output_path=output)
        assert result.fixes_applied == []
        assert os.path.isfile(output)

    def test_fix_audio_regression_detection(self, stereo_wav, tmp_path, monkeypatch):
        """Worsened problems appear in FixResult.regressions."""
        from phantom.processing import fix_audio
        from phantom.problems import ProblemsResult, ProblemItem

        before_result = ProblemsResult(
            problems=[
                ProblemItem(type="mud", severity="moderate", message="Mud", details={})
            ],
            clean=False,
        )
        after_result = ProblemsResult(
            problems=[
                ProblemItem(
                    type="mud", severity="dealbreaker", message="Mud worse", details={}
                )
            ],
            clean=False,
        )
        call_count = {"n": 0}

        def mock_detect(audio):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return before_result
            return after_result

        monkeypatch.setattr("phantom.processing.detect_problems", mock_detect)

        output = str(tmp_path / "output.wav")
        result = fix_audio(stereo_wav, output_path=output)
        assert len(result.regressions) == 1
        assert result.regressions[0].problem_type == "mud"
        assert result.regressions[0].status == "worsened"

    def test_fix_audio_unfixable_skipped(self, stereo_wav, tmp_path, monkeypatch):
        """Unfixable problems are skipped, not passed to recipe lookup."""
        from phantom.processing import fix_audio
        from phantom.problems import ProblemsResult, ProblemItem

        before_result = ProblemsResult(
            problems=[
                ProblemItem(
                    type="clipping",
                    severity="dealbreaker",
                    message="Clipped",
                    details={},
                ),
                ProblemItem(type="mud", severity="moderate", message="Mud", details={}),
            ],
            clean=False,
        )
        after_result = ProblemsResult(problems=[], clean=True)
        call_count = {"n": 0}

        def mock_detect(audio):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return before_result
            return after_result

        monkeypatch.setattr("phantom.processing.detect_problems", mock_detect)

        output = str(tmp_path / "output.wav")
        result = fix_audio(stereo_wav, output_path=output)
        # Only mud should be fixed, not clipping
        assert "mud" in result.fixes_applied
        assert "clipping" not in result.fixes_applied

    def test_fix_audio_default_output_path(self, stereo_wav, monkeypatch):
        """Default output path uses _fixed suffix."""
        from phantom.processing import fix_audio
        from phantom.problems import ProblemsResult

        monkeypatch.setattr(
            "phantom.processing.detect_problems",
            lambda audio: ProblemsResult(problems=[], clean=True),
        )

        result = fix_audio(stereo_wav)
        expected = stereo_wav.replace(".wav", "_fixed.wav")
        assert result.output_path == expected
        assert os.path.isfile(expected)

    def test_fix_audio_improvements_list(self, stereo_wav, tmp_path, monkeypatch):
        """Resolved problems appear in improvements list."""
        from phantom.processing import fix_audio
        from phantom.problems import ProblemsResult, ProblemItem

        before_result = ProblemsResult(
            problems=[
                ProblemItem(type="mud", severity="moderate", message="Mud", details={}),
            ],
            clean=False,
        )
        after_result = ProblemsResult(problems=[], clean=True)
        call_count = {"n": 0}

        def mock_detect(audio):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return before_result
            return after_result

        monkeypatch.setattr("phantom.processing.detect_problems", mock_detect)

        output = str(tmp_path / "output.wav")
        result = fix_audio(stereo_wav, output_path=output)
        assert len(result.improvements) == 1
        assert result.improvements[0].problem_type == "mud"
        assert result.improvements[0].status == "resolved"

    def test_fix_audio_dependency_guard(self, stereo_wav, monkeypatch):
        """fix_audio raises DependencyMissingError without pedalboard."""
        import builtins
        import sys

        monkeypatch.delitem(sys.modules, "pedalboard", raising=False)

        original_import = builtins.__import__

        def _mock_import(name, *args, **kwargs):
            if name == "pedalboard":
                raise ImportError("No module named 'pedalboard'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", _mock_import)

        from phantom.processing import fix_audio

        with pytest.raises(DependencyMissingError):
            fix_audio(stereo_wav)
