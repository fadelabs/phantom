# Reaper MCP Server Comparison

Three actively maintained Reaper MCP servers are available for use with Phantom. Any MCP-compatible Reaper server works -- Phantom recommends TwelveTake for its compound tool support and lack of tool name collisions.

## Comparison Table

| Feature | TwelveTake-Studios/reaper-mcp | bonfire-audio/reaper-mcp | Total Reaper MCP (shiehn) |
|---------|-------------------------------|--------------------------|---------------------------|
| Tools | 130 across 12 categories | 58 across 10 categories | 600+ (full), 53 default |
| Architecture | Lua bridge + file-based IPC | python-reapy | Lua bridge + file-based IPC |
| Installation | Clone repo, copy Lua script | `pip install reaper-mcp-server` | Clone repo, run install script |
| PyPI | No | Yes | No |
| Compound tools | Yes (sidechain, mastering chain, parallel comp) | Limited (mastering chain, limiter) | No built-in compounds |
| Undo handling | Wrapped in undo blocks natively | Not documented | Not documented |
| License | MIT | MIT | MIT |
| Platform | macOS, Windows, Linux | macOS, Windows, Linux | macOS, Windows, Linux |
| Latency | ~50ms per call (file-based IPC) | Varies (reapy IPC) | ~50ms per call (file-based IPC) |
| Tool name collisions with Phantom | None | Yes (`analyze_loudness`, `analyze_dynamics`, etc.) | None |

## When to Choose Each

### TwelveTake-Studios/reaper-mcp (Recommended)

Best compound tool support, native undo safety, and no tool name collisions with Phantom. Compound tools like `setup_sidechain_compression`, `add_mastering_chain`, and `add_parallel_compression` map directly to Phantom recipe operations. Requires manual install from GitHub.

**Best for:** Most users. Especially those following Phantom's workflow recipes.

### bonfire-audio/reaper-mcp

Simplest install via `pip install reaper-mcp-server`. Good for users who prefer PyPI packages and need a quick setup. Has analysis tool name collisions with Phantom (`analyze_loudness`, `analyze_dynamics`, `analyze_frequency_spectrum`, `analyze_stereo_field`, `detect_clipping`) -- Claude Code's server namespacing resolves these, but you may need to specify "Use Phantom's `analyze_loudness`" in prompts when ambiguous.

**Best for:** Users who prefer pip install over manual GitHub setup, or who want MIDI-focused tools.

### Total Reaper MCP (shiehn)

Most comprehensive tool count with 600+ tools across all profiles. The profiles system lets you choose which tools to expose (dsl-production, mixing, full, etc.). The default profile exposes only 53 tools; the "mixing" profile (~120 tools) is closest to Phantom's needs. Adds configuration complexity compared to TwelveTake.

**Best for:** Power users who need full ReaScript coverage or natural-language DSL parameters.

## External References

- [TwelveTake-Studios/reaper-mcp](https://github.com/TwelveTake-Studios/reaper-mcp) (130 tools, MIT, verified April 2026)
- [bonfire-audio/reaper-mcp](https://github.com/bonfire-audio/reaper-mcp) (58 tools, MIT, PyPI: reaper-mcp-server 0.1.7, verified April 2026)
- [Total Reaper MCP](https://github.com/shiehn/total-reaper-mcp) (600+ tools, MIT, verified April 2026)

For setup instructions, see [setup-guide.md](setup-guide.md).
