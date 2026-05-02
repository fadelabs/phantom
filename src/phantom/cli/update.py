"""Phantom version checking and self-update commands."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

import rich_click as click
from rich.panel import Panel

from phantom import __version__
from phantom.cli._formatting import get_console, output_json

GITHUB_REPO = "fadelabs/phantom"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
TAGS_URL = f"https://api.github.com/repos/{GITHUB_REPO}/tags?per_page=1"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
PIP_INSTALL_URL = f"git+https://github.com/{GITHUB_REPO}"
CACHE_DIR = Path("~/.phantom").expanduser()
CACHE_FILE = CACHE_DIR / "update-check.json"
CACHE_TTL_HOURS = 24
REQUEST_TIMEOUT = 5


def _parse_version(tag: str) -> tuple[int, ...]:
    """Parse 'v1.2.3' or '1.2.3' into (1, 2, 3)."""
    return tuple(int(x) for x in tag.lstrip("v").split("."))


def _fetch_json(url: str) -> dict | None:
    """Fetch JSON from a URL. Returns None on any failure."""
    req = Request(url, headers={"User-Agent": f"phantom-audio/{__version__}"})
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode())
    except (URLError, OSError, json.JSONDecodeError, ValueError):
        pass
    return None


def _fetch_latest_version() -> str | None:
    """Get the latest version string from GitHub releases or tags."""
    data = _fetch_json(RELEASES_URL)
    if data and "tag_name" in data:
        return data["tag_name"].lstrip("v")

    data = _fetch_json(TAGS_URL)
    if data and isinstance(data, list) and len(data) > 0:
        return data[0].get("name", "").lstrip("v") or None

    return None


def _read_cache() -> dict | None:
    """Read the update check cache file. Returns None if missing/corrupt."""
    try:
        return json.loads(CACHE_FILE.read_text())
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _write_cache(latest: str, current: str) -> None:
    """Write update check result to cache."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps(
                {
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                    "latest_version": latest,
                    "current_version": current,
                }
            )
        )
    except OSError:
        pass


def _clear_cache() -> None:
    """Remove the cache file."""
    try:
        CACHE_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def check_for_update(force: bool = False) -> tuple[str, str] | None:
    """Check GitHub for a newer Phantom version.

    Returns (latest_version, current_version) on success, None on failure.
    Uses a 24h file cache unless force=True.
    """
    try:
        current = __version__

        if not force:
            cache = _read_cache()
            if cache and "checked_at" in cache:
                checked = datetime.fromisoformat(cache["checked_at"])
                age_hours = (
                    datetime.now(timezone.utc) - checked
                ).total_seconds() / 3600
                if age_hours < CACHE_TTL_HOURS:
                    return (cache["latest_version"], cache["current_version"])

        latest = _fetch_latest_version()
        if not latest:
            return None

        _write_cache(latest, current)
        return (latest, current)
    except Exception:
        return None


def is_editable_install() -> bool:
    """Check if phantom-audio is installed in editable (development) mode."""
    try:
        dist = importlib.metadata.distribution("phantom-audio")
        direct_url_text = dist.read_text("direct_url.json")
        if direct_url_text:
            data = json.loads(direct_url_text)
            return data.get("dir_info", {}).get("editable", False)
    except Exception:
        pass
    return False


def _install_type() -> str:
    """Return a human-readable install type string."""
    if is_editable_install():
        return "editable (development)"
    return "standard"


@click.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="Output raw JSON")
def version(json_output: bool) -> None:
    """Show Phantom version and check for updates."""
    console = get_console(json_mode=json_output)

    info = {
        "version": __version__,
        "python": platform.python_version(),
        "os": platform.system(),
        "arch": platform.machine(),
        "install_type": _install_type(),
    }

    result = check_for_update(force=True)

    if result is not None:
        latest, current = result
        info["latest_version"] = latest
        info["update_available"] = _parse_version(latest) > _parse_version(current)
    else:
        info["latest_version"] = None
        info["update_available"] = None

    if json_output:
        output_json(info)
        return

    console.print(
        Panel(
            f"  Version:  [cyan]{info['version']}[/cyan]\n"
            f"  Python:   [cyan]{info['python']}[/cyan]\n"
            f"  OS:       [cyan]{info['os']} {info['arch']}[/cyan]\n"
            f"  Install:  [cyan]{info['install_type']}[/cyan]",
            title="Phantom",
            border_style="cyan",
        )
    )

    if info["update_available"] is None:
        console.print("[dim]Unable to check for updates[/dim]")
    elif info["update_available"]:
        console.print(
            f"[bold yellow]Update available: {info['version']} → "
            f"{info['latest_version']}[/bold yellow]\n"
            f"Run [green]phantom update[/green] to install"
        )
    else:
        console.print(f"[green]Up to date ({info['version']})[/green]")


@click.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def update(yes: bool) -> None:
    """Update Phantom to the latest version."""
    console = get_console()

    result = check_for_update(force=True)

    if result is None:
        console.print(
            Panel(
                "Could not reach GitHub to check for updates.\n"
                f"Check manually: [link={RELEASES_PAGE}]{RELEASES_PAGE}[/link]",
                title="Update Check Failed",
                border_style="red",
            )
        )
        raise SystemExit(1)

    latest, current = result

    if _parse_version(latest) <= _parse_version(current):
        console.print(f"[green]Already up to date ({current})[/green]")
        return

    console.print(f"[bold]Update available:[/bold] {current} → [cyan]{latest}[/cyan]")

    if is_editable_install():
        console.print(
            Panel(
                "You have an editable (development) install.\n"
                "Update with:\n\n"
                "  [green]git pull && pip install -e .[/green]",
                title="Development Install",
                border_style="yellow",
            )
        )
        return

    if not yes:
        if not click.confirm("Update now?", default=True):
            console.print("[dim]Update cancelled[/dim]")
            return

    console.print(f"[dim]Installing phantom-audio {latest}...[/dim]")

    proc = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", PIP_INSTALL_URL],
        capture_output=True,
        text=True,
    )

    if proc.returncode == 0:
        _clear_cache()
        console.print(
            Panel(
                f"[bold green]Updated to {latest}[/bold green]\n"
                "Restart your terminal to use the new version.",
                title="Success",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"pip exited with code {proc.returncode}\n\n"
                f"[dim]{proc.stderr.strip()[:500]}[/dim]",
                title="Update Failed",
                border_style="red",
            )
        )
        raise SystemExit(1)
