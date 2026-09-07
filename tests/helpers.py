"""Shared assertions and decoding for MCP contract tests."""

import json

from fastmcp.exceptions import ToolError


def parse_tool_error(error: ToolError) -> dict:
    """Decode the JSON object carried by a Phantom MCP ToolError."""
    payload = json.loads(str(error))
    assert isinstance(payload, dict), "Expected a structured error object"
    return payload
