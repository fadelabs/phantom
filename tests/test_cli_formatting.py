"""Tests for Phantom CLI formatting utilities and CLI entry point.

Covers severity/rating style maps, console factory, band label formatting,
JSON output, error panel rendering, problems table, spectral chart,
and CLI --version / --help smoke tests.
"""

from __future__ import annotations

import io
import json

from click.testing import CliRunner
from rich.console import Console

from phantom.cli import cli
from phantom.cli._formatting import (
    RATING_STYLES,
    SEVERITY_LABELS,
    SEVERITY_STYLES,
    _format_band_label,
    get_console,
    output_json,
    render_error,
    render_problems_table,
    render_spectral_chart,
)
from phantom.exceptions import DependencyMissingError, PhantomError
from phantom.problems import ProblemItem, ProblemSummary, ProblemsResult


# ---------------------------------------------------------------------------
# Style maps
# ---------------------------------------------------------------------------


def test_severity_styles_has_all_tiers():
    """SEVERITY_STYLES has exactly 4 keys matching problem severity tiers."""
    expected = {"dealbreaker", "significant", "moderate", "minor"}
    assert set(SEVERITY_STYLES.keys()) == expected
    assert len(SEVERITY_STYLES) == 4

    assert set(SEVERITY_LABELS.keys()) == expected
    assert len(SEVERITY_LABELS) == 4


def test_severity_styles_values():
    """Severity styles match the D-06 spec."""
    assert SEVERITY_STYLES["dealbreaker"] == "bold red"
    assert SEVERITY_STYLES["significant"] == "yellow"
    assert SEVERITY_STYLES["moderate"] == "blue"
    assert SEVERITY_STYLES["minor"] == "dim"


def test_rating_styles_has_all_ratings():
    """RATING_STYLES has exactly 5 keys for comparison deviation ratings."""
    expected = {"on_target", "slight", "moderate", "significant", "unmeasurable"}
    assert set(RATING_STYLES.keys()) == expected
    assert len(RATING_STYLES) == 5


# ---------------------------------------------------------------------------
# Console factory
# ---------------------------------------------------------------------------


def test_get_console_normal_mode():
    """Normal mode console writes to stdout."""
    console = get_console(json_mode=False)
    assert console.file is not None
    # Default Console writes to stdout
    import sys

    assert console.file is sys.stdout


def test_get_console_json_mode():
    """JSON mode console writes to stderr so piped JSON stays clean."""
    console = get_console(json_mode=True)
    import sys

    assert console.file is sys.stderr


# ---------------------------------------------------------------------------
# Band label formatting
# ---------------------------------------------------------------------------


def test_format_band_label():
    """_format_band_label converts octave band keys to display labels."""
    assert _format_band_label("31_hz") == "31 Hz"
    assert _format_band_label("62_hz") == "62 Hz"
    assert _format_band_label("125_hz") == "125 Hz"
    assert _format_band_label("250_hz") == "250 Hz"
    assert _format_band_label("500_hz") == "500 Hz"
    assert _format_band_label("1000_hz") == "1k Hz"
    assert _format_band_label("2000_hz") == "2k Hz"
    assert _format_band_label("4000_hz") == "4k Hz"
    assert _format_band_label("8000_hz") == "8k Hz"
    assert _format_band_label("16000_hz") == "16k Hz"


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def test_output_json_writes_to_stdout(capsys):
    """output_json prints valid JSON to stdout."""
    output_json({"key": "value", "number": 42})
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["key"] == "value"
    assert data["number"] == 42


# ---------------------------------------------------------------------------
# Error rendering
# ---------------------------------------------------------------------------


def test_render_error_phantom_error():
    """PhantomError renders as a red Error panel."""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    render_error(PhantomError("test error msg"), console)
    output = buf.getvalue()
    assert "test error msg" in output
    assert "Error" in output


def test_render_error_dependency_missing():
    """DependencyMissingError renders as a yellow Missing Dependency panel."""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    render_error(DependencyMissingError(package="Demucs", extra="separation"), console)
    output = buf.getvalue()
    assert "Demucs" in output
    assert "separation" in output
    assert "Missing Dependency" in output


def test_render_error_generic_exception():
    """Generic exceptions render as Unexpected Error panel."""
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    render_error(ValueError("something went wrong"), console)
    output = buf.getvalue()
    assert "something went wrong" in output
    assert "Unexpected Error" in output


# ---------------------------------------------------------------------------
# Problems table
# ---------------------------------------------------------------------------


def test_render_problems_table_no_problems():
    """Empty problems list shows the 'No problems detected' message."""
    result = ProblemsResult(problems=[], clean=True, summary=ProblemSummary())
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    render_problems_table(result, console)
    output = buf.getvalue()
    assert "No problems detected" in output


def test_render_problems_table_with_problems():
    """Problems table renders severity labels and problem details."""
    problems = [
        ProblemItem(
            type="clipping",
            severity="dealbreaker",
            message="Clipping detected in 5 locations",
            details={"clip_count": 5},
        ),
        ProblemItem(
            type="dc_offset",
            severity="moderate",
            message="DC offset of 0.03",
            details={"offset": 0.03},
        ),
    ]
    summary = ProblemSummary(dealbreaker=1, moderate=1, total=2)
    result = ProblemsResult(problems=problems, clean=False, summary=summary)

    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    render_problems_table(result, console)
    output = buf.getvalue()
    # Should contain severity label and problem info
    assert "DEAL" in output
    assert "clipping" in output.lower() or "Clipping" in output


# ---------------------------------------------------------------------------
# Spectral chart
# ---------------------------------------------------------------------------


def test_render_spectral_chart():
    """Spectral chart renders in a Frequency Balance panel."""
    bands = {
        "31_hz": -20.0,
        "125_hz": -15.0,
        "1000_hz": -10.0,
        "8000_hz": -25.0,
    }
    buf = io.StringIO()
    console = Console(file=buf, force_terminal=True)
    render_spectral_chart(bands, console)
    output = buf.getvalue()
    assert "Frequency Balance" in output


# ---------------------------------------------------------------------------
# CLI entry point smoke tests
# ---------------------------------------------------------------------------


def test_cli_version():
    """phantom --version prints the package version."""
    import phantom

    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert phantom.__version__ in result.output


def test_cli_help():
    """phantom --help shows the tool description."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Phantom" in result.output
    assert "audio" in result.output.lower()


def test_cli_serve_in_help():
    """phantom --help lists the serve command."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "serve" in result.output


# ---------------------------------------------------------------------------
# Backward compatibility entry points
# ---------------------------------------------------------------------------


def test_phantom_mcp_entry_point():
    """phantom-mcp entry point: phantom.server:main is importable and callable."""
    from phantom.server import main

    assert callable(main), (
        "phantom.server.main must be callable for phantom-mcp entry point"
    )


def test_python_m_phantom_routes_to_cli():
    """python -m phantom routes to the CLI, not the MCP server."""
    from phantom.cli import cli as cli_obj

    assert cli_obj is not None, "phantom.cli.cli must be importable"
    # Verify __main__ imports cli, not main from server
    import phantom.__main__ as main_module
    import inspect

    source = inspect.getsource(main_module)
    assert "from phantom.cli import cli" in source, (
        "phantom.__main__ must import cli from phantom.cli (routes to CLI, not MCP server)"
    )
    assert "from phantom.server import main" not in source, (
        "phantom.__main__ must NOT import main from phantom.server"
    )
