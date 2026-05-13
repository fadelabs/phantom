"""Tests for phantom fix CLI command."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest
import soundfile as sf

from click.testing import CliRunner
from phantom.cli import cli
from phantom.processing import FixResult, FixComparison
from phantom.problems import ProblemsResult, ProblemItem


@pytest.fixture
def runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def make_wav(tmp_path):
    """Factory: write numpy array to a temporary WAV file and return path string."""
    _counter = [0]

    def _make(samples, sr=44100):
        _counter[0] += 1
        path = tmp_path / f"fix_test_{_counter[0]}.wav"
        sf.write(str(path), samples, sr)
        return str(path)

    return _make


def _make_mock_fix_result(output_path: str = "/tmp/output_fixed.wav") -> FixResult:
    """Create a mock FixResult for testing."""
    return FixResult(
        output_path=output_path,
        fixes_applied=["mud", "harshness"],
        before=ProblemsResult(
            problems=[
                ProblemItem(
                    type="mud", severity="moderate", message="Mud detected", details={}
                ),
                ProblemItem(
                    type="harshness",
                    severity="significant",
                    message="Harsh",
                    details={},
                ),
            ],
            clean=False,
        ),
        after=ProblemsResult(problems=[], clean=True),
        improvements=[
            FixComparison(
                problem_type="mud",
                before_severity="moderate",
                after_severity=None,
                status="resolved",
            ),
            FixComparison(
                problem_type="harshness",
                before_severity="significant",
                after_severity=None,
                status="resolved",
            ),
        ],
        regressions=[],
    )


# ---------------------------------------------------------------------------
# Test 1: JSON output mode
# ---------------------------------------------------------------------------


def test_fix_json_output(runner, mono_sine_440hz, make_wav):
    """phantom fix --json with mocked fix_audio returns exit 0, JSON contains expected keys."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    mock_result = _make_mock_fix_result(path.replace(".wav", "_fixed.wav"))

    with patch("phantom.cli.fix.fix_audio", return_value=mock_result):
        result = runner.invoke(cli, ["fix", "--json", path])

    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    data = json.loads(result.output)
    assert "output_path" in data
    assert "fixes_applied" in data


# ---------------------------------------------------------------------------
# Test 2: Rich output mode
# ---------------------------------------------------------------------------


def test_fix_rich_output(runner, mono_sine_440hz, make_wav):
    """phantom fix without --json returns exit 0, output contains fix complete text."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    mock_result = _make_mock_fix_result(path.replace(".wav", "_fixed.wav"))

    with patch("phantom.cli.fix.fix_audio", return_value=mock_result):
        result = runner.invoke(cli, ["fix", path])

    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    output_lower = result.output.lower()
    assert "fix" in output_lower


# ---------------------------------------------------------------------------
# Test 3: DependencyMissingError handling
# ---------------------------------------------------------------------------


def test_fix_dependency_error(runner, mono_sine_440hz, make_wav):
    """phantom fix with DependencyMissingError returns non-zero exit."""
    from phantom.exceptions import DependencyMissingError

    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    with patch(
        "phantom.cli.fix.fix_audio",
        side_effect=DependencyMissingError(package="Pedalboard", extra="processing"),
    ):
        result = runner.invoke(cli, ["fix", path])
    assert result.exit_code != 0
    output_lower = result.output.lower()
    assert "not installed" in output_lower or "processing" in output_lower


# ---------------------------------------------------------------------------
# Test 4: PhantomError handling
# ---------------------------------------------------------------------------


def test_fix_phantom_error(runner, mono_sine_440hz, make_wav):
    """phantom fix with PhantomError returns non-zero exit."""
    from phantom.exceptions import PhantomError

    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    with patch(
        "phantom.cli.fix.fix_audio",
        side_effect=PhantomError("Audio file is corrupted"),
    ):
        result = runner.invoke(cli, ["fix", path])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Test 5: --output flag passes output_path
# ---------------------------------------------------------------------------


def test_fix_output_flag(runner, mono_sine_440hz, make_wav, tmp_path):
    """phantom fix --output custom.wav passes output_path to fix_audio."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)
    custom_output = str(tmp_path / "custom.wav")
    mock_result = _make_mock_fix_result(custom_output)

    with patch("phantom.cli.fix.fix_audio", return_value=mock_result) as mock_fn:
        result = runner.invoke(cli, ["fix", "--output", custom_output, path])

    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    mock_fn.assert_called_once()
    call_kwargs = mock_fn.call_args
    assert call_kwargs[1].get("output_path") == custom_output or (
        len(call_kwargs[0]) >= 2 and call_kwargs[0][1] == custom_output
    )


# ---------------------------------------------------------------------------
# Test 6: --interactive mode
# ---------------------------------------------------------------------------


def test_fix_interactive_mode(runner, mono_sine_440hz, make_wav):
    """phantom fix --interactive prompts user and passes selected problems."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)

    mock_problems = ProblemsResult(
        problems=[
            ProblemItem(
                type="mud", severity="moderate", message="Mud detected", details={}
            ),
            ProblemItem(
                type="harshness",
                severity="significant",
                message="Harsh",
                details={},
            ),
        ],
        clean=False,
    )
    mock_result = _make_mock_fix_result(path.replace(".wav", "_fixed.wav"))

    with (
        patch("phantom.cli.fix.detect_problems", return_value=mock_problems),
        patch("phantom.cli.fix.fix_audio", return_value=mock_result) as mock_fix,
        patch("phantom.cli.fix.Prompt.ask", return_value="1"),
    ):
        result = runner.invoke(cli, ["fix", "--interactive", path])

    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    mock_fix.assert_called_once()
    # Verify problems parameter was passed (selected subset)
    call_kwargs = mock_fix.call_args
    problems_arg = call_kwargs[1].get("problems") if call_kwargs[1] else None
    assert problems_arg is not None, "Expected problems= kwarg to be passed to fix_audio"


# ---------------------------------------------------------------------------
# Test 7: --interactive mode with all out-of-range indices falls back to all
# ---------------------------------------------------------------------------


def test_fix_interactive_out_of_range_falls_back(runner, mono_sine_440hz, make_wav):
    """When all user indices are out of range, fix falls back to fixing all."""
    samples, sr = mono_sine_440hz
    path = make_wav(samples, sr)

    mock_problems = ProblemsResult(
        problems=[
            ProblemItem(
                type="mud", severity="moderate", message="Mud detected", details={}
            ),
        ],
        clean=False,
    )
    mock_result = _make_mock_fix_result(path.replace(".wav", "_fixed.wav"))

    with (
        patch("phantom.cli.fix.detect_problems", return_value=mock_problems),
        patch("phantom.cli.fix.fix_audio", return_value=mock_result) as mock_fix,
        patch("phantom.cli.fix.Prompt.ask", return_value="10,20"),
    ):
        result = runner.invoke(cli, ["fix", "--interactive", path])

    assert result.exit_code == 0, f"Exit {result.exit_code}: {result.output}"
    assert "no valid selections" in result.output.lower()
    mock_fix.assert_called_once()
    call_kwargs = mock_fix.call_args
    problems_arg = call_kwargs[1].get("problems") if call_kwargs[1] else None
    # Should fall back to None (fix all) since no valid selection
    assert problems_arg is None, "Expected problems=None (fix all) for out-of-range selections"
