"""Configure Phantom alongside the independently maintained Ableton MCP server."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import rich_click as click

from phantom._utils import atomic_write_text
from phantom.cli._formatting import output_json
from phantom.cli.setup import _mcp_candidates

ABLETON_PACKAGE = "ableton-mcp==1.4.0"
ABLETON_SERVER_NAME = "AbletonMCP"


def ableton_mcp_entry() -> dict:
    """Pin the server and disable upstream collection of session data."""
    return {
        "command": "uvx",
        "args": ["--from", ABLETON_PACKAGE, "ableton-mcp"],
        "env": {
            "ABLETON_HOST": "127.0.0.1",
            "ABLETON_PORT": "9877",
            "ABLETON_MCP_DISABLE_TELEMETRY": "true",
            "ABLETON_MCP_SKIP_SCRIPT_INSTALL": "true",
        },
    }


def _read_config(path: Path) -> dict:
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError) as exc:
        raise click.ClickException(
            f"Cannot read MCP configuration: {path.name}"
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers", {}), dict):
        raise click.ClickException(
            "MCP configuration must contain an mcpServers object"
        )
    return data


def _install_script(scripts_dir: Path | None) -> None:
    command = ["uvx", "--from", ABLETON_PACKAGE, "ableton-mcp-install-script"]
    if scripts_dir is not None:
        command.extend(["--target", str(scripts_dir.expanduser().resolve())])
    env = {**os.environ, "ABLETON_MCP_DISABLE_TELEMETRY": "true"}
    # This explicit setup step installs the script; server starts never do.
    env.pop("ABLETON_MCP_SKIP_SCRIPT_INSTALL", None)
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=180, env=env, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise click.ClickException(
            "Ableton Remote Script installation failed; retry setup."
        ) from exc
    if result.returncode:
        raise click.ClickException(
            "Ableton Remote Script installation failed: "
            + (result.stderr or result.stdout).strip()[:500]
        )


@click.command("setup-ableton")
@click.option(
    "--config",
    "config_path",
    type=click.Path(path_type=Path),
    help="MCP JSON configuration to update.",
)
@click.option(
    "--scripts-dir",
    type=click.Path(file_okay=False, path_type=Path),
    help="Custom Ableton User Library/Remote Scripts directory.",
)
@click.option(
    "--config-only",
    is_flag=True,
    help="Write MCP configuration without installing the Live Remote Script.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Replace an existing AbletonMCP entry; preserve all other servers.",
)
@click.option(
    "--json", "json_output", is_flag=True, help="Output setup status as JSON."
)
def setup_ableton(
    config_path: Path | None,
    scripts_dir: Path | None,
    config_only: bool,
    force: bool,
    json_output: bool,
) -> None:
    """Install the Ableton Remote Script and configure AbletonMCP alongside Phantom.

    Restart Live, select AbletonMCP under Settings > Link, Tempo & MIDI >
    Control Surface, then restart your MCP client. Audio analysis uses exported
    WAV/AIFF/FLAC files; the external bridge controls Live's session.
    """
    if shutil.which("uvx") is None:
        raise click.ClickException(
            "uvx is required. Install uv, then run setup-ableton again."
        )
    candidates = _mcp_candidates()
    target = (
        config_path.expanduser()
        if config_path
        else next((p for p in candidates if p.exists()), candidates[0])
    )
    data = _read_config(target)
    servers = data.setdefault("mcpServers", {})
    entry = ableton_mcp_entry()
    existing = servers.get(ABLETON_SERVER_NAME)
    if existing is not None and existing != entry and not force:
        raise click.ClickException(
            "AbletonMCP already has a different configuration. Use --force to replace that entry."
        )
    if not config_only:
        _install_script(scripts_dir)
    servers[ABLETON_SERVER_NAME] = entry
    servers.setdefault("phantom", {"command": "phantom-mcp", "args": []})
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, json.dumps(data, indent=2) + "\n")
    status = {
        "status": "configured",
        "config_path": str(target),
        "package": ABLETON_PACKAGE,
        "remote_script": "not_installed" if config_only else "installer_completed",
        "live_connection": "not_verified",
        "next_step": "Restart Live, select AbletonMCP as a Control Surface, restart your MCP client, then call get_session_info.",
    }
    if json_output:
        output_json(status)
    else:
        click.echo(f"Configured AbletonMCP and Phantom in {target}")
        click.echo(status["next_step"])
