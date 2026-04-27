"""Allow running Phantom via: python -m phantom

Invokes the CLI. For the MCP server, use: phantom-mcp
"""

from phantom.cli import cli

if __name__ == "__main__":
    cli()
