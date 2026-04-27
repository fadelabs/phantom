"""Phantom doctor command -- diagnose installation health."""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path

import rich_click as click
from rich.panel import Panel
from rich.table import Table

from phantom import __version__
from phantom.cli._formatting import get_console, output_json

# Core deps: package name -> import name
_CORE_DEPS = {
    "numpy": "numpy",
    "scipy": "scipy",
    "soundfile": "soundfile",
    "essentia": "essentia",
    "pydantic": "pydantic",
    "fastmcp": "fastmcp",
}

# Optional deps: package name -> import name
_OPTIONAL_DEPS = {
    "demucs": "demucs",
    "matchering": "matchering",
    "pedalboard": "pedalboard",
    "librosa": "librosa",
}

_ENV_VARS = [
    "PHANTOM_AUDIO_DIR",
    "PHANTOM_OUTPUT_DIR",
    "PHANTOM_PROFILES_DIR",
    "PHANTOM_MAX_DURATION",
    "PHANTOM_MAX_FILE_SIZE",
]

OK = "[green]OK[/green]"
FAIL = "[red]FAIL[/red]"
WARN = "[yellow]--[/yellow]"


def _try_import(name: str) -> tuple[bool, str]:
    """Try to import a package. Returns (success, version_or_error)."""
    try:
        mod = __import__(name)
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "?"))
        return True, str(version)
    except Exception as exc:
        return False, str(exc)


def _check_mcp_config(path: Path) -> bool | None:
    """Check if 'phantom' key exists in an MCP config file. Returns None if file missing."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        servers = data.get("mcpServers", {})
        return "phantom" in servers
    except (json.JSONDecodeError, OSError):
        return False


def _collect_results() -> dict:
    """Collect all diagnostic results into a dict."""
    from phantom.cli.setup_reaper import _get_reaper_scripts_dir

    results: dict = {"ok": True}

    # 1. Phantom info
    results["phantom"] = {
        "version": __version__,
        "python": platform.python_version(),
        "os": platform.system(),
        "arch": platform.machine(),
    }

    # 2. Core deps
    core = {}
    for pkg, imp in _CORE_DEPS.items():
        ok, ver = _try_import(imp)
        core[pkg] = {"ok": ok, "version": ver}
        if not ok:
            results["ok"] = False
    results["core_deps"] = core

    # 3. Optional deps
    optional = {}
    for pkg, imp in _OPTIONAL_DEPS.items():
        ok, ver = _try_import(imp)
        optional[pkg] = {"ok": ok, "version": ver}
    results["optional_deps"] = optional

    # 4. Environment vars
    env = {}
    for var in _ENV_VARS:
        val = os.environ.get(var)
        entry: dict = {"set": val is not None, "value": val}
        if val and var.endswith("_DIR"):
            entry["exists"] = Path(val).expanduser().exists()
        env[var] = entry
    results["env_vars"] = env

    # 5. External tools
    results["ffmpeg"] = shutil.which("ffmpeg") is not None

    # 6. MCP config
    results["mcp_config"] = {
        "local": _check_mcp_config(Path.cwd() / ".mcp.json"),
        "global": _check_mcp_config(Path.home() / ".mcp.json"),
    }

    # 7. Reaper integration
    install_dir = Path("~/.phantom/reaper-mcp").expanduser()
    scripts_dir = _get_reaper_scripts_dir()
    lua_files = list(scripts_dir.glob("*.lua")) if scripts_dir.exists() else []
    results["reaper"] = {
        "bridge_installed": install_dir.exists(),
        "scripts_dir": str(scripts_dir),
        "lua_scripts_found": len(lua_files),
    }

    return results


@click.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="Output raw JSON")
def doctor(json_output: bool) -> None:
    """Diagnose Phantom installation health.

    Checks core and optional dependencies, environment variables,
    external tools, MCP configuration, and Reaper integration.
    """
    console = get_console(json_mode=json_output)
    results = _collect_results()

    if json_output:
        output_json(results)
        sys.exit(0 if results["ok"] else 1)

    # --- Phantom info ---
    info = results["phantom"]
    console.print(
        Panel(
            f"  Version:  [cyan]{info['version']}[/cyan]\n"
            f"  Python:   [cyan]{info['python']}[/cyan]\n"
            f"  OS:       [cyan]{info['os']}[/cyan]\n"
            f"  Arch:     [cyan]{info['arch']}[/cyan]",
            title="Phantom",
            border_style="cyan",
        )
    )

    # --- Core deps ---
    table = Table(title="Core Dependencies")
    table.add_column("Package", style="bold")
    table.add_column("Version")
    table.add_column("Status")

    for pkg, dep in results["core_deps"].items():
        status = OK if dep["ok"] else FAIL
        ver = dep["version"] if dep["ok"] else "[dim]not installed[/dim]"
        table.add_row(pkg, ver, status)

    console.print(table)

    # --- Optional deps ---
    table = Table(title="Optional Extras")
    table.add_column("Package", style="bold")
    table.add_column("Version")
    table.add_column("Status")

    for pkg, dep in results["optional_deps"].items():
        status = OK if dep["ok"] else WARN
        ver = dep["version"] if dep["ok"] else "[dim]not installed[/dim]"
        table.add_row(pkg, ver, status)

    console.print(table)

    # --- Environment vars ---
    table = Table(title="Environment Variables")
    table.add_column("Variable", style="bold")
    table.add_column("Value")
    table.add_column("Status")

    for var, entry in results["env_vars"].items():
        if not entry["set"]:
            table.add_row(var, "[dim]not set[/dim]", WARN)
        elif "exists" in entry:
            status = OK if entry["exists"] else FAIL
            table.add_row(var, entry["value"], status)
        else:
            table.add_row(var, entry["value"], OK)

    console.print(table)

    # --- External tools ---
    table = Table(title="External Tools")
    table.add_column("Tool", style="bold")
    table.add_column("Status")

    ffmpeg_status = OK if results["ffmpeg"] else f"{WARN} [dim]not on PATH[/dim]"
    table.add_row("ffmpeg", ffmpeg_status)

    console.print(table)

    # --- MCP config ---
    table = Table(title="MCP Configuration")
    table.add_column("Location", style="bold")
    table.add_column("Status")

    for loc, label in [("local", "./.mcp.json"), ("global", "~/.mcp.json")]:
        val = results["mcp_config"][loc]
        if val is None:
            table.add_row(label, f"{WARN} [dim]file not found[/dim]")
        elif val:
            table.add_row(label, f"{OK} phantom configured")
        else:
            table.add_row(label, f"{WARN} [dim]phantom key missing[/dim]")

    console.print(table)

    # --- Reaper ---
    reaper = results["reaper"]
    table = Table(title="Reaper Integration")
    table.add_column("Check", style="bold")
    table.add_column("Status")

    bridge_status = (
        OK if reaper["bridge_installed"] else f"{WARN} [dim]not installed[/dim]"
    )
    table.add_row("MCP bridge (~/.phantom/reaper-mcp)", bridge_status)

    lua_status = (
        f"{OK} {reaper['lua_scripts_found']} found"
        if reaper["lua_scripts_found"] > 0
        else f"{WARN} [dim]none found[/dim]"
    )
    table.add_row(f"Lua scripts ({reaper['scripts_dir']})", lua_status)

    console.print(table)

    # --- Summary ---
    if results["ok"]:
        console.print(
            Panel(
                "[bold green]All core dependencies OK.[/bold green]",
                border_style="green",
            )
        )
    else:
        failed = [p for p, d in results["core_deps"].items() if not d["ok"]]
        console.print(
            Panel(
                f"[bold red]Missing core dependencies:[/bold red] {', '.join(failed)}\n\n"
                "Install with: [green]pip install phantom-audio[/green]",
                title="Action Required",
                border_style="red",
            )
        )

    sys.exit(0 if results["ok"] else 1)
