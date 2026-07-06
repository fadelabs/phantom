"""Phantom render command -- audio format conversion via ffmpeg.

Requires ffmpeg >= 4.0 (for the -max_alloc / -fs resource guards used to
bound decode work against decompression bombs; see Advisory 2).
"""

from __future__ import annotations

import os
import re
import shutil
import sys

import rich_click as click
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn

from phantom.cli._formatting import get_console, output_json, render_error

_SUPPORTED_FORMATS = ("mp3", "flac", "ogg", "wav", "aac", "m4a")

_BITRATE_RE = re.compile(r"^\d+k?$", re.IGNORECASE)
_SAMPLE_RATE_RE = re.compile(r"^\d+$")


def _validate_bitrate(ctx, param, value):
    """Validate bitrate format (e.g., 320k, 192k, 128000)."""
    if value is None:
        return value
    if not _BITRATE_RE.match(value):
        raise click.BadParameter(
            f"Invalid bitrate format: {value}. Use e.g., 320k, 192k, 128000"
        )
    return value


def _validate_sample_rate(ctx, param, value):
    """Validate sample rate format (must be a positive integer)."""
    if value is None:
        return value
    if not _SAMPLE_RATE_RE.match(value):
        raise click.BadParameter(
            f"Invalid sample rate: {value}. Use e.g., 44100, 48000, 96000"
        )
    return value


@click.command()
@click.argument("file", type=click.Path())
@click.option(
    "--format",
    "-f",
    "output_format",
    required=True,
    type=click.Choice(_SUPPORTED_FORMATS, case_sensitive=False),
    help="Output audio format",
)
@click.option(
    "--bitrate",
    "-b",
    default=None,
    callback=_validate_bitrate,
    help="Bitrate for lossy formats (e.g., 320k, 192k)",
)
@click.option(
    "--sample-rate",
    "-s",
    "sample_rate",
    default=None,
    callback=_validate_sample_rate,
    help="Output sample rate (e.g., 44100, 48000)",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    default=None,
    help="Output file path (default: input name with new extension)",
)
@click.option(
    "--json",
    "-j",
    "json_output",
    is_flag=True,
    help="Output raw JSON",
)
def render(
    file: str,
    output_format: str,
    bitrate: str | None,
    sample_rate: str | None,
    output_path: str | None,
    json_output: bool,
) -> None:
    """Convert audio files to different formats using ffmpeg.

    Requires ffmpeg installed on your system.
    """
    console = get_console(json_mode=json_output)

    # Check ffmpeg availability (D-10)
    if not shutil.which("ffmpeg"):
        console.print(
            Panel(
                "[bold]ffmpeg[/bold] is not installed.\n\n"
                "Install ffmpeg:\n"
                "  macOS:   [green]brew install ffmpeg[/green]\n"
                "  Ubuntu:  [green]sudo apt install ffmpeg[/green]\n"
                "  Windows: [green]choco install ffmpeg[/green]\n\n"
                "Or download from: https://ffmpeg.org/download.html",
                title="Missing Dependency",
                border_style="yellow",
            )
        )
        sys.exit(1)

    # Validate input path against PHANTOM_AUDIO_DIR restriction
    from phantom._utils import validate_input_path, validate_output_path
    from phantom.exceptions import PathSecurityError

    try:
        file = validate_input_path(file)
    except PathSecurityError as e:
        render_error(e, console)
        sys.exit(1)

    # Validate input file exists
    if not os.path.isfile(file):
        console.print(
            Panel(f"File not found: {file}", title="Error", border_style="red")
        )
        sys.exit(1)

    # Decode-bomb guard (Advisory 2). render handles formats libsndfile cannot
    # probe (mp3/aac), so we use a format-agnostic input file-size cap here and
    # hand ffmpeg explicit duration/size/allocation limits below.
    from phantom._utils import (
        DEFAULT_MAX_DURATION,
        DEFAULT_MAX_FILE_SIZE,
        _get_env_float,
        _get_env_int,
    )
    from phantom.exceptions import AnalysisError

    try:
        max_file_size = _get_env_int("PHANTOM_MAX_FILE_SIZE", DEFAULT_MAX_FILE_SIZE)
        max_duration = _get_env_float("PHANTOM_MAX_DURATION", DEFAULT_MAX_DURATION)
    except AnalysisError as e:
        render_error(e, console)
        sys.exit(1)

    input_size = os.path.getsize(file)
    if input_size > max_file_size:
        console.print(
            Panel(
                f"Input file is {input_size / 1_000_000:.1f} MB, which exceeds the "
                f"{max_file_size / 1_000_000:.0f} MB limit. "
                f"Set PHANTOM_MAX_FILE_SIZE to increase the limit.",
                title="File Too Large",
                border_style="red",
            )
        )
        sys.exit(1)

    # Determine output path
    if output_path is None:
        output_path = os.path.splitext(file)[0] + "." + output_format

    # Validate output path against PHANTOM_OUTPUT_DIR restriction
    try:
        output_path = validate_output_path(output_path)
    except PathSecurityError as e:
        render_error(e, console)
        sys.exit(1)

    # Self-overwrite guard (P-22). ffmpeg runs with `-y`, so if the output path
    # resolves to the same file as the source (e.g. rendering x.wav to `wav`
    # with no --output), the source would be clobbered in place. Refuse before
    # any ffmpeg run. Compare realpaths so symlinks/relative paths can't slip by;
    # also test os.path.samefile so same-inode collisions realpath does NOT
    # normalize are caught -- hardlinks, and case-variant names on
    # case-insensitive filesystems (macOS APFS), e.g. SONG.WAV -> SONG.wav.
    same_target = os.path.realpath(output_path) == os.path.realpath(file) or (
        os.path.exists(output_path) and os.path.samefile(output_path, file)
    )
    if same_target:
        console.print(
            Panel(
                "Output would overwrite the source file. Pass [bold]--output[/bold] "
                "with a different path (or choose a different [bold]--format[/bold]) "
                "so your original is preserved.",
                title="Would Overwrite Source",
                border_style="red",
            )
        )
        sys.exit(1)

    # Build ffmpeg command as list (NEVER shell=True -- T-12-11).
    # Resource guards (Advisory 2): -max_alloc caps a single allocation;
    # -t (input option) bounds how much audio is decoded; -fs caps output size.
    cmd = [
        "ffmpeg",
        "-y",
        "-max_alloc",
        str(max_file_size),
        "-t",
        f"{max_duration:.3f}",
        "-i",
        file,
    ]
    if bitrate:
        cmd.extend(["-b:a", bitrate])
    if sample_rate:
        cmd.extend(["-ar", sample_rate])
    cmd.extend(["-fs", str(max_file_size)])
    cmd.append(output_path)

    # Import ffmpeg-progress-yield with a clear error if missing
    try:
        from ffmpeg_progress_yield import FfmpegProgress
    except ImportError:
        console.print(
            Panel(
                "[bold]ffmpeg-progress-yield[/bold] is not available.\n\n"
                "Install with: [green]uv pip install ffmpeg-progress-yield[/green]",
                title="Missing Dependency",
                border_style="yellow",
            )
        )
        sys.exit(1)

    # Run with progress bar
    try:
        with Progress(
            TextColumn("[bold blue]Rendering"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("render", total=100)
            ff = FfmpegProgress(cmd)
            for pct in ff.run_command_with_progress():
                progress.update(task, completed=pct)
    except Exception as e:
        render_error(e, console)
        sys.exit(1)

    # Output result
    if json_output:
        output_json(
            {
                "input": file,
                "output": output_path,
                "format": output_format,
                "bitrate": bitrate,
                "sample_rate": sample_rate,
            }
        )
    else:
        console.print(
            Panel(
                f"[green]Rendered:[/green] {output_path}",
                border_style="green",
            )
        )
