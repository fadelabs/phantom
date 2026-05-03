"""Phantom separate command -- stem separation via Demucs."""

from __future__ import annotations

import sys

import rich_click as click
from rich.panel import Panel
from rich.table import Table

from phantom import (
    separate_stems,
    PhantomError,
    DependencyMissingError,
)
from phantom.cli._formatting import (
    get_console,
    output_json,
    render_error,
)


@click.command()
@click.argument("file", type=click.Path())
@click.option(
    "--output-dir",
    "-o",
    default=None,
    help="Output directory for stems (default: ./stems)",
)
@click.option(
    "--json",
    "-j",
    "json_output",
    is_flag=True,
    help="Output raw JSON",
)
def separate(file: str, output_dir: str | None, json_output: bool) -> None:
    """Separate audio into stems (vocals, drums, bass, other) using Demucs.

    Requires the separation extra: uv tool install "phantom-audio[separation]"
    """
    console = get_console(json_mode=json_output)

    if output_dir is None:
        output_dir = "./stems"

    try:
        with console.status(
            "[bold blue]Separating stems with Demucs...",
            spinner="dots",
        ):
            result = separate_stems(file, output_dir)

        if json_output:
            output_json(result.model_dump())
            return

        # Rich output
        console.print(
            Panel(
                "[bold green]Separation complete[/bold green]",
                title="Phantom Separate",
                border_style="green",
            )
        )

        table = Table(title="Separated Stems")
        table.add_column("Stem", style="bold")
        table.add_column("Output Path")

        for stem_name, stem_path in sorted(result.stems.items()):
            table.add_row(stem_name, stem_path)

        console.print(table)

    except DependencyMissingError as exc:
        render_error(exc, console)
        sys.exit(1)
    except PhantomError as exc:
        render_error(exc, console)
        sys.exit(1)
