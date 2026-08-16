"""Phantom uninstall command -- clean removal of all Phantom artifacts."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path

import rich_click as click
from rich.panel import Panel
from rich.table import Table

from rich.status import Status

from phantom._utils import atomic_write_text
from phantom.cli._formatting import get_console
from phantom.cli.setup_reaper import _remove_startup_block

_PHANTOM_DIR = Path("~/.phantom").expanduser()

_STARTUP_MARKER = "-- [phantom] auto-start MCP bridge"


def _get_reaper_scripts_dir() -> Path:
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "REAPER" / "Scripts"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "REAPER" / "Scripts"
    else:
        return Path.home() / ".config" / "REAPER" / "Scripts"


def _mcp_candidates() -> list[Path]:
    """.mcp.json locations to scan, nearest first.

    Kept as a function rather than an inline list so tests can redirect it away
    from the developer's real config files (see tests/conftest.py).
    """
    return [Path.cwd() / ".mcp.json", Path.home() / ".mcp.json"]


def _find_artifacts() -> dict:
    """Scan for all Phantom artifacts on disk."""
    artifacts: dict = {}

    if _PHANTOM_DIR.exists():
        artifacts["phantom_dir"] = str(_PHANTOM_DIR)

    for mcp_path in _mcp_candidates():
        if mcp_path.exists():
            try:
                data = json.loads(mcp_path.read_text())
                servers = data.get("mcpServers", {})
                if "phantom" in servers or "reaper" in servers:
                    artifacts.setdefault("mcp_configs", []).append(
                        {
                            "path": str(mcp_path),
                            "has_phantom": "phantom" in servers,
                            "has_reaper": "reaper" in servers,
                        }
                    )
            except (json.JSONDecodeError, OSError):
                pass

    scripts_dir = _get_reaper_scripts_dir()
    if scripts_dir.exists():
        bridge_data = scripts_dir / "mcp_bridge_data"
        if bridge_data.exists():
            artifacts["reaper_bridge_data"] = str(bridge_data)

        lua_files = [
            f for f in scripts_dir.glob("*.lua") if f.name == "reaper_mcp_bridge.lua"
        ]
        if lua_files:
            artifacts["reaper_lua_files"] = [str(f) for f in lua_files]

        startup = scripts_dir / "__startup.lua"
        if startup.exists():
            content = startup.read_text()
            if _STARTUP_MARKER in content:
                artifacts["reaper_startup_hook"] = str(startup)

    return artifacts


def _remove_mcp_entries(
    config_path: str, remove_phantom: bool, remove_reaper: bool
) -> bool:
    """Remove phantom and/or reaper entries from an MCP config file.

    Returns True iff the config was successfully rewritten or removed.
    """
    path = Path(config_path)
    try:
        data = json.loads(path.read_text())
        servers = data.get("mcpServers", {})

        if remove_phantom:
            servers.pop("phantom", None)
        if remove_reaper:
            servers.pop("reaper", None)

        if not servers:
            data.pop("mcpServers", None)

        if data:
            atomic_write_text(config_path, json.dumps(data, indent=2) + "\n")
        else:
            path.unlink()
        return True
    except (json.JSONDecodeError, OSError):
        return False


def _remove_startup_hook(startup_path: str) -> bool:
    """Remove the Phantom auto-start block from __startup.lua.

    Delegates the actual stripping to the single canonical implementation in
    ``setup_reaper._remove_startup_block`` so both call sites handle every edge
    (missing end marker, block-only file, no block) identically. This function
    keeps the path I/O and the bool contract: True iff the hook was
    successfully rewritten or removed (including the no-op "no phantom block"
    case), False on any OS error.
    """
    path = Path(startup_path)
    try:
        new_content = _remove_startup_block(path.read_text())
        if new_content is None:
            return True  # no phantom block present -- nothing to do
        if new_content == "":
            path.unlink()  # file held only the phantom block
        else:
            atomic_write_text(startup_path, new_content)
        return True
    except OSError:
        return False


def _uninstall_uv_package(console, removed: list[str]) -> None:
    """Uninstall the phantom-audio uv tool package, recording the outcome."""
    try:
        proc = subprocess.run(
            ["uv", "tool", "uninstall", "phantom-audio"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        console.print(
            "[yellow]Could not uninstall package automatically (timed out). "
            "Run: uv tool uninstall phantom-audio[/yellow]"
        )
        return

    uv_output = (proc.stdout + proc.stderr).lower()

    if proc.returncode == 0 or "uninstalled" in uv_output:
        removed.append("phantom-audio package")
    elif "not installed" in uv_output:
        removed.append("phantom-audio package (already removed)")
    else:
        console.print(
            "[yellow]Could not uninstall package automatically. "
            "Run: uv tool uninstall phantom-audio[/yellow]"
        )


@click.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--keep-config", is_flag=True, help="Keep MCP config entries")
def uninstall(yes: bool, keep_config: bool) -> None:
    """Remove Phantom and all its artifacts.

    Removes ~/.phantom directory, MCP config entries, Reaper bridge
    files, startup hooks, and the uv package itself.
    """
    console = get_console()
    with Status("Scanning for Phantom artifacts...", console=console):
        artifacts = _find_artifacts()

    table = Table(title="Phantom Artifacts Found")
    table.add_column("Item", style="bold")
    table.add_column("Location")

    if "phantom_dir" in artifacts:
        table.add_row("Config & cache", artifacts["phantom_dir"])

    for cfg in artifacts.get("mcp_configs", []):
        entries = []
        if cfg["has_phantom"]:
            entries.append("phantom")
        if cfg["has_reaper"]:
            entries.append("reaper")
        table.add_row(f"MCP config ({', '.join(entries)})", cfg["path"])

    if "reaper_bridge_data" in artifacts:
        table.add_row("Reaper bridge data", artifacts["reaper_bridge_data"])

    for lua in artifacts.get("reaper_lua_files", []):
        table.add_row("Reaper Lua script", lua)

    if "reaper_startup_hook" in artifacts:
        table.add_row("Reaper auto-start hook", artifacts["reaper_startup_hook"])

    table.add_row("uv package", "phantom-audio")

    console.print(table)

    if not artifacts and not yes:
        console.print("\n[dim]No Phantom artifacts found beyond the uv package.[/dim]")

    if not yes:
        console.print()
        if not click.confirm("Remove everything listed above?", default=False):
            console.print("[dim]Uninstall cancelled[/dim]")
            return

    removed: list[str] = []

    if "phantom_dir" in artifacts:
        shutil.rmtree(artifacts["phantom_dir"], ignore_errors=True)
        removed.append("~/.phantom")

    if not keep_config:
        for cfg in artifacts.get("mcp_configs", []):
            if _remove_mcp_entries(cfg["path"], cfg["has_phantom"], cfg["has_reaper"]):
                removed.append(f"MCP entries in {cfg['path']}")
            else:
                console.print(
                    f"[yellow]Could not update {cfg['path']} -- remove the "
                    "phantom/reaper entries manually.[/yellow]"
                )

    if "reaper_bridge_data" in artifacts:
        shutil.rmtree(artifacts["reaper_bridge_data"], ignore_errors=True)
        removed.append("Reaper bridge data")

    for lua in artifacts.get("reaper_lua_files", []):
        try:
            Path(lua).unlink()
            removed.append(f"Lua: {Path(lua).name}")
        except OSError:
            pass

    if "reaper_startup_hook" in artifacts:
        if _remove_startup_hook(artifacts["reaper_startup_hook"]):
            removed.append("Reaper auto-start hook")
        else:
            console.print(
                f"[yellow]Could not update {artifacts['reaper_startup_hook']} -- "
                "remove the phantom auto-start block manually.[/yellow]"
            )

    _uninstall_uv_package(console, removed)

    console.print(
        Panel(
            "[bold green]Phantom removed.[/bold green]\n\n"
            + "\n".join(f"  [dim]{r}[/dim]" for r in removed),
            title="Uninstalled",
            border_style="green",
        )
    )
