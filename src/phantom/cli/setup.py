"""Phantom setup command -- one-command onboarding."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import rich_click as click
from rich.panel import Panel

from phantom.cli._formatting import get_console, output_json

OK = "[green]OK[/green]"
SKIP = "[dim]skipped[/dim]"
WARN = "[yellow]--[/yellow]"

_PHANTOM_MCP_ENTRY = {
    "command": "phantom-mcp",
    "args": [],
}


def _mcp_candidates() -> list[Path]:
    return [Path.cwd() / ".mcp.json", Path.home() / ".mcp.json"]


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

    plugin_dir = Path(__file__).resolve().parent.parent.parent.parent / "plugin"
    if not (plugin_dir / ".claude-plugin" / "plugin.json").exists():
        if not json_mode:
            console.print(
                f"  {WARN} Plugin not bundled in this install. "
                "Install from the repo: [cyan]claude plugin install "
                "https://github.com/fadelabs/phantom[/cyan]"
            )
        return {
            "step": "plugin",
            "status": "skipped",
            "message": "plugin not bundled — install from GitHub repo",
        }

    try:
        proc = subprocess.run(
            ["claude", "plugin", "install", str(plugin_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode == 0:
            if not json_mode:
                console.print(f"  {OK} Claude Code plugin registered")
            return {"step": "plugin", "status": "configured"}
        else:
            msg = proc.stderr.strip()[:200] if proc.stderr else "unknown error"
            if not json_mode:
                console.print(f"  {WARN} Plugin registration failed: {msg}")
            return {"step": "plugin", "status": "error", "message": msg}
    except (subprocess.TimeoutExpired, OSError) as e:
        if not json_mode:
            console.print(f"  {WARN} Plugin registration failed: {e}")
        return {"step": "plugin", "status": "error", "message": str(e)}


def _setup_reaper(console, json_mode: bool) -> dict:
    """Run Reaper bridge setup. Returns status dict."""
    from phantom.cli.setup_reaper import _get_reaper_scripts_dir

    scripts_dir = _get_reaper_scripts_dir()
    if not scripts_dir.exists():
        if not json_mode:
            console.print(f"  {SKIP} Reaper not detected — skipped")
        return {"step": "reaper", "status": "skipped", "message": "Reaper not detected"}

    try:
        from phantom.cli.setup_reaper import setup_reaper as _run_reaper_setup

        ctx = click.Context(_run_reaper_setup, info_name="setup-reaper")
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
    results.append(_setup_mcp_config(console, json_output))

    # 2. Claude Code plugin
    if skip_plugin:
        if not json_output:
            console.print(f"  {SKIP} Plugin registration skipped (--skip-plugin)")
        results.append(
            {"step": "plugin", "status": "skipped", "message": "--skip-plugin"}
        )
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
        results.append(_setup_reaper(console, json_output))

    if json_output:
        output_json({"steps": results})
        return

    # 4. Run doctor
    console.print()
    from phantom.cli.doctor import _collect_results

    doctor_results = _collect_results()
    ok = doctor_results.get("ok", False)
    if ok:
        console.print(
            Panel(
                "[bold green]Setup complete. Run phantom doctor for details.[/bold green]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[bold yellow]Setup complete with warnings. Run phantom doctor for details.[/bold yellow]",
                border_style="yellow",
            )
        )
