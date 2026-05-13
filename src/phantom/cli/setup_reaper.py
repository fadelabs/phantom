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
_GIT_TIMEOUT_SECONDS = 30


def _get_reaper_scripts_dir() -> Path:
    """Return the OS-specific Reaper Scripts directory path."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "REAPER" / "Scripts"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return Path.home() / "AppData" / "Roaming" / "REAPER" / "Scripts"
        return Path(appdata) / "REAPER" / "Scripts"
    else:
        return Path.home() / ".config" / "REAPER" / "Scripts"


def _check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def _run_step(cmd: list[str], step_name: str, timeout: int | None = None) -> None:
    """Run a subprocess, raising a clear error on failure."""
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
    except FileNotFoundError:
        raise click.ClickException(f"{step_name}: command not found: {cmd[0]}")
    except subprocess.TimeoutExpired:
        raise click.ClickException(
            f"{step_name} timed out after {timeout} seconds. "
            "Check your connection and try again."
        )
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

    # Atomic write: temp file + rename
    tmp_path = str(startup_file) + ".tmp"
    Path(tmp_path).write_text(new_content)
    os.replace(tmp_path, str(startup_file))
    if not json_output:
        console.print(
            "  Configured [green]__startup.lua[/green] — bridge will auto-start with Reaper"
        )
    return True


def _merge_mcp_config(mcp_config: dict, console, yes: bool) -> str | None:
    """Merge reaper MCP config into .mcp.json. Returns path written to."""
    candidates = [Path.home() / ".mcp.json", Path.cwd() / ".mcp.json"]
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
    # Atomic write: temp file + rename
    tmp_path = str(target) + ".tmp"
    Path(tmp_path).write_text(json.dumps(existing, indent=2) + "\n")
    os.replace(tmp_path, str(target))
    return str(target)


@click.command()
@click.option(
    "--install-dir",
    default=None,
    help="Directory to clone reaper-mcp into (default: ~/.phantom/reaper-mcp)",
)
@click.option("--json", "-j", "json_output", is_flag=True, help="Output raw JSON")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
def setup_reaper(install_dir: str | None, json_output: bool, yes: bool) -> None:
    """Set up Reaper MCP bridge for DAW integration.

    Auto-detects Reaper installation, clones the bridge, copies Lua scripts,
    configures auto-start, and writes MCP config. No prompts needed.
    """
    console = get_console(json_mode=json_output)

    if not _check_tool("git"):
        raise click.ClickException(
            "git is required. Install: xcode-select --install (macOS), "
            "sudo apt install git (Linux), or https://git-scm.com (Windows)"
        )

    if not _check_tool("uv"):
        raise click.ClickException(
            "uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )

    install_path = Path(
        install_dir if install_dir else _DEFAULT_INSTALL_DIR
    ).expanduser()
    scripts_dir = _get_reaper_scripts_dir()
    reaper_found = scripts_dir.exists()

    if not reaper_found:
        if json_output:
            output_json(
                {"reaper_detected": False, "reaper_scripts_dir": str(scripts_dir)}
            )
        else:
            console.print(
                f"[dim]Reaper not detected at {scripts_dir} — skipping setup.[/dim]"
            )
        return

    # --- Clone or update ---
    if install_path.exists():
        is_git_repo = (install_path / ".git").is_dir()

        if not is_git_repo:
            raise click.ClickException(
                f"{install_path} exists but is not a git repository. "
                "Remove it manually or choose a different --install-dir."
            )

        remote_url = ""
        try:
            result = subprocess.run(
                ["git", "-C", str(install_path), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            remote_url = result.stdout.strip()
        except Exception:
            pass

        expected_remote = REAPER_MCP_REPO.removesuffix(".git")
        is_fadelabs = remote_url and (
            expected_remote in remote_url or "fadelabs/reaper-mcp" in remote_url
        )
        if not is_fadelabs:
            if not yes and sys.stdin.isatty():
                if not click.confirm(
                    f"{install_path} has a different remote ({remote_url or 'unknown'}). "
                    "Remove and re-clone?",
                    default=False,
                ):
                    raise click.ClickException(
                        "Aborted. Choose a different --install-dir."
                    )
            shutil.rmtree(install_path)

    if install_path.exists():
        if not json_output:
            console.print("[dim]Updating reaper-mcp...[/dim]")
        _run_step(
            ["git", "-C", str(install_path), "pull", "--ff-only"],
            "Git pull",
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    else:
        if not json_output:
            console.print("[dim]Installing reaper-mcp...[/dim]")
        install_path.parent.mkdir(parents=True, exist_ok=True)
        _run_step(
            ["git", "clone", "--depth", "1", REAPER_MCP_REPO, str(install_path)],
            "Git clone",
            timeout=_GIT_TIMEOUT_SECONDS,
        )

    # --- Install Python dependencies ---
    if (install_path / "pyproject.toml").exists():
        _run_step(
            ["uv", "sync", "--directory", str(install_path)],
            "Dependency install",
        )

    # --- Copy Lua bridge to Reaper ---
    lua_copied: list[str] = []
    # Only copy top-level .lua files — avoid test/example scripts in subdirectories
    lua_files = list(install_path.glob("*.lua"))

    for lua_file in lua_files:
        dest = scripts_dir / lua_file.name
        shutil.copy2(str(lua_file), str(dest))
        lua_copied.append(str(dest))

    # --- Create bridge data directory ---
    bridge_data_dir = scripts_dir / "mcp_bridge_data"
    bridge_data_dir.mkdir(parents=True, exist_ok=True)

    # --- Configure auto-start via __startup.lua ---
    _configure_startup_script(scripts_dir, console, json_output)

    # --- Write MCP config ---
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

    config_written_to = _merge_mcp_config(mcp_config, console, yes=yes)

    # --- Output ---
    if json_output:
        output_json(
            {
                "install_dir": str(install_path),
                "reaper_scripts_dir": str(scripts_dir),
                "reaper_detected": True,
                "lua_copied": lua_copied,
                "startup_configured": True,
                "mcp_config": mcp_config,
                "mcp_config_written_to": config_written_to,
            }
        )
        return

    console.print(
        Panel(
            "[bold green]Reaper MCP bridge ready.[/bold green]\n\n"
            f"  Bridge:     {install_path}\n"
            f"  Lua:        {scripts_dir}\n"
            "  Auto-start: configured\n"
            + (f"  MCP config: {config_written_to}" if config_written_to else ""),
            title="Done",
            border_style="green",
        )
    )
    console.print(
        "[dim]Restart Reaper if it's running. The bridge auto-starts on launch.[/dim]"
    )
