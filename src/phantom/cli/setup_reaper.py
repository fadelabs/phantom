"""Phantom setup-reaper command -- guided Reaper MCP bridge installation."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import rich_click as click
from rich.panel import Panel

from phantom.cli._formatting import get_console, output_json

REAPER_MCP_REPO = "https://github.com/fadelabs/reaper-mcp.git"
_DEFAULT_INSTALL_DIR = "~/.phantom/reaper-mcp"


def _get_reaper_scripts_dir() -> Path:
    """Return the OS-specific Reaper Scripts directory path."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "REAPER" / "Scripts"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        return Path(appdata) / "REAPER" / "Scripts"
    else:
        return Path.home() / ".config" / "REAPER" / "Scripts"


def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _run_step(cmd: list[str], step_name: str) -> None:
    """Run a subprocess, raising a clear error on failure."""
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError:
        raise click.ClickException(f"{step_name}: command not found: {cmd[0]}")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode().strip() if e.stderr else str(e)
        raise click.ClickException(f"{step_name} failed:\n{stderr}")


_STARTUP_MARKER = "-- [phantom] auto-start MCP bridge"

_STARTUP_BLOCK = f"""{_STARTUP_MARKER}
dofile(reaper.GetResourcePath() .. "/Scripts/reaper_mcp_bridge.lua")
-- [/phantom]
"""


def _configure_startup_script(scripts_dir: Path, console, json_output: bool) -> bool:
    """Add MCP bridge auto-start to Reaper's __startup.lua.

    Reaper natively auto-executes __startup.lua on launch — no extensions required.
    """
    startup_file = scripts_dir / "__startup.lua"

    if startup_file.exists():
        content = startup_file.read_text()
        if _STARTUP_MARKER in content:
            if not json_output:
                console.print("  Auto-start already configured in __startup.lua")
            return True
        # Append to existing startup file
        new_content = content.rstrip() + "\n\n" + _STARTUP_BLOCK
    else:
        new_content = _STARTUP_BLOCK

    startup_file.write_text(new_content)
    if not json_output:
        console.print(
            "  Configured [green]__startup.lua[/green] — bridge will auto-start with Reaper"
        )
    return True


def _merge_mcp_config(mcp_config: dict, console, yes: bool) -> str | None:
    """Merge reaper MCP config into .mcp.json. Returns path written to."""
    candidates = [Path.cwd() / ".mcp.json", Path.home() / ".mcp.json"]
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
        console.print(
            f"[yellow]Could not parse {target} — skipping auto-config.[/yellow]"
        )
        return None

    servers = existing.setdefault("mcpServers", {})
    if "reaper" in servers:
        if not yes and sys.stdin.isatty():
            if not click.confirm(
                f"Reaper config already exists in {target}. Overwrite?", default=False
            ):
                return None

    servers["reaper"] = mcp_config["mcpServers"]["reaper"]
    target.write_text(json.dumps(existing, indent=2) + "\n")
    return str(target)


@click.command()
@click.option(
    "--install-dir",
    default=None,
    help="Directory to clone reaper-mcp into (default: ~/.phantom/reaper-mcp)",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option("--json", "-j", "json_output", is_flag=True, help="Output raw JSON")
def setup_reaper(install_dir: str | None, yes: bool, json_output: bool) -> None:
    """Set up Reaper MCP bridge for DAW integration.

    Clones the reaper-mcp bridge, installs dependencies,
    copies the Lua bridge to Reaper, and configures MCP.
    """
    console = get_console(json_mode=json_output)

    # --- Pre-flight checks ---
    if not _check_tool("git"):
        console.print(
            Panel(
                "[bold]git[/bold] is required but not installed.\n\n"
                "  macOS:   [green]xcode-select --install[/green]\n"
                "  Ubuntu:  [green]sudo apt install git[/green]\n"
                "  Windows: [green]https://git-scm.com/download/win[/green]",
                title="Missing: git",
                border_style="red",
            )
        )
        sys.exit(1)

    if not _check_tool("uv"):
        console.print(
            Panel(
                "[bold]uv[/bold] is required but not installed.\n\n"
                "  macOS/Linux:  [green]curl -LsSf https://astral.sh/uv/install.sh | sh[/green]\n"
                '  Windows:      [green]powershell -c "irm https://astral.sh/uv/install.ps1 | iex"[/green]\n\n'
                "More info: https://docs.astral.sh/uv/",
                title="Missing: uv",
                border_style="red",
            )
        )
        sys.exit(1)

    install_path = Path(
        install_dir if install_dir else _DEFAULT_INSTALL_DIR
    ).expanduser()
    scripts_dir = _get_reaper_scripts_dir()
    reaper_found = scripts_dir.exists()

    # --- Show plan ---
    if not json_output:
        plan_lines = [
            f"  Clone to:       [cyan]{install_path}[/cyan]",
            f"  Reaper scripts: [cyan]{scripts_dir}[/cyan]",
        ]
        if not reaper_found:
            plan_lines.append(
                "  [yellow]Reaper not detected — Lua copy will be skipped[/yellow]"
            )
        console.print(
            Panel("\n".join(plan_lines), title="Reaper MCP Setup", border_style="cyan")
        )

        if not yes and sys.stdin.isatty():
            if not click.confirm("Proceed?", default=True):
                console.print("[dim]Cancelled.[/dim]")
                return

    # --- Clone or update ---
    if install_path.exists():
        remote_url = ""
        try:
            result = subprocess.run(
                ["git", "-C", str(install_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
            )
            remote_url = result.stdout.strip()
        except Exception:
            pass

        expected_remote = REAPER_MCP_REPO.removesuffix(".git")
        is_fadelabs = remote_url and (
            expected_remote in remote_url or "fadelabs/reaper-mcp" in remote_url
        )
        if remote_url and not is_fadelabs:
            if not json_output:
                console.print(
                    f"[yellow]Existing clone uses a different remote:[/yellow]\n"
                    f"  [dim]{remote_url}[/dim]\n"
                    f"[yellow]Will replace with fadelabs fork.[/yellow]"
                )
            if not yes and sys.stdin.isatty():
                if not click.confirm(
                    "Delete existing clone and re-clone?", default=True
                ):
                    console.print("[dim]Cancelled.[/dim]")
                    return
            shutil.rmtree(install_path)

    if install_path.exists():
        with console.status("[bold blue]Pulling latest changes...", spinner="dots"):
            _run_step(
                ["git", "-C", str(install_path), "pull", "--ff-only"],
                "Git pull",
            )
    else:
        with console.status("[bold blue]Cloning reaper-mcp...", spinner="dots"):
            install_path.parent.mkdir(parents=True, exist_ok=True)
            _run_step(
                ["git", "clone", "--depth", "1", REAPER_MCP_REPO, str(install_path)],
                "Git clone",
            )

    # --- Install Python dependencies ---
    if (install_path / "pyproject.toml").exists():
        with console.status("[bold blue]Installing dependencies...", spinner="dots"):
            _run_step(
                ["uv", "sync", "--directory", str(install_path)],
                "Dependency install",
            )

    # --- Copy Lua bridge to Reaper ---
    lua_copied: list[str] = []
    lua_files = list(install_path.rglob("*.lua"))

    if lua_files and reaper_found:
        for lua_file in lua_files:
            dest = scripts_dir / lua_file.name
            shutil.copy2(str(lua_file), str(dest))
            lua_copied.append(str(dest))
            if not json_output:
                console.print(f"  Copied [green]{lua_file.name}[/green] -> {dest}")
    elif lua_files and not reaper_found and not json_output:
        console.print(
            f"[yellow]Reaper not found at {scripts_dir} — skipping Lua copy.[/yellow]\n"
            "[dim]Install Reaper, then re-run [green]phantom setup-reaper[/green].[/dim]"
        )

    # --- Create bridge data directory ---
    bridge_data_dir = scripts_dir / "mcp_bridge_data"
    if reaper_found:
        bridge_data_dir.mkdir(parents=True, exist_ok=True)

    # --- Configure auto-start via __startup.lua ---
    startup_configured = False
    if reaper_found:
        startup_configured = _configure_startup_script(
            scripts_dir, console, json_output
        )

    # --- Build MCP config ---
    mcp_config = {
        "mcpServers": {
            "reaper": {
                "command": "uv",
                "args": [
                    "run",
                    "--directory",
                    str(install_path),
                    "python",
                    "reaper_mcp_server.py",
                ],
                "cwd": str(install_path),
                "env": {"REAPER_BRIDGE_DIR": str(bridge_data_dir)},
            }
        }
    }

    # --- Auto-install MCP config ---
    config_written_to = None
    if not json_output:
        config_written_to = _merge_mcp_config(mcp_config, console, yes)

    # --- Output ---
    if json_output:
        output_json(
            {
                "install_dir": str(install_path),
                "reaper_scripts_dir": str(scripts_dir),
                "reaper_detected": reaper_found,
                "lua_copied": lua_copied,
                "startup_configured": startup_configured,
                "mcp_config": mcp_config,
                "mcp_config_written_to": config_written_to,
            }
        )
        return

    # Success summary
    summary_lines = [
        "[bold green]Reaper MCP bridge installed.[/bold green]",
        "",
        f"  Install dir:    {install_path}",
    ]
    if lua_copied:
        summary_lines.append(f"  Lua scripts:    {scripts_dir}")
    if startup_configured:
        summary_lines.append("  Auto-start:     __startup.lua configured")
    if config_written_to:
        summary_lines.append(f"  MCP config:     {config_written_to}")

    console.print(Panel("\n".join(summary_lines), title="Done", border_style="green"))

    # Next steps
    if reaper_found and startup_configured:
        console.print(
            Panel(
                "The MCP bridge will start automatically when Reaper launches.\n"
                "Just open Reaper and Claude can connect — no manual steps needed.\n\n"
                "If Reaper is already running, restart it or load the bridge once manually:\n"
                "  Actions > Show action list > Load ReaScript > reaper_mcp_bridge.lua",
                title="Ready",
                border_style="green",
            )
        )
    elif reaper_found:
        bridge_path = scripts_dir / "reaper_mcp_bridge.lua"
        console.print(
            Panel(
                "[bold]Load the bridge script inside Reaper:[/bold]\n\n"
                "  1. Open Reaper\n"
                "  2. Actions > Show action list  (shortcut [green]?[/green])\n"
                "  3. Click [bold]Load ReaScript...[/bold] at bottom-left\n"
                f"  4. Select [cyan]{bridge_path}[/cyan]\n"
                "  5. Click [bold]Run[/bold]\n\n"
                "The bridge must be running in Reaper before Claude can connect.",
                title="Next Step",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                "MCP config is ready. After installing Reaper, run:\n\n"
                "  [green]phantom setup-reaper[/green]\n\n"
                "to copy the Lua bridge and finish setup.",
                title="Next Step",
                border_style="yellow",
            )
        )

    if not config_written_to:
        console.print()
        console.print(
            Panel(
                "Add this to your .mcp.json:\n\n" + json.dumps(mcp_config, indent=2),
                title="MCP Configuration",
                border_style="cyan",
            )
        )
