"""Phantom fix command -- corrective audio processing via Pedalboard."""

from __future__ import annotations

import sys

import rich_click as click
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from phantom.processing import fix_audio, UNFIXABLE_TYPES, RECIPES
from phantom.problems import detect_problems
from phantom.exceptions import DependencyMissingError, PhantomError
from phantom.audio import load_audio
from phantom.cli._formatting import (
    get_console,
    output_json,
    render_error,
    SEVERITY_STYLES,
)


@click.command()
@click.argument("file", type=click.Path())
@click.option(
    "--output",
    "-o",
    "output_path",
    default=None,
    help="Output file path (default: input_fixed.wav)",
)
@click.option(
    "--interactive",
    "-i",
    is_flag=True,
    help="Select which problems to fix interactively",
)
@click.option(
    "--json",
    "-j",
    "json_output",
    is_flag=True,
    help="Output raw JSON",
)
def fix(
    file: str,
    output_path: str | None,
    interactive: bool,
    json_output: bool,
) -> None:
    """Fix detected audio problems using corrective processing.

    Analyzes the input file for problems, applies corrective EQ and
    filtering recipes, then compares before/after results.

    Requires the processing extra: uv tool install "phantom-audio[processing]"
    """
    console = get_console(json_mode=json_output)

    try:
        problems_filter: list[str] | None = None

        if interactive:
            # Interactive mode: detect problems first, let user select
            with console.status(
                "[bold blue]Analyzing audio problems...",
                spinner="dots",
            ):
                audio = load_audio(file)
                problems_result = detect_problems(audio)

            if not problems_result.problems:
                console.print("[bold green]No problems detected -- nothing to fix.")
                return

            # Separate fixable from unfixable problems
            fixable_problems = [
                p
                for p in problems_result.problems
                if p.type not in UNFIXABLE_TYPES and p.type in RECIPES
            ]
            unfixable_problems = [
                p
                for p in problems_result.problems
                if p.type in UNFIXABLE_TYPES or p.type not in RECIPES
            ]

            if unfixable_problems:
                console.print(
                    f"[dim]{len(unfixable_problems)} problem(s) cannot be "
                    f"auto-fixed ({', '.join(p.type for p in unfixable_problems)})"
                    f"[/dim]"
                )

            if not fixable_problems:
                console.print(
                    "[bold yellow]No auto-fixable problems detected."
                )
                return

            # Display numbered list of fixable problems
            console.print(
                Panel(
                    "[bold]Fixable Problems[/bold]",
                    border_style="blue",
                )
            )
            for i, problem in enumerate(fixable_problems, 1):
                style = SEVERITY_STYLES.get(problem.severity, "")
                console.print(
                    f"  [{style}]{i}. [{problem.severity.upper()}] "
                    f"{problem.type}: {problem.message}[/{style}]"
                )

            # Ask user to select problems
            selection = Prompt.ask(
                "\nEnter problem numbers to fix (comma-separated, or 'all')",
                default="all",
            )

            if selection.strip().lower() != "all":
                try:
                    indices = [int(s.strip()) - 1 for s in selection.split(",")]
                    problems_filter = [
                        fixable_problems[i].type
                        for i in indices
                        if 0 <= i < len(fixable_problems)
                    ]
                    if not problems_filter:
                        console.print(
                            "[yellow]No valid selections -- fixing all problems."
                        )
                        problems_filter = None
                except (ValueError, IndexError):
                    console.print("[yellow]Invalid selection -- fixing all problems.")
                    problems_filter = None
            else:
                problems_filter = None

        # Run fix_audio
        with console.status(
            "[bold blue]Analyzing and fixing audio problems...",
            spinner="dots",
        ):
            result = fix_audio(
                file,
                problems=problems_filter,
                output_path=output_path,
            )

        if json_output:
            output_json(result.model_dump())
            return

        # Rich output
        if result.fixes_applied:
            console.print(
                Panel(
                    "[bold green]Fix complete[/bold green]",
                    title="Phantom Fix",
                    border_style="green",
                )
            )

            # Fixes applied table
            fixes_table = Table(title="Fixes Applied")
            fixes_table.add_column("Problem Type", style="bold")
            for fix_name in result.fixes_applied:
                fixes_table.add_row(fix_name)
            console.print(fixes_table)
        else:
            console.print(
                Panel(
                    "[bold green]No fixable problems detected[/bold green]",
                    title="Phantom Fix",
                    border_style="green",
                )
            )

        # Before/after comparison table
        if result.improvements or result.regressions:
            comparison_table = Table(title="Before/After Comparison")
            comparison_table.add_column("Problem", style="bold")
            comparison_table.add_column("Before")
            comparison_table.add_column("After")
            comparison_table.add_column("Status")

            for comp in result.improvements:
                after_text = comp.after_severity or "resolved"
                comparison_table.add_row(
                    comp.problem_type,
                    comp.before_severity,
                    f"[green]{after_text}[/green]",
                    f"[green]{comp.status}[/green]",
                )

            for comp in result.regressions:
                comparison_table.add_row(
                    comp.problem_type,
                    comp.before_severity,
                    f"[bold red]{comp.after_severity}[/bold red]",
                    f"[bold red]{comp.status}[/bold red]",
                )

            console.print(comparison_table)

        # Regressions warning
        if result.regressions:
            console.print(
                "[bold red]Warning: Some problems worsened after processing.[/bold red]"
            )

        console.print(f"\nOutput: {result.output_path}")

    except DependencyMissingError as exc:
        render_error(exc, console)
        sys.exit(1)
    except PhantomError as exc:
        render_error(exc, console)
        sys.exit(1)
