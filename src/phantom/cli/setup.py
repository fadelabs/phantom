"""Phantom setup command -- one-command onboarding."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import rich_click as click
from rich.panel import Panel
from rich.status import Status

from phantom.cli._formatting import get_console, output_json

OK = "[green]OK[/green]"
SKIP = "[dim]skipped[/dim]"
WARN = "[yellow]--[/yellow]"

_PHANTOM_MCP_ENTRY = {
    "command": "phantom-mcp",
    "args": [],
}


def _mcp_candidates() -> list[Path]:
    return [Path.home() / ".mcp.json", Path.cwd() / ".mcp.json"]


def _setup_mcp_config(console, json_mode: bool) -> dict:
    """Write phantom entry to .mcp.json. Returns status dict."""
    candidates = _mcp_candidates()
    target = None

    for candidate in candidates:
        if candidate.exists():
            target = candidate
            break

    if target is None:
        target = candidates[0]

    try:
        if target.exists():
            existing = json.loads(target.read_text())
        else:
            existing = {}
    except (json.JSONDecodeError, OSError):
        if not json_mode:
            console.print(f"  {WARN} Could not parse {target}")
        return {
            "step": "mcp",
            "status": "error",
            "message": f"Could not parse {target}",
        }

    servers = existing.setdefault("mcpServers", {})

    if "phantom" in servers:
        if not json_mode:
            console.print(f"  {SKIP} Phantom MCP server already configured in {target}")
        return {"step": "mcp", "status": "skipped", "path": str(target)}

    servers["phantom"] = _PHANTOM_MCP_ENTRY

    tmp = str(target) + ".tmp"
    Path(tmp).write_text(json.dumps(existing, indent=2) + "\n")
    os.replace(tmp, str(target))

    if not json_mode:
        console.print(f"  {OK} Phantom MCP server configured in {target}")
    return {"step": "mcp", "status": "configured", "path": str(target)}


def _setup_plugin(console, json_mode: bool) -> dict:
    """Register Claude Code plugin. Returns status dict."""
    if not shutil.which("claude"):
        if not json_mode:
            console.print(
                f"  {WARN} Claude Code not installed — install from [cyan]claude.ai/code[/cyan]"
            )
        return {
            "step": "plugin",
            "status": "skipped",
            "message": "claude CLI not found",
        }

    _MARKETPLACE_URL = "https://github.com/fadelabs/phantom.git"
    _PLUGIN_NAME = "phantom"

    try:
        # Add marketplace if not already added
        proc = subprocess.run(
            ["claude", "plugin", "marketplace", "add", _MARKETPLACE_URL],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Ignore errors if already added

        # Install plugin
        proc = subprocess.run(
            ["claude", "plugin", "install", _PLUGIN_NAME],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            if not json_mode:
                console.print(f"  {OK} Claude Code plugin installed")
            return {"step": "plugin", "status": "configured"}
        elif "already installed" in (proc.stdout + proc.stderr).lower():
            if not json_mode:
                console.print(f"  {SKIP} Claude Code plugin already installed")
            return {"step": "plugin", "status": "skipped"}
        else:
            msg = (proc.stderr or proc.stdout).strip()[:200] or "unknown error"
            if not json_mode:
                console.print(f"  {WARN} Plugin install failed: {msg}")
            return {"step": "plugin", "status": "error", "message": msg}
    except (subprocess.TimeoutExpired, OSError) as e:
        if not json_mode:
            console.print(f"  {WARN} Plugin install failed: {e}")
        return {"step": "plugin", "status": "error", "message": str(e)}


def _setup_reaper(console, json_mode: bool) -> dict:
    """Run Reaper bridge setup. Returns status dict."""
    from phantom.cli.setup_reaper import _get_reaper_scripts_dir

    scripts_dir = _get_reaper_scripts_dir()
    if not scripts_dir.exists():
        if not json_mode:
            console.print(f"  {SKIP} Reaper not detected — skipped")
        return {"step": "reaper", "status": "skipped", "message": "Reaper not detected"}

    import io
    import contextlib

    try:
        from phantom.cli.setup_reaper import setup_reaper as _run_reaper_setup

        ctx = click.Context(_run_reaper_setup, info_name="setup-reaper")
        with contextlib.redirect_stdout(io.StringIO()):
            ctx.invoke(_run_reaper_setup, json_output=True)
        if not json_mode:
            console.print(f"  {OK} Reaper bridge configured")
        return {"step": "reaper", "status": "configured"}
    except SystemExit:
        if not json_mode:
            console.print(f"  {OK} Reaper bridge configured")
        return {"step": "reaper", "status": "configured"}
    except Exception as e:
        if not json_mode:
            console.print(f"  {WARN} Reaper setup issue: {e}")
        return {"step": "reaper", "status": "error", "message": str(e)}


@click.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="Output raw JSON")
@click.option("--skip-reaper", is_flag=True, help="Skip Reaper bridge setup")
@click.option(
    "--skip-plugin", is_flag=True, help="Skip Claude Code plugin registration"
)
def setup(json_output: bool, skip_reaper: bool, skip_plugin: bool) -> None:
    """Set up Phantom: MCP server, Claude Code plugin, and Reaper bridge.

    Configures everything needed to use Phantom with Claude Code.
    Skips anything already configured.
    """
    console = get_console(json_mode=json_output)
    results = []

    if not json_output:
        console.print(Panel("[bold]Setting up Phantom[/bold]", border_style="cyan"))

    # 1. MCP config
    if not json_output:
        with Status("Configuring MCP server...", console=console):
            results.append(_setup_mcp_config(console, json_output))
    else:
        results.append(_setup_mcp_config(console, json_output))

    # 2. Claude Code plugin
    if skip_plugin:
        if not json_output:
            console.print(f"  {SKIP} Plugin registration skipped (--skip-plugin)")
        results.append(
            {"step": "plugin", "status": "skipped", "message": "--skip-plugin"}
        )
    else:
        if not json_output:
            with Status("Registering Claude Code plugin...", console=console):
                results.append(_setup_plugin(console, json_output))
        else:
            results.append(_setup_plugin(console, json_output))

    # 3. Reaper
    if skip_reaper:
        if not json_output:
            console.print(f"  {SKIP} Reaper setup skipped (--skip-reaper)")
        results.append(
            {"step": "reaper", "status": "skipped", "message": "--skip-reaper"}
        )
    else:
        if not json_output:
            with Status("Setting up Reaper bridge...", console=console):
                results.append(_setup_reaper(console, json_output))
        else:
            results.append(_setup_reaper(console, json_output))

    if json_output:
        output_json({"steps": results})
        return

    # 4. Check for optional extras
    console.print()
    extras = {
        "separation": ("Stem separation (Demucs + PyTorch)", "~2.5GB download"),
        "matching": ("Reference matching", "GPLv3 license"),
        "processing": ("Audio processing engine (Pedalboard)", ""),
    }
    missing_extras = []
    for extra, (label, note) in extras.items():
        try:
            if extra == "separation":
                import demucs  # noqa: F401
            elif extra == "matching":
                import matchering  # noqa: F401
            elif extra == "processing":
                import pedalboard  # noqa: F401
        except ImportError:
            suffix = f" ({note})" if note else ""
            missing_extras.append((extra, f"{label}{suffix}"))

    if missing_extras:
        console.print("[bold]Optional extras not installed:[/bold]")
        for extra, label in missing_extras:
            console.print(f"  [dim]•[/dim] {label}")
        console.print()
        if sys.stdin.isatty() and click.confirm("Install optional extras now?", default=False):
            # Map extras to their actual package names
            extra_packages = {
                "separation": "demucs",
                "matching": "matchering",
                "processing": "pedalboard",
            }
            with_args = []
            for extra, _ in missing_extras:
                pkg = extra_packages.get(extra, extra)
                with_args.extend(["--with", pkg])

            with Status("Installing extras (this may take a few minutes)...", console=console):
                proc = subprocess.run(
                    ["uv", "tool", "install", "phantom-audio",
                     "--python", "3.13", "--force"] + with_args,
                    capture_output=True,
                    text=True,
                    timeout=900,
                )
            if proc.returncode == 0:
                for _, label in missing_extras:
                    console.print(f"  {OK} {label}")
            else:
                pkgs = " ".join(f"--with {extra_packages.get(e, e)}" for e, _ in missing_extras)
                console.print(f"  {WARN} Install failed. Run manually:")
                console.print(f"    uv tool install phantom-audio --python 3.13 {pkgs}")

    console.print()
    console.print(
        Panel(
            "[bold green]Setup complete.[/bold green]",
            border_style="green",
        )
    )
