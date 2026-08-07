"""Phantom analyze command -- full audio diagnostic from the terminal."""

from __future__ import annotations

import os
import sys

import rich_click as click
from rich.panel import Panel

from phantom import load_audio, PhantomError
from phantom.facade import (
    ANALYSIS_TYPES,
    BatchDiagnosticResult,
    StemDiagnosticResult,
    run_analyses,
)
from phantom.cli._formatting import (
    get_console,
    render_problems_table,
    render_spectral_chart,
    render_analysis_table,
    output_json,
    render_error,
)
from phantom.problems import inject_sample_rate_mismatch


# ---------------------------------------------------------------------------
# Analysis dispatcher
# ---------------------------------------------------------------------------


def _run_selected_analyses(audio, enabled: list[str]) -> dict:
    """Run only the enabled analysis types and return results dict.

    Delegates to ``phantom.facade.run_analyses``, which routes each analyzer
    through the shared ``analysis_cache`` under the registry's canonical cache
    keys (P-01). The keys (e.g. ``analyze_spectrum``) match those used by the
    MCP composite tools and ``compare_*`` tools, so CLI and server share
    entries.
    """
    return run_analyses(audio, enabled)


def _enabled_analyses(
    spectrum: bool,
    loudness: bool,
    dynamics: bool,
    stereo: bool,
    phase: bool,
    problems: bool,
) -> list[str]:
    """Return the list of enabled analysis names based on flags.

    If no flags are set, all analyses are enabled (full diagnostic).
    """
    run_all = not any([spectrum, loudness, dynamics, stereo, phase, problems])
    if run_all:
        return list(ANALYSIS_TYPES)

    enabled: list[str] = []
    if spectrum:
        enabled.append("spectral")
    if loudness:
        enabled.append("loudness")
    if dynamics:
        enabled.append("dynamics")
    if stereo:
        enabled.append("stereo")
    if phase:
        enabled.append("phase")
    if problems:
        enabled.append("problems")
    return enabled


# ---------------------------------------------------------------------------
# Rich rendering helpers
# ---------------------------------------------------------------------------


def _render_file_header(audio, file_path: str, console) -> None:
    """Print a Rich Panel header with file metadata."""
    ch_label = "stereo" if audio.num_channels == 2 else "mono"
    console.print(
        Panel(
            f"[bold]{os.path.basename(file_path)}[/bold]  |  "
            f"{audio.duration:.1f}s  |  {audio.sample_rate} Hz  |  {ch_label}",
            border_style="cyan",
        )
    )


def _render_results(results: dict, console) -> None:
    """Render analysis results as Rich tables and charts."""
    for name, result in results.items():
        if name == "problems":
            render_problems_table(result, console)
        elif name == "spectral":
            render_analysis_table("Spectral Analysis", result.model_dump(), console)
            octave_bands = getattr(result, "octave_band_energy_db", None)
            if octave_bands is not None:
                render_spectral_chart(octave_bands, console)
        else:
            render_analysis_table(
                ANALYSIS_TYPES[name].title, result.model_dump(), console
            )


def _build_json_payload(audio, file_path: str, results: dict) -> dict:
    """Build a JSON-serializable dict for a single file analysis."""
    payload = StemDiagnosticResult(
        file=os.path.basename(file_path),
        duration_seconds=audio.duration,
        sample_rate=audio.sample_rate,
        channels=audio.num_channels,
        **results,
    )
    return payload.model_dump(exclude_none=True)


# ---------------------------------------------------------------------------
# Batch mode helpers
# ---------------------------------------------------------------------------


def _detect_sample_rate_mismatch(
    all_results: dict[str, dict],
    sample_rates: dict[str, int],
) -> None:
    """Inject sample_rate_mismatch ProblemItem into each stem's problems.

    Modifies *all_results* in place if a mismatch is detected.
    """
    unique_rates = set(sample_rates.values())
    if len(unique_rates) <= 1:
        return

    for stem_name, stem_data in all_results.items():
        if "error" in stem_data:
            continue

        problems_result = stem_data.get("_problems_result")
        if problems_result is None:
            continue

        rebuilt = inject_sample_rate_mismatch(problems_result, sample_rates)

        # Update results dict
        stem_data["results"]["problems"] = rebuilt
        stem_data["_problems_result"] = rebuilt


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


@click.command()
@click.argument("files", nargs=-1, required=True, type=click.Path())
@click.option("--json", "-j", "json_output", is_flag=True, help="Output raw JSON")
@click.option("--spectrum", is_flag=True, help="Spectral analysis only")
@click.option("--loudness", is_flag=True, help="Loudness analysis only")
@click.option("--dynamics", is_flag=True, help="Dynamics analysis only")
@click.option("--stereo", is_flag=True, help="Stereo field analysis only")
@click.option("--phase", is_flag=True, help="Phase coherence analysis only")
@click.option("--problems", is_flag=True, help="Problem detection only")
def analyze(
    files: tuple[str, ...],
    json_output: bool,
    spectrum: bool,
    loudness: bool,
    dynamics: bool,
    stereo: bool,
    phase: bool,
    problems: bool,
) -> None:
    """Analyze one or more audio files.

    Runs full diagnostic by default. Use flags to narrow analysis scope.
    Multiple files trigger batch mode with cross-file warnings.
    """
    console = get_console(json_mode=json_output)
    enabled = _enabled_analyses(spectrum, loudness, dynamics, stereo, phase, problems)
    is_batch = len(files) > 1

    try:
        if is_batch:
            _run_batch(files, enabled, json_output, console)
        else:
            _run_single(files[0], enabled, json_output, console)
    except PhantomError as exc:
        render_error(exc, console)
        sys.exit(1)
    except Exception as exc:
        render_error(exc, console)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Single file mode
# ---------------------------------------------------------------------------


def _run_single(
    file_path: str,
    enabled: list[str],
    json_output: bool,
    console,
) -> None:
    """Analyze a single audio file."""
    audio = load_audio(file_path)
    results = _run_selected_analyses(audio, enabled)

    if json_output:
        payload = _build_json_payload(audio, file_path, results)
        output_json(payload)
        sys.exit(0)

    _render_file_header(audio, file_path, console)
    _render_results(results, console)


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------


def _run_batch(
    files: tuple[str, ...],
    enabled: list[str],
    json_output: bool,
    console,
) -> None:
    """Analyze multiple audio files with cross-file warnings."""
    all_results: dict[str, dict] = {}
    sample_rates: dict[str, int] = {}

    # Detect basename collisions -- use full path as key when duplicates exist
    basenames = [os.path.basename(f) for f in files]
    use_full_path = len(set(basenames)) != len(basenames)

    for file_path in files:
        stem_name = file_path if use_full_path else os.path.basename(file_path)
        try:
            audio = load_audio(file_path)
            sample_rates[stem_name] = audio.sample_rate
            results = _run_selected_analyses(audio, enabled)

            all_results[stem_name] = {
                "audio": audio,
                "file_path": file_path,
                "results": results,
                "_problems_result": results.get("problems"),
            }
        except PhantomError as exc:
            all_results[stem_name] = {
                "error": str(exc),
                "error_type": type(exc).__name__,
            }
        except Exception as exc:
            all_results[stem_name] = {
                "error": str(exc),
                "error_type": type(exc).__name__,
            }

    # Post-pass: detect sample rate mismatches
    _detect_sample_rate_mismatch(all_results, sample_rates)

    # Determine if there is a mismatch for the warning display
    has_mismatch = len(set(sample_rates.values())) > 1 if sample_rates else False

    if json_output:
        _output_batch_json(all_results, files, enabled)
        sys.exit(0)

    _render_batch_rich(all_results, sample_rates, has_mismatch, console)


def _output_batch_json(
    all_results: dict[str, dict],
    files: tuple[str, ...],
    enabled: list[str],
) -> None:
    """Output batch results as JSON."""
    stems: dict = {}
    for stem_name, data in all_results.items():
        if "error" in data:
            stems[stem_name] = {
                "error": data["error"],
                "error_type": data["error_type"],
            }
            continue

        audio = data["audio"]
        results = data["results"]
        stems[stem_name] = StemDiagnosticResult(
            file=stem_name,
            duration_seconds=audio.duration,
            sample_rate=audio.sample_rate,
            channels=audio.num_channels,
            **results,
        ).model_dump(exclude_none=True)

    batch_payload = BatchDiagnosticResult(
        stems=stems,
        stem_count=len(files),
    ).model_dump()
    output_json(batch_payload)


def _render_batch_rich(
    all_results: dict[str, dict],
    sample_rates: dict[str, int],
    has_mismatch: bool,
    console,
) -> None:
    """Render batch results with Rich formatting."""
    for stem_name, data in all_results.items():
        if "error" in data:
            console.print(
                Panel(
                    f"[bold red]{data['error']}[/bold red]",
                    title=f"Error: {stem_name}",
                    border_style="red",
                )
            )
            continue

        audio = data["audio"]
        file_path = data["file_path"]
        results = data["results"]

        _render_file_header(audio, file_path, console)
        _render_results(results, console)

    # Sample rate mismatch warning at the end
    if has_mismatch:
        rate_lines = "\n".join(
            f"  {name}: {rate} Hz" for name, rate in sample_rates.items()
        )
        console.print(
            Panel(
                f"[bold red]Sample rate mismatch detected![/bold red]\n\n{rate_lines}",
                title="Warning",
                border_style="bold red",
            )
        )
