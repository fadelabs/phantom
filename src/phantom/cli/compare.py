"""Phantom compare command -- compare audio against reference targets."""

from __future__ import annotations

import sys
from typing import Optional

import rich_click as click
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from phantom import (
    load_audio,
    compare_to_profile,
    compare_to_reference,
    load_profile,
    list_profiles,
    PhantomError,
)
from phantom.cli._formatting import (
    get_console,
    RATING_STYLES,
    output_json,
    render_error,
    _format_band_label,
)


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _format_metric_name(key: str) -> str:
    """Convert a snake_case metric key to a display name.

    Examples:
        "integrated_lufs" -> "Integrated LUFS"
        "true_peak_dbtp"  -> "True Peak dBTP"
        "crest_factor_db" -> "Crest Factor dB"
        "stereo_width"    -> "Stereo Width"
    """
    replacements = {
        "lufs": "LUFS",
        "dbtp": "dBTP",
        "dbfs": "dBFS",
        "db": "dB",
        "lu": "LU",
        "rms": "RMS",
        "hz": "Hz",
    }
    parts = key.split("_")
    result = []
    for part in parts:
        lower = part.lower()
        if lower in replacements:
            result.append(replacements[lower])
        else:
            result.append(part.capitalize())
    return " ".join(result)


def _fmt(value: Optional[float]) -> str:
    """Format a float for table display, or dash if None."""
    if value is None:
        return "-"
    return f"{value:.2f}"


def _fmt_range(target_range: Optional[list[float]]) -> str:
    """Format a target range for display."""
    if target_range is None or len(target_range) < 2:
        return "-"
    return f"{target_range[0]:.1f} to {target_range[1]:.1f}"


def _add_deviation_row(
    table: Table,
    name: str,
    dev: object,
) -> None:
    """Add a row for a DeviationResult or RangeDeviationResult."""
    rating = getattr(dev, "rating", "unmeasurable") or "unmeasurable"
    style = RATING_STYLES.get(rating, "")
    value = _fmt(getattr(dev, "value", None))

    # RangeDeviationResult has target_range; DeviationResult has target
    target_range = getattr(dev, "target_range", None)
    target = getattr(dev, "target", None)
    if target_range is not None:
        target_str = _fmt_range(target_range)
    elif target is not None:
        target_str = _fmt(target)
    else:
        target_str = "-"

    deviation = _fmt(getattr(dev, "deviation", None))
    table.add_row(name, value, target_str, deviation, rating, style=style)


def _render_profile_comparison(
    result: object, profile_name: str, console: object
) -> None:
    """Render a profile comparison result as Rich tables."""
    console.print(
        Panel(
            f"[bold]Profile:[/bold] {profile_name}",
            title="Comparison Result",
            border_style="cyan",
        )
    )

    # -- Loudness section --
    loudness = getattr(result, "loudness", None)
    if loudness is not None:
        table = Table(title="Loudness")
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_column("Target")
        table.add_column("Deviation")
        table.add_column("Rating")

        for field_name in ("integrated_lufs", "true_peak_dbtp"):
            dev = getattr(loudness, field_name, None)
            if dev is not None:
                _add_deviation_row(table, _format_metric_name(field_name), dev)

        console.print(table)

    # -- Frequency section --
    frequency = getattr(result, "frequency", None)
    if frequency:
        table = Table(title="Frequency Balance")
        table.add_column("Band", style="bold")
        table.add_column("Value")
        table.add_column("Target")
        table.add_column("Deviation")
        table.add_column("Rating")

        for band_key, dev in frequency.items():
            _add_deviation_row(table, _format_band_label(band_key), dev)

        console.print(table)

    # -- Dynamics section --
    dynamics = getattr(result, "dynamics", None)
    if dynamics is not None:
        table = Table(title="Dynamics")
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_column("Target")
        table.add_column("Deviation")
        table.add_column("Rating")

        for field_name in ("crest_factor_db",):
            dev = getattr(dynamics, field_name, None)
            if dev is not None:
                _add_deviation_row(table, _format_metric_name(field_name), dev)

        console.print(table)

    # -- Stereo section --
    stereo = getattr(result, "stereo", None)
    if stereo is not None:
        table = Table(title="Stereo")
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_column("Target")
        table.add_column("Deviation")
        table.add_column("Rating")

        width = getattr(stereo, "width", None)
        if width is not None:
            _add_deviation_row(table, "Stereo Width", width)

        mono_below = getattr(stereo, "mono_below", None)
        if mono_below is not None:
            rating = getattr(mono_below, "rating", "unmeasurable")
            style = RATING_STYLES.get(rating, "")
            table.add_row(
                "Mono Below",
                f"{getattr(mono_below, 'mono_below_hz', '-')} Hz",
                "-",
                f"corr={_fmt(getattr(mono_below, 'bass_correlation', None))}",
                rating,
                style=style,
            )

        console.print(table)


def _add_ref_deviation_row(
    table: Table,
    name: str,
    dev: object,
) -> None:
    """Add a row for a reference comparison DeviationResult."""
    rating = getattr(dev, "rating", "unmeasurable") or "unmeasurable"
    style = RATING_STYLES.get(rating, "")
    value = _fmt(getattr(dev, "value", None))
    reference = _fmt(getattr(dev, "reference", None))
    deviation = _fmt(getattr(dev, "deviation", None))
    table.add_row(name, value, reference, deviation, rating, style=style)


def _render_reference_comparison(result: object, console: object) -> None:
    """Render a reference comparison result as Rich tables."""
    console.print(
        Panel(
            "[bold]WAV-to-WAV Reference Comparison[/bold]",
            title="Comparison Result",
            border_style="cyan",
        )
    )

    # -- Loudness section --
    loudness = getattr(result, "loudness", None)
    if loudness is not None:
        table = Table(title="Loudness")
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_column("Reference")
        table.add_column("Deviation")
        table.add_column("Rating")

        for field_name in ("integrated_lufs", "true_peak_dbtp", "loudness_range_lu"):
            dev = getattr(loudness, field_name, None)
            if dev is not None:
                _add_ref_deviation_row(table, _format_metric_name(field_name), dev)

        console.print(table)

    # -- Frequency section --
    frequency = getattr(result, "frequency", None)
    if frequency:
        table = Table(title="Frequency Balance")
        table.add_column("Band", style="bold")
        table.add_column("Value")
        table.add_column("Reference")
        table.add_column("Deviation")
        table.add_column("Rating")

        for band_key, dev in frequency.items():
            _add_ref_deviation_row(table, _format_band_label(band_key), dev)

        console.print(table)

    # -- Dynamics section --
    dynamics = getattr(result, "dynamics", None)
    if dynamics is not None:
        table = Table(title="Dynamics")
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_column("Reference")
        table.add_column("Deviation")
        table.add_column("Rating")

        for field_name in ("rms_dbfs", "crest_factor_db", "dynamic_range_db"):
            dev = getattr(dynamics, field_name, None)
            if dev is not None:
                _add_ref_deviation_row(table, _format_metric_name(field_name), dev)

        console.print(table)

    # -- Stereo section --
    stereo = getattr(result, "stereo", None)
    if stereo is not None:
        table = Table(title="Stereo")
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        table.add_column("Reference")
        table.add_column("Deviation")
        table.add_column("Rating")

        for field_name in ("correlation", "stereo_width"):
            dev = getattr(stereo, field_name, None)
            if dev is not None:
                _add_ref_deviation_row(table, _format_metric_name(field_name), dev)

        console.print(table)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@click.command()
@click.argument("file", type=click.Path())
@click.option(
    "--profile",
    "-p",
    default=None,
    help="Compare against genre profile (e.g., rock, pop, hip-hop)",
)
@click.option(
    "--reference",
    "-r",
    type=click.Path(),
    default=None,
    help="Compare against reference WAV file",
)
@click.option(
    "--json",
    "-j",
    "json_output",
    is_flag=True,
    help="Output raw JSON",
)
def compare(
    file: str, profile: str | None, reference: str | None, json_output: bool
) -> None:
    """Compare audio against a reference profile or WAV file.

    Use --profile for genre comparison or --reference for WAV-to-WAV comparison.
    If neither specified, shows an interactive profile picker.
    """
    # Mutual exclusivity check
    if profile and reference:
        raise click.UsageError(
            "--profile and --reference are mutually exclusive. Use one or the other."
        )

    console = get_console(json_mode=json_output)

    try:
        # Interactive picker when neither flag given
        if not profile and not reference:
            if sys.stdin.isatty():
                profiles = list_profiles()
                if not profiles:
                    raise click.UsageError("No profiles available.")

                table = Table(title="Available Profiles")
                table.add_column("#", style="dim")
                table.add_column("Profile", style="bold")
                for i, name in enumerate(profiles, 1):
                    table.add_row(str(i), name)
                console.print(table)

                profile = Prompt.ask(
                    "Select profile",
                    choices=profiles,
                    console=console,
                )
            else:
                profiles = list_profiles()
                print(
                    f"Available profiles: {', '.join(profiles)}",
                    file=sys.stderr,
                )
                raise click.UsageError(
                    "No profile specified. Use --profile <name> or --reference <file>"
                )

        # Profile comparison mode
        if profile:
            audio = load_audio(file)
            ref = load_profile(profile)
            result = compare_to_profile(audio, ref)

            if json_output:
                data = result.model_dump()
                data["profile_name"] = profile
                output_json(data)
                return

            _render_profile_comparison(result, profile, console)
            return

        # Reference comparison mode
        if reference:
            audio = load_audio(file)
            ref_audio = load_audio(reference)
            result = compare_to_reference(audio, ref_audio)

            if json_output:
                output_json(result.model_dump())
                return

            _render_reference_comparison(result, console)
            return

    except click.UsageError:
        raise
    except PhantomError as exc:
        render_error(exc, console)
        sys.exit(1)
    except Exception as exc:
        render_error(exc, console)
        sys.exit(1)
