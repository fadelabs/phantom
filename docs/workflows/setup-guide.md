# Reaper MCP Setup Guide

Phantom's analysis MCP server works alongside a Reaper MCP server. Phantom handles measurement and analysis (spectrum, loudness, dynamics, problems, masking). The Reaper MCP server handles DAW control (track creation, FX insertion, routing, automation). Claude Code connects to both servers simultaneously.

## Prerequisites

- **Reaper DAW** installed ([reaper.fm](https://www.reaper.fm/))
- **Python 3.8+** (for TwelveTake's MCP server)
- **Phantom installed** (via `uv` -- see main README)
- **TwelveTake-Studios/reaper-mcp** cloned from GitHub: [github.com/TwelveTake-Studios/reaper-mcp](https://github.com/TwelveTake-Studios/reaper-mcp) (130 tools, MIT license, verified April 2026)

## Installing TwelveTake reaper-mcp

1. Clone the repository:

   ```bash
   git clone https://github.com/TwelveTake-Studios/reaper-mcp.git
   ```

2. Install Python dependencies:

   ```bash
   cd reaper-mcp
   pip install -r requirements.txt
   ```

3. Copy `reaper_mcp_bridge.lua` to Reaper's Scripts folder:

   | Platform | Scripts Folder |
   |----------|----------------|
   | macOS | `~/Library/Application Support/REAPER/Scripts/` |
   | Windows | `%APPDATA%\REAPER\Scripts\` |
   | Linux | `~/.config/REAPER/Scripts/` |

4. Load the bridge script in Reaper:
   - Open Reaper
   - Go to **Actions > Show Action List**
   - Click **Load ReaScript**
   - Select `reaper_mcp_bridge.lua`
   - Click **Run**

The bridge script runs as a deferred action inside Reaper, polling for IPC requests from the MCP server.

## Dual MCP Server Configuration

Add both servers to your project's `.mcp.json` file:

```json
{
  "mcpServers": {
    "phantom": {
      "command": "uv",
      "args": ["run", "python", "-m", "phantom"],
      "cwd": "/path/to/phantom"
    },
    "reaper": {
      "command": "python",
      "args": ["/path/to/reaper-mcp/reaper_mcp_server.py"],
      "env": {}
    }
  }
}
```

> **Security warning:** Update `/path/to/phantom` and `/path/to/reaper-mcp` to the actual paths on your machine. Do NOT commit credentials or API keys in `.mcp.json`. If your project's `.mcp.json` is tracked by git, ensure it contains only paths, not secrets.

## Startup Order

The two MCP servers have different startup requirements:

1. **Open Reaper**
2. **Run the bridge script:** Actions > Run ReaScript > `reaper_mcp_bridge.lua` (or add it to Reaper's startup actions for automatic loading)
3. **Start Claude Code** -- both MCP servers initialize on session start
4. **Verify:** Run `/mcp` in Claude Code. You should see both `phantom` and `reaper` servers listed with their tools.

> **Important:** Phantom's server starts on demand (Python process via `uv run`). Reaper MCP requires a live Reaper instance with the bridge script running BEFORE starting Claude Code. If Reaper is not running or the bridge is not loaded, the Reaper MCP server will fail to connect and its tools will not appear.

## Tool Namespacing

Claude Code prefixes every MCP tool with the server name that provides it:

- Phantom tools: `mcp__phantom__analyze_spectrum`, `mcp__phantom__analyze_loudness`, etc.
- Reaper tools: `mcp__reaper__get_track_count`, `mcp__reaper__insert_track`, etc.

**bonfire-audio collision note:** If using bonfire-audio's reaper-mcp server (which has analysis tools like `analyze_loudness`, `analyze_dynamics`), Claude Code's namespacing resolves the collisions automatically. Use explicit server prefix in prompts when ambiguous: "Use Phantom's `analyze_loudness`" vs "Use Reaper's `analyze_loudness`". TwelveTake's server uses DAW-control-focused names (e.g., `track_fx_add_by_name`, `insert_track`) that do not collide with Phantom's analysis tool names.

## Troubleshooting

**Reaper MCP tools not appearing in `/mcp`:**
The bridge script is not running. Open Reaper, go to Actions > Run ReaScript > select `reaper_mcp_bridge.lua`. Then restart Claude Code so it re-initializes the MCP connection.

**Connection lost after Reaper crash:**
Stdio MCP servers are NOT automatically reconnected. Restart Reaper, re-run the bridge script, then restart Claude Code.

**Phantom tools not appearing:**
Check that `uv run python -m phantom` runs without errors in a terminal. Verify that `.mcp.json` has the correct `cwd` path pointing to the Phantom project root.

**Wrong analysis results (bonfire-audio users):**
If using bonfire-audio's server, verify you are calling Phantom's analysis tools (prefixed `mcp__phantom__`) and not Reaper's built-in analysis. The two implementations return different result formats.

## Latency Expectations

File-based IPC adds ~50ms per Reaper MCP call. Typical operation times:

| Operation | Approximate Calls | Approximate Time |
|-----------|-------------------|------------------|
| Single track insert + FX | 3-5 | ~150-250ms |
| Session setup recipe (~20 calls) | ~20 | ~1-2 seconds |
| Full mix workflow (~50+ calls) | ~50+ | ~3-5 seconds |

Claude is executing sequentially, not frozen. For compound operations, each step completes before the next begins.

## Alternative Servers

For a comparison of all available Reaper MCP servers, see [server-comparison.md](server-comparison.md).
