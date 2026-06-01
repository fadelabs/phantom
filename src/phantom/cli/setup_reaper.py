"""Phantom setup-reaper command -- guided Reaper MCP bridge installation."""

from __future__ import annotations

import difflib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import rich_click as click
from rich.panel import Panel

from phantom._utils import atomic_write_text
from phantom.cli._formatting import get_console, output_json
from phantom import __version__

REAPER_MCP_REPO = "https://github.com/fadelabs/reaper-mcp.git"


def _normalize_git_remote(url: str) -> str:
    """Normalize a git remote URL to 'host/owner/repo' for exact comparison.

    Handles https, ssh:// and scp-style git@host:owner/repo forms so the
    expected-remote check can't be fooled by a substring match (e.g.
    evil.com/fadelabs/reaper-mcp-x).
    """
    u = url.strip().lower().removesuffix(".git").rstrip("/")
    if u.startswith("git@"):
        host, _, path = u[4:].partition(":")
        return f"{host}/{path}"
    for scheme in ("https://", "http://", "ssh://", "git://"):
        if u.startswith(scheme):
            u = u[len(scheme) :]
            break
    # strip optional userinfo@ in the authority component
    authority, _, rest = u.partition("/")
    if "@" in authority:
        authority = authority.split("@", 1)[1]
    return f"{authority}/{rest}" if rest else authority


_DEFAULT_INSTALL_DIR = "~/.phantom/reaper-mcp"
_GIT_TIMEOUT_SECONDS = 30
EXPECTED_LUA_FILES = ["reaper_mcp_bridge.lua"]


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


def _backup_dir(path: Path) -> Path:
    """Move *path* aside to a timestamped backup instead of destroying it.

    Returns the backup path. Used in place of shutil.rmtree so a setup-reaper
    run never irrecoverably deletes a user's prior install (issue #6).
    """
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.parent / f"{path.name}.bak.{ts}"
    suffix = 1
    while backup.exists():
        backup = path.parent / f"{path.name}.bak.{ts}-{suffix}"
        suffix += 1
    shutil.move(str(path), str(backup))
    return backup


def _fresh_clone_staged(
    install_path: Path, allow_unverified: bool, json_output: bool, console
) -> None:
    """Clone + dependency-install into a staging dir, then move into place.

    Transactional (issue #6): the clone and `uv sync` both run inside
    ~/.phantom/.staging/<tmp>; install_path is created only by a final move
    after every step succeeds. If any step fails, the staging dir is removed
    and the live filesystem is left unchanged — no half-installed bridge.

    The bridge is launched via `uv run --directory <install_path>`, which
    revalidates/rebuilds the environment, so the staged .venv being moved is
    self-healing.
    """
    if not json_output:
        console.print("[dim]Installing reaper-mcp...[/dim]")

    install_path.parent.mkdir(parents=True, exist_ok=True)
    staging_root = install_path.parent / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f"{install_path.name}.", dir=str(staging_root))
    )

    try:
        try:
            _run_step(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    f"v{__version__}",
                    REAPER_MCP_REPO,
                    str(staging),
                ],
                "Git clone (version-pinned)",
                timeout=_GIT_TIMEOUT_SECONDS,
            )
        except click.ClickException:
            if not allow_unverified:
                raise click.ClickException(
                    f"Tag v{__version__} not found in reaper-mcp. Refusing to clone "
                    "unverified HEAD. Re-run with --allow-unverified to proceed."
                )
            if not json_output:
                console.print(
                    f"[yellow]Warning: tag v{__version__} not found — "
                    "cloning HEAD (unverified version).[/yellow]"
                )
            # Reset the staging dir so the fallback clones into an empty target.
            shutil.rmtree(staging)
            staging.mkdir()
            _run_step(
                ["git", "clone", "--depth", "1", REAPER_MCP_REPO, str(staging)],
                "Git clone (HEAD fallback)",
                timeout=_GIT_TIMEOUT_SECONDS,
            )

        if (staging / "pyproject.toml").exists():
            _run_step(
                ["uv", "sync", "--directory", str(staging)],
                "Dependency install",
                timeout=120,
            )

        # Every step succeeded — move the staged tree into place (same fs).
        shutil.move(str(staging), str(install_path))
    except BaseException:
        # Any failure: discard staging, leave the live filesystem untouched.
        shutil.rmtree(staging, ignore_errors=True)
        raise
    finally:
        # Best-effort cleanup of the staging root once it's empty.
        try:
            staging_root.rmdir()
        except OSError as e:
            # Ignore only the expected "directory not empty" case; surface
            # other filesystem problems instead of silently swallowing them.
            if getattr(e, "errno", None) not in (39, 145):  # ENOTEMPTY (POSIX/Windows)
                raise


def _run_step(cmd: list[str], step_name: str, timeout: int | None = None) -> None:
    """Run a subprocess, raising a clear error on failure."""
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=timeout)
    except FileNotFoundError as e:
        raise click.ClickException(f"{step_name}: command not found: {cmd[0]} ({e})")
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

    atomic_write_text(startup_file, new_content)
    if not json_output:
        console.print(
            "  Configured [green]__startup.lua[/green] — bridge will auto-start with Reaper"
        )
    return True


def _resolve_mcp_target() -> Path:
    """Pick the .mcp.json to write: first existing of $HOME/cwd, else $HOME."""
    candidates = [Path.home() / ".mcp.json", Path.cwd() / ".mcp.json"]
    return next((c for c in candidates if c.exists()), candidates[0])


def _compute_mcp_merge(mcp_config: dict):
    """Compute the proposed .mcp.json change without writing it.

    Returns (target, old_text, new_text, reaper_exists). new_text is None when
    the existing file can't be parsed (caller should skip auto-config).
    """
    target = _resolve_mcp_target()
    if target.exists():
        try:
            old_text = target.read_text()
            existing = json.loads(old_text)
        except (json.JSONDecodeError, OSError):
            return target, target.read_text() if target.exists() else "", None, False
    else:
        old_text = ""
        existing = {}

    reaper_exists = "reaper" in existing.get("mcpServers", {})
    servers = existing.setdefault("mcpServers", {})
    servers["reaper"] = mcp_config["mcpServers"]["reaper"]
    new_text = json.dumps(existing, indent=2) + "\n"
    return target, old_text, new_text, reaper_exists


def _render_mcp_diff(target: Path, old_text: str, new_text: str, console) -> None:
    """Print a unified diff of the proposed .mcp.json change."""
    diff = "".join(
        difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=f"{target} (current)",
            tofile=f"{target} (proposed)",
        )
    )
    if not diff.strip():
        console.print(f"  [dim]{target} already up to date — no change.[/dim]")
        return
    console.print(f"  [bold].mcp.json change[/bold] ({target}):")
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            console.print(f"    [green]{line}[/green]")
        elif line.startswith("-") and not line.startswith("---"):
            console.print(f"    [red]{line}[/red]")
        else:
            console.print(f"    [dim]{line}[/dim]")


def _remove_startup_block(content: str) -> str | None:
    """Strip the phantom auto-start block from __startup.lua content.

    Returns the new content, or None if no phantom block is present.
    """
    if _STARTUP_MARKER not in content:
        return None
    lines = content.splitlines(keepends=True)
    out, skipping = [], False
    for line in lines:
        if _STARTUP_MARKER in line:
            skipping = True
            continue
        if skipping:
            if "-- [/phantom]" in line:
                skipping = False
            continue
        out.append(line)
    return "".join(out).rstrip() + "\n" if "".join(out).strip() else ""


def _compute_mcp_unmerge():
    """Compute removal of the reaper entry from .mcp.json without writing.

    Returns (target, old_text, new_text, had_reaper). new_text is None when the
    file is absent or unparseable; had_reaper is False when there's nothing to
    remove.
    """
    target = _resolve_mcp_target()
    if not target.exists():
        return target, "", None, False
    try:
        old_text = target.read_text()
        existing = json.loads(old_text)
    except (json.JSONDecodeError, OSError):
        return target, "", None, False
    servers = existing.get("mcpServers", {})
    if "reaper" not in servers:
        return target, old_text, old_text, False
    del servers["reaper"]
    new_text = json.dumps(existing, indent=2) + "\n"
    return target, old_text, new_text, True


def _merge_mcp_config(mcp_config: dict, console, yes: bool) -> str | None:
    """Merge reaper MCP config into .mcp.json, showing the diff. Returns path written."""
    target, old_text, new_text, reaper_exists = _compute_mcp_merge(mcp_config)

    if new_text is None:
        console.print(
            f"[yellow]Could not parse {target} — skipping auto-config.[/yellow]"
        )
        return None

    # Transparency: always show what will change before writing (issue #6).
    _render_mcp_diff(target, old_text, new_text, console)

    if reaper_exists:
        if yes:
            pass  # Explicit --yes flag: user consented to overwrite
        elif sys.stdin.isatty():
            if not click.confirm(
                f"Reaper config already exists in {target}. Overwrite?", default=False
            ):
                return None
        else:
            # Non-interactive, no --yes: refuse silent overwrite
            raise click.ClickException(
                f"Reaper config already exists in {target}. "
                "Run with --yes to overwrite."
            )

    atomic_write_text(target, new_text)
    return str(target)


def _print_dry_run_plan(
    install_path: Path,
    scripts_dir: Path,
    bridge_data_dir: Path,
    mcp_config: dict,
    console,
) -> None:
    """Print exactly what a real run would do, mutating nothing (issue #6)."""
    will_update = install_path.exists() and (install_path / ".git").is_dir()
    console.print("[bold]Dry run — no changes will be made.[/bold]\n")
    if will_update:
        console.print(
            f"  Update existing bridge at [cyan]{install_path}[/cyan] "
            f"(git fetch + checkout v{__version__})"
        )
    else:
        console.print(
            f"  Clone [cyan]{REAPER_MCP_REPO}[/cyan] (tag v{__version__}) "
            f"into [cyan]{install_path}[/cyan]"
        )
    console.print(f"  Run: [dim]uv sync --directory {install_path}[/dim]")
    for name in EXPECTED_LUA_FILES:
        console.print(
            f"  Copy Lua: [dim]{install_path / name}[/dim] -> [dim]{scripts_dir / name}[/dim]"
        )
    console.print(f"  Create bridge data dir: [dim]{bridge_data_dir}[/dim]")
    startup = scripts_dir / "__startup.lua"
    if startup.exists() and _STARTUP_MARKER in startup.read_text():
        console.print(f"  Auto-start: already configured in [dim]{startup}[/dim]")
    else:
        console.print(f"  Configure auto-start in [dim]{startup}[/dim]")
    target, old_text, new_text, _ = _compute_mcp_merge(mcp_config)
    if new_text is None:
        console.print(
            f"  [yellow]{target} cannot be parsed — would skip auto-config.[/yellow]"
        )
    else:
        _render_mcp_diff(target, old_text, new_text, console)
    console.print("\n[dim]Re-run without --dry-run to apply.[/dim]")


def _do_uninstall(
    install_path: Path,
    scripts_dir: Path,
    console,
    json_output: bool,
    dry_run: bool,
    yes: bool,
) -> None:
    """Reverse a setup-reaper install (issue #6).

    Backs up the bridge dir, removes copied Lua + bridge data, strips the
    phantom block from __startup.lua, and removes the reaper entry from
    .mcp.json. Honors --dry-run and --yes.
    """
    lua_targets = [scripts_dir / name for name in EXPECTED_LUA_FILES]
    lua_present = [p for p in lua_targets if p.exists()]
    bridge_data = scripts_dir / "mcp_bridge_data"
    startup = scripts_dir / "__startup.lua"
    startup_has_block = startup.exists() and _STARTUP_MARKER in startup.read_text()
    mcp_target, _old, mcp_new, had_reaper = _compute_mcp_unmerge()

    nothing = not any(
        [
            install_path.exists(),
            lua_present,
            bridge_data.exists(),
            startup_has_block,
            had_reaper,
        ]
    )
    if nothing:
        if json_output:
            output_json({"uninstalled": False, "reason": "nothing to remove"})
        else:
            console.print(
                "[dim]Nothing to uninstall — no Phantom Reaper bridge found.[/dim]"
            )
        return

    if dry_run:
        if not json_output:
            console.print("[bold]Dry run — nothing will be removed.[/bold]\n")
            if install_path.exists():
                console.print(f"  Back up + remove bridge: [dim]{install_path}[/dim]")
            for p in lua_present:
                console.print(f"  Remove Lua: [dim]{p}[/dim]")
            if bridge_data.exists():
                console.print(f"  Remove bridge data: [dim]{bridge_data}[/dim]")
            if startup_has_block:
                console.print(f"  Strip phantom block from [dim]{startup}[/dim]")
            if had_reaper:
                console.print(f"  Remove 'reaper' entry from [dim]{mcp_target}[/dim]")
            console.print("\n[dim]Re-run without --dry-run to apply.[/dim]")
        else:
            output_json(
                {
                    "uninstalled": False,
                    "dry_run": True,
                    "install_dir": str(install_path) if install_path.exists() else None,
                    "lua": [str(p) for p in lua_present],
                    "bridge_data": str(bridge_data) if bridge_data.exists() else None,
                    "startup_block": startup_has_block,
                    "mcp_entry": str(mcp_target) if had_reaper else None,
                }
            )
        return

    if not yes:
        if sys.stdin.isatty():
            if not click.confirm("Remove the Phantom Reaper bridge?", default=False):
                raise click.ClickException("Aborted.")
        else:
            raise click.ClickException("Run with --yes to uninstall non-interactively.")

    backup = None
    if install_path.exists():
        backup = _backup_dir(install_path)
    for p in lua_present:
        p.unlink()
    if bridge_data.exists():
        shutil.rmtree(bridge_data)
    if startup_has_block:
        new_startup = _remove_startup_block(startup.read_text())
        if new_startup:
            atomic_write_text(startup, new_startup)
        else:
            startup.unlink()  # file held only the phantom block
    if had_reaper and mcp_new is not None:
        atomic_write_text(mcp_target, mcp_new)

    if json_output:
        output_json(
            {
                "uninstalled": True,
                "backup": str(backup) if backup else None,
                "lua_removed": [str(p) for p in lua_present],
                "mcp_entry_removed": had_reaper,
            }
        )
    else:
        console.print(
            Panel(
                "[bold green]Phantom Reaper bridge removed.[/bold green]"
                + (f"\n\n  Bridge backed up to: {backup}" if backup else ""),
                title="Uninstalled",
                border_style="green",
            )
        )


@click.command()
@click.option(
    "--install-dir",
    default=None,
    help="Directory to clone reaper-mcp into (default: ~/.phantom/reaper-mcp)",
)
@click.option("--json", "-j", "json_output", is_flag=True, help="Output raw JSON")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show exactly what would be installed/changed without touching anything",
)
@click.option(
    "--uninstall",
    is_flag=True,
    help="Remove the Phantom Reaper bridge (backs up the install, reverts config)",
)
@click.option(
    "--allow-unverified",
    is_flag=True,
    help="Permit cloning reaper-mcp HEAD when the version tag is missing (runs unverified code)",
)
def setup_reaper(
    install_dir: str | None,
    json_output: bool,
    yes: bool,
    dry_run: bool,
    uninstall: bool,
    allow_unverified: bool,
) -> None:
    """Set up Reaper MCP bridge for DAW integration.

    Auto-detects Reaper installation, clones the bridge, copies Lua scripts,
    configures auto-start, and writes MCP config. No prompts needed.

    Use --dry-run to preview every action (clone target, install command, Lua
    file destinations, and the .mcp.json diff) without changing anything.
    """
    console = get_console(json_mode=json_output)

    install_path = Path(
        install_dir if install_dir else _DEFAULT_INSTALL_DIR
    ).expanduser()
    scripts_dir = _get_reaper_scripts_dir()

    # Uninstall reverses a prior install and needs neither git/uv nor a
    # detected Reaper — handle it before the install-only preconditions.
    if uninstall:
        _do_uninstall(install_path, scripts_dir, console, json_output, dry_run, yes)
        return

    if not _check_tool("git"):
        raise click.ClickException(
            "git is required. Install: xcode-select --install (macOS), "
            "sudo apt install git (Linux), or https://git-scm.com (Windows)"
        )

    if not _check_tool("uv"):
        raise click.ClickException(
            "uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
        )

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

    # Build the MCP config + bridge paths up front so --dry-run can preview the
    # exact .mcp.json change without performing any installation.
    bridge_data_dir = scripts_dir / "mcp_bridge_data"
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

    if dry_run:
        if json_output:
            target, _old, _new, _exists = _compute_mcp_merge(mcp_config)
            output_json(
                {
                    "dry_run": True,
                    "install_dir": str(install_path),
                    "reaper_scripts_dir": str(scripts_dir),
                    "would_update": install_path.exists()
                    and (install_path / ".git").is_dir(),
                    "clone_url": REAPER_MCP_REPO,
                    "version_tag": f"v{__version__}",
                    "uv_sync_cmd": ["uv", "sync", "--directory", str(install_path)],
                    "lua_files": {
                        name: str(scripts_dir / name) for name in EXPECTED_LUA_FILES
                    },
                    "bridge_data_dir": str(bridge_data_dir),
                    "mcp_config_target": str(target),
                    "mcp_config": mcp_config,
                }
            )
        else:
            _print_dry_run_plan(
                install_path, scripts_dir, bridge_data_dir, mcp_config, console
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

        is_fadelabs = bool(remote_url) and _normalize_git_remote(
            remote_url
        ) == _normalize_git_remote(REAPER_MCP_REPO)
        if not is_fadelabs:
            if yes:
                # Explicit --yes flag: user consented. Back up, don't destroy.
                backup = _backup_dir(install_path)
                if not json_output:
                    console.print(
                        f"  Backed up existing install to [dim]{backup}[/dim]"
                    )
            elif sys.stdin.isatty():
                if not click.confirm(
                    f"{install_path} has a different remote ({remote_url or 'unknown'}). "
                    "Back up and re-clone?",
                    default=False,
                ):
                    raise click.ClickException(
                        "Aborted. Choose a different --install-dir."
                    )
                backup = _backup_dir(install_path)
                console.print(f"  Backed up existing install to [dim]{backup}[/dim]")
            else:
                # Non-interactive, no --yes: refuse destructive action
                raise click.ClickException(
                    f"{install_path} has a different remote ({remote_url or 'unknown'}). "
                    "Run with --yes to back up and re-clone, or choose a different --install-dir."
                )

    if install_path.exists():
        # --- Update an existing, verified install in place ---
        if not json_output:
            console.print("[dim]Updating reaper-mcp...[/dim]")
        _run_step(
            ["git", "-C", str(install_path), "fetch", "--tags"],
            "Git fetch",
            timeout=_GIT_TIMEOUT_SECONDS,
        )
        try:
            _run_step(
                ["git", "-C", str(install_path), "checkout", f"v{__version__}"],
                "Git checkout version tag",
                timeout=_GIT_TIMEOUT_SECONDS,
            )
        except click.ClickException:
            if not json_output:
                console.print(
                    f"[yellow]Warning: tag v{__version__} not found — "
                    "staying on current version (unverified).[/yellow]"
                )
        if (install_path / "pyproject.toml").exists():
            _run_step(
                ["uv", "sync", "--directory", str(install_path)],
                "Dependency install",
                timeout=120,  # 2-minute timeout for dependency install
            )
    else:
        # --- Fresh install: stage clone + sync, then move into place ---
        _fresh_clone_staged(install_path, allow_unverified, json_output, console)

    # --- Copy Lua bridge to Reaper ---
    lua_copied: list[str] = []
    # Only copy top-level .lua files — avoid test/example scripts in subdirectories
    lua_files = list(install_path.glob("*.lua"))

    for lua_file in lua_files:
        if lua_file.name not in EXPECTED_LUA_FILES:
            if not json_output:
                console.print(
                    f"[yellow]Skipping unexpected Lua file: {lua_file.name}[/yellow]"
                )
            continue
        dest = scripts_dir / lua_file.name
        shutil.copy2(str(lua_file), str(dest))
        lua_copied.append(str(dest))

    # --- Create bridge data directory ---
    # bridge_data_dir / mcp_config were computed before the dry-run gate above.
    bridge_data_dir.mkdir(parents=True, exist_ok=True)

    # --- Configure auto-start via __startup.lua ---
    _configure_startup_script(scripts_dir, console, json_output)

    # --- Write MCP config (shows a diff before writing) ---
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
