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
def cli() -> None:
    """Phantom: AI audio engineering toolkit.

    Analyze, compare, separate, and render audio files
    with professional terminal output.
    """


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
