# Working with Ableton Live

Use this workflow when the user is working in Live. Reaper Lua recipes and
Reaper plugin parameter mappings do not apply to Ableton.

## Connect and inspect

`phantom setup-ableton` installs the matching Remote Script and configures the
external AbletonMCP server alongside Phantom. The user must restart Live, select
AbletonMCP as a Control Surface, and restart the MCP client. Setup alone does not
prove that the bridge is connected.

List the tools exposed by the installed bridge. Start with `get_session_info`
and, if available, `get_remote_script_info`. Inspect relevant tracks with
`get_track_info`. Treat the current tool schemas as authoritative; different
bridge versions support different operations.

Ask which session to use if more than one DAW is connected. Do not select a DAW
from the existence of its tools alone. Read the session before making changes,
and work on a saved copy when the requested changes are destructive.

## Measure before changing

Export the relevant mix or stems as WAV, AIFF, or FLAC. Analyze those exports
with Phantom. Track names, device settings, and MIDI notes from the Live bridge
are not measurements of the rendered audio.

Use `full_diagnostic` for a file, `batch_diagnostic` for a group of stems, and
`analyze_masking` or `multi_stem_masking` when investigating overlapping parts.
Compare a full mix against a full-mix reference; do not EQ every stem toward a
genre profile. Use `analyze_phase` to investigate mono cancellation.

If a running Phantom Studio instance publishes metrics, `read_live_metrics`
can supplement file analysis. Check the instance ID and stale flag. Never
assume that a snapshot describes the master bus or the track being discussed.

## Apply a small, reversible change

Explain the observation, proposed operation, expected effect, and uncertainty.
Use only available Live tools. Before changing a device, inspect its parameter
names and ranges with `get_device_parameters`, then use `set_device_parameter`
according to its schema. Never substitute Reaper's normalized parameter values
for a Live device's range.

Read track IDs or indices again after creating, deleting, or reordering tracks.
Do not assume an earlier index still names the same instrument. Record the old
parameter values so the move can be reversed. If the bridge exposes undo, group
related operations; otherwise explain how to restore the recorded values.

If the bridge cannot perform an operation, give the user precise manual steps.
Do not invent a tool, claim a render happened, or report a change as applied
without a successful response and readback.

## Check the result

Export the same section with the same rendering settings and analyze it again.
Compare the intended metric, true peak, and any new problems. Offer a
level-matched listening comparison; an increase in loudness alone is not evidence
of an improvement. Keep or undo the change based on those checks and the user's
intent.

Phantom's setup disables upstream AbletonMCP telemetry and server-start script
installation. Preserve those settings unless the user explicitly changes them.

Upstream installation and tools: https://github.com/ahujasid/ableton-mcp
