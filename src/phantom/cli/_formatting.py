"""Shared Rich formatting utilities for Phantom CLI.

Provides severity-colored tables, spectral ASCII charts, JSON output,
and error panel rendering used across all CLI subcommands.
"""

from __future__ import annotations

import json
import sys

import plotext as plt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from phantom.exceptions import RECOMMENDED_PYTHON, DependencyMissingError, PhantomError

# ---------------------------------------------------------------------------
# Severity styling (D-06)
# ---------------------------------------------------------------------------

SEVERITY_STYLES: dict[str, str] = {
    "dealbreaker": "bold red",
    "significant": "yellow",
    "moderate": "blue",
    "minor": "dim",
}

SEVERITY_LABELS: dict[str, str] = {
    "dealbreaker": "DEAL",
    "significant": "SIG",
    "moderate": "MOD",
    "minor": "MIN",
}

# ---------------------------------------------------------------------------
# Rating styling (for comparison deviations)
# ---------------------------------------------------------------------------

RATING_STYLES: dict[str, str] = {
    "on_target": "green",
    "slight": "dim",
    "moderate": "yellow",
    "significant": "bold red",
    "unmeasurable": "dim italic",
}


# ---------------------------------------------------------------------------
# Console factory
# ---------------------------------------------------------------------------


def get_console(json_mode: bool = False) -> Console:
    """Return a Rich Console.

    When *json_mode* is True the console writes to stderr so that
    JSON output on stdout stays clean for piping (Pitfall 1).
    """
    if json_mode:
        return Console(file=sys.stderr)
    return Console()


# ---------------------------------------------------------------------------
# Problems table
# ---------------------------------------------------------------------------


def render_problems_table(problems_result: object, console: Console) -> None:
    """Render a severity-colored problems table.

    *problems_result* should be a ``ProblemsResult`` instance with
    ``.problems`` (list of ``ProblemItem``) and ``.summary`` attributes.
    """
    problems = getattr(problems_result, "problems", [])
    summary = getattr(problems_result, "summary", None)

    if not problems:
        console.print("[bold green]No problems detected[/bold green]")
        return

    table = Table(title="Problems Detected", show_lines=True)
    table.add_column("Severity", width=6)
    table.add_column("Type", width=24)
    table.add_column("Message")

    for problem in problems:
        severity = getattr(problem, "severity", "")
        style = SEVERITY_STYLES.get(severity, "")
        label = SEVERITY_LABELS.get(severity, severity.upper())
        table.add_row(
            label,
            getattr(problem, "type", ""),
            getattr(problem, "message", ""),
            style=style,
        )

    console.print(table)

    # Summary line
    if summary is not None:
        parts: list[str] = []
        for sev in ("dealbreaker", "significant", "moderate", "minor"):
            count = getattr(summary, sev, 0)
            if count:
                style = SEVERITY_STYLES.get(sev, "")
                parts.append(f"[{style}]{count} {sev}[/{style}]")
        if parts:
            console.print("Summary: " + ", ".join(parts))


# ---------------------------------------------------------------------------
# Spectral chart (D-07)
# ---------------------------------------------------------------------------


def _format_band_label(key: str) -> str:
    """Convert octave band dict key to a display label.

    Examples::

        "31_hz"    -> "31 Hz"
        "125_hz"   -> "125 Hz"
        "1000_hz"  -> "1k Hz"
        "16000_hz" -> "16k Hz"
    """
    freq_str = key.replace("_hz", "").replace("_", "")
    try:
        freq = int(freq_str)
    except ValueError:
        return key

    if freq >= 1000:
        return f"{freq // 1000}k Hz"
    return f"{freq} Hz"


def render_spectral_chart(
    octave_band_energy_db: dict[str, float], console: Console
) -> None:
    """Render an ASCII spectral bar chart inside a Rich Panel."""
    bands = list(octave_band_energy_db.keys())
    energies = list(octave_band_energy_db.values())
    labels = [_format_band_label(b) for b in bands]

    plt.clf()
    plt.bar(labels, energies, orientation="h", width=3 / 5)
    plt.title("Octave Band Energy (dB)")
    plt.plotsize(60, len(bands) * 2 + 4)

    chart_str = plt.build()

    console.print(Panel(chart_str, title="Frequency Balance", border_style="cyan"))


# ---------------------------------------------------------------------------
# Generic analysis table
# ---------------------------------------------------------------------------


def render_analysis_table(
    title: str, data: dict[str, object], console: Console
) -> None:
    """Render a key-value table for analysis results."""
    table = Table(title=title)
    table.add_column("Metric", style="bold")
    table.add_column("Value")

    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            for sub_key, sub_val in value.items():
                display_val = _format_value(sub_val)
                table.add_row(f"  {sub_key}", display_val)
        else:
            table.add_row(key, _format_value(value))

    console.print(table)


def _format_value(value: object) -> str:
    """Format a value for table display."""
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, list):
        if value and isinstance(value[0], float):
            return ", ".join(f"{v:.2f}" for v in value)
        return str(value)
    return str(value)


# ---------------------------------------------------------------------------
# JSON output (D-08)
# ---------------------------------------------------------------------------


def output_json(data: object) -> None:
    """Print JSON to stdout for piping.

    Uses ``default=str`` to handle non-serializable types gracefully.
    """
    print(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Error rendering (Pattern 7)
# ---------------------------------------------------------------------------


def render_error(exc: Exception, console: Console) -> None:
    """Render an exception as a styled Rich Panel.

    - ``DependencyMissingError``: yellow panel with install instructions
    - ``PhantomError``: red panel with error message
    - Other: red panel titled "Unexpected Error"
    """
    if isinstance(exc, DependencyMissingError):
        console.print(
            Panel(
                f"[bold]{exc.package}[/bold] is not installed.\n\n"
                f'Install with: [green]uv tool install "phantom-audio\\[{exc.extra}\\]" --python {RECOMMENDED_PYTHON}[/green]',
                title="Missing Dependency",
                border_style="yellow",
            )
        )
    elif isinstance(exc, PhantomError):
        console.print(
            Panel(
                str(exc),
                title="Error",
                border_style="red",
            )
        )
    else:
        console.print(
            Panel(
                str(exc),
                title="Unexpected Error",
                border_style="red",
            )
        )
