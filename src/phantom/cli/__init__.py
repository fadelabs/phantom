"""Phantom CLI -- professional audio analysis from the terminal."""

from __future__ import annotations

import importlib
import warnings

import rich_click as click

from phantom import __version__

# rich-click configuration for pro audio aesthetic (D-06)
click.rich_click.TEXT_MARKUP = "rich"
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_COMMANDS_TABLE_COLUMN_WIDTH_RATIO = (1, 2)


@click.group()
@click.version_option(version=__version__, prog_name="phantom")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Phantom: AI audio engineering toolkit.

    Analyze, compare, separate, and render audio files
    with professional terminal output.
    """
    # Auto-setup on first run (skip for setup/uninstall/version/update)
    if ctx.invoked_subcommand not in (None, "setup", "uninstall", "version", "update"):
        try:
            import json
            from pathlib import Path

            mcp_home = Path.home() / ".mcp.json"
            mcp_cwd = Path.cwd() / ".mcp.json"
            phantom_configured = False
            for mcp_path in (mcp_home, mcp_cwd):
                if mcp_path.exists():
                    data = json.loads(mcp_path.read_text())
                    if "phantom" in data.get("mcpServers", {}):
                        phantom_configured = True
                        break
            if not phantom_configured:
                click.echo(
                    click.style(
                        "First run detected — running phantom setup...",
                        bold=True,
                    ),
                    err=True,
                )
                ctx.invoke(cli.commands["setup"])
        except Exception:
            pass

    # Check for updates
    if ctx.invoked_subcommand not in (None, "version", "update", "setup", "uninstall"):
        try:
            from phantom.cli.update import _parse_version, check_for_update

            result = check_for_update()
            if result is not None:
                latest, current = result
                if _parse_version(latest) > _parse_version(current):
                    click.echo(
                        click.style(
                            f"Update available: {current} → {latest}"
                            ' — run "phantom update"',
                            dim=True,
                        ),
                        err=True,
                    )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Subcommand registration
# ---------------------------------------------------------------------------
# Uses importlib to distinguish "module doesn't exist yet" (silently skipped)
# from "module exists but has a broken import" (warning emitted).

_COMMANDS = {
    "phantom.cli.analyze": ("analyze", None),
    "phantom.cli.compare": ("compare", None),
    "phantom.cli.separate": ("separate", None),
    "phantom.cli.render": ("render", None),
    "phantom.cli.setup_reaper": ("setup_reaper", "setup-reaper"),
    "phantom.cli.doctor": ("doctor", None),
    "phantom.cli.fix": ("fix", None),
}

for _module_path, (_attr_name, _cli_name) in _COMMANDS.items():
    try:
        _mod = importlib.import_module(_module_path)
        _cmd = getattr(_mod, _attr_name)
        cli.add_command(_cmd, name=_cli_name)
    except ModuleNotFoundError:
        pass  # Module genuinely doesn't exist yet (development)
    except ImportError as _exc:
        warnings.warn(f"Failed to load {_module_path}: {_exc}")


# ---------------------------------------------------------------------------
# Version & update commands (separate from _COMMANDS to avoid duplicate key)
# ---------------------------------------------------------------------------

try:
    from phantom.cli.update import update as _update_cmd
    from phantom.cli.update import version as _version_cmd

    cli.add_command(_version_cmd)
    cli.add_command(_update_cmd)
except ImportError:
    pass

try:
    from phantom.cli.uninstall import uninstall as _uninstall_cmd

    cli.add_command(_uninstall_cmd)
except ImportError:
    pass

try:
    from phantom.cli.setup import setup as _setup_cmd

    cli.add_command(_setup_cmd)
except ImportError:
    pass


# ---------------------------------------------------------------------------
# D-05 resolution: 'phantom serve' as MCP server alias
# ---------------------------------------------------------------------------
# Keeps phantom-mcp entry point unchanged (backward compatible).
# Both invoke the same server.main(). See D-05 in 12-CONTEXT.md.


@cli.command(name="serve")
def serve() -> None:
    """Start the Phantom MCP server (stdio transport).

    Alias for the phantom-mcp entry point. Use this or phantom-mcp
    in your .mcp.json configuration.
    """
    from phantom.server import main

    main()
