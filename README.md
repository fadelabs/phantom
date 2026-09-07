# Phantom

Phantom measures audio and gives an AI assistant evidence to work with. Analyze a mix or a folder of stems, compare it with a reference, and investigate loudness, tonal balance, stereo behavior, phase, and frequency masking.

Use it as a command-line tool, a Python library, or an MCP server. The Claude Code plugin adds five skills for interpreting the measurements and planning a mix. Separate Reaper and Ableton MCP integrations let an assistant work inside your DAW.

[Documentation](https://fadelab.net/docs/overview?utm_source=github&utm_medium=readme) · [Getting started](https://fadelab.net/docs/getting-started?utm_source=github&utm_medium=readme) · [Tool reference](https://fadelab.net/docs/tools-index?utm_source=github&utm_medium=readme) · [Releases](https://github.com/fadelabs/phantom/releases)

## Start with one file

Phantom supports macOS and Linux with Python 3.10–3.13. The commands below use 3.13. **Windows is not supported:** the Essentia dependency has no Windows wheel. A replacement backend is tracked in [issue #52](https://github.com/fadelabs/phantom/issues/52).

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv tool install phantom-audio --python 3.13
phantom analyze mix.wav
phantom analyze mix.wav --json
phantom compare mix.wav --reference reference.wav
phantom doctor
```

The CLI works without an AI assistant. First use may run setup to configure the MCP server and Claude Code plugin; you can also run `phantom setup` explicitly.

For an assistant, try: “Analyze these stems. Prioritize technical problems, explain the measurements, and tell me what you would check by listening before changing anything.”

## What you can do

- **Check a recording before mixing.** Look for digital clipping, DC offset, mains hum, noise, and stereo polarity problems. Batch diagnostics also report differing sample rates.
- **Compare a mix with a reference.** Measure loudness, relative octave-band balance, dynamics, and stereo differences. Nine genre profiles provide starting targets when you do not have a reference file.
- **Find competing stems.** Rank pairs by weighted octave-band overlap to decide where to investigate masking. The score is a heuristic; it does not establish that one instrument is inaudible.
- **Try corrective processing.** With the processing extra, apply EQ and other Pedalboard operations or use recipes for selected detected problems. `fix_audio` reports before/after findings, including regressions.
- **Read meters from Phantom Studio.** `read_live_metrics` reads local snapshots from the separate Studio preview plugin. Studio is not included in this package.

The measurements support an engineering decision. They cannot decide whether distortion is intentional, whether a reference suits a song, or whether a change sounds better.

## Analysis tools

The MCP server exposes 20 tools over stdio:

| Purpose | Tools |
|---|---|
| Measure a file | `analyze_spectrum`, `analyze_loudness`, `analyze_dynamics`, `analyze_stereo`, `analyze_phase`, `detect_problems` |
| Compare stems | `compare_phase`, `analyze_masking`, `multi_stem_masking` |
| Compare targets | `compare_to_profile`, `compare_to_reference`, `list_profiles`, `load_profile` |
| Process audio | `match_to_reference`, `separate_stems`, `fix_audio`, `apply_processing` |
| Diagnose a session | `full_diagnostic`, `batch_diagnostic`, `read_live_metrics` |

Loudness is measured from the individual channels. Clipping checks either channel and accounts for integer PCM's positive rail. For analyses based on a mono signal, Phantom uses the loudest channel if stereo cancellation would otherwise turn active audio into a silent downmix. Phase and stereo measurements still describe the original channels.

## Optional processing

Install the capabilities you need into the same isolated environment:

```bash
# Corrective EQ, compression, and other Pedalboard effects
uv tool install --force 'phantom-audio[processing]' --python 3.13

# Add reference matching and stem separation as well
uv tool install --force 'phantom-audio[all]' --python 3.13
```

The `matching` extra uses Matchering. The `separation` extra installs the sibling `phantom-audio-separation` package and Demucs/PyTorch; these are a substantially larger download, and first use downloads model weights. `analysis` adds librosa for optional cross-validation. None is needed for the core analysis tools.

```bash
phantom fix vocal.wav --output vocal-fixed.wav
phantom separate mix.wav --output stems
phantom render mix.wav --reference reference.wav --output matched.wav
phantom render mix.wav --format flac --output converted.flac
```

Relative output paths resolve inside `~/.phantom/output` by default. Set `PHANTOM_OUTPUT_DIR` to an existing directory to write elsewhere. Format conversion also requires the `ffmpeg` executable.

Corrective processing writes 32-bit float WAVs to preserve precision and headroom. It does not restore clipped samples, perform source-aware de-essing, or guarantee improvement. An EQ cut around 7 kHz is a static tonal change, not a dynamic de-esser. Listen to the result and inspect reported regressions.

## Use with an MCP client

Run `phantom-mcp` or `phantom serve` for the stdio server. A client that accepts MCP JSON configuration can use:

```json
{
  "mcpServers": {
    "phantom": {
      "command": "phantom-mcp",
      "args": []
    }
  }
}
```

The executable must be on the client's PATH. See [assistant configuration](https://fadelab.net/docs/configuring-assistants) for client-specific setup.

The Claude Code plugin supplies these skills:

| Skill | Focus |
|---|---|
| `audio-diagnostician` | Assess recordings and prioritize findings |
| `session-architect` | Organize tracks, routing, and session structure |
| `mix-engineer` | Balance, EQ, dynamics, and reference comparison |
| `effects-engineer` | Reverb, delay, modulation, and creative chains |
| `mastering-engineer` | Final tonal, dynamics, and delivery checks |

## Work in a DAW

Phantom analyzes files; a separate MCP server controls the DAW. Export a mix or stems, analyze them, make a proposed change, then export and measure again. Check the bridge's available tools before attempting an operation.

### Reaper

```bash
phantom setup-reaper
```

This installs the [Phantom Reaper MCP fork](https://github.com/fadelabs/reaper-mcp), copies its Lua bridge, and configures the MCP entry and startup script. Existing installations and conflicting configurations may require an explicit choice; read setup's result before assuming it is connected. Open Reaper and verify the bridge responds before editing a session.

The plugin includes Reaper recipes for routing, FX, automation, and session setup. Plugin parameter names and ranges vary; discover them before setting values. Some third-party plugins expose limited parameters to the host.

### Ableton Live

```bash
phantom setup-ableton
```

This runs the Remote Script installer from `ableton-mcp==1.4.0` and configures `AbletonMCP` alongside Phantom. It preserves other MCP entries, uses loopback port 9877, and disables upstream telemetry. Restart Live, select **AbletonMCP** as a Control Surface in its MIDI settings, then restart your MCP client and call `get_session_info` to verify the connection.

For a custom User Library, pass `--scripts-dir '/path/to/User Library/Remote Scripts'`. Use `--config PATH` to select an MCP JSON file, or `--config-only` to configure the client without installing the script. Setup refuses to replace a different existing Ableton entry unless you pass `--force`.

The external [Ableton MCP project](https://github.com/ahujasid/ableton-mcp) supplies Live control. Phantom's audio analysis still uses exported files. Reaper Lua recipes cannot be run in Live; use the Ableton workflow guidance and only the tools exposed by your installed bridge. A real Live-session smoke test is still required for this integration; setup and configuration tests do not establish DAW compatibility.

## Reference profiles

Built-in profiles: `ambient`, `edm`, `electronic`, `hip-hop`, `lo-fi`, `metal`, `pop`, `rock`, and `rock-metal`.

Profiles describe broad spectral and dynamics tendencies. They are not mastering rules for every song, and a full-mix profile is not an appropriate tonal target for every isolated stem. Streaming normalization levels are playback references, not a requirement to master every release to one LUFS value.

## Privacy and limits

Audio analysis runs locally. If you connect an AI assistant, the measurements and tool results it receives are subject to that provider's configuration and data policy. Optional separation downloads model weights. The standalone installers report install status, OS, architecture, version, selected extras, and a per-install identifier to `fadelab.net`; they do not send audio or raw error logs.

To opt out of installer telemetry:

```bash
curl -sSL https://fadelab.net/install | PHANTOM_NO_TELEMETRY=1 bash
```

Put the variable on `bash`, which runs the installer. Direct `uv tool install` does not run Phantom's shell installer. Ableton MCP is a separate project; Phantom's generated configuration explicitly disables its telemetry.

Inputs may come from anywhere unless `PHANTOM_AUDIO_DIR` is set. Outputs are always confined to the output directory. Default per-file limits are 15 minutes, 500 MB on disk, and 1 GB decoded. Large batches and resampling have additional memory guards. Live snapshots are limited to 1 MB and flagged stale after 10 seconds.

WAV, FLAC, AIFF, OGG, and other libsndfile formats are supported for analysis. MP3/AAC/M4A/WMA are rejected by the loader; convert them with `phantom render` first. Only mono and stereo audio are supported. Technical and tonal problem detectors are heuristics and may miss or misclassify material; a high-frequency cutoff alone is not proof of lossy encoding.

## Configuration

Phantom reads its settings from environment variables. The full runtime set is 40 `PHANTOM_*` variables — paths and limits, analysis thresholds, FFT/frame sizes, and behavior flags — and `phantom doctor` prints the complete list with the value each has in your environment (or that it is unset). All analysis thresholds and frame sizes are knobs on `AnalysisSettings` (`src/phantom/_settings.py`), each overridable through its `PHANTOM_*` env var with the documented default. Settings resolve per call, so a change takes effect without a restart, and the analysis cache keys on your settings — a tuned run is never served a result computed under different settings.

### Paths and Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `PHANTOM_AUDIO_DIR` | *(none)* | Restrict input file reads to this directory tree. When unset, inputs may be read from anywhere (Phantom's core use case); writes are always confined regardless. |
| `PHANTOM_OUTPUT_DIR` | `~/.phantom/output` | Directory all file writes are confined to. Writes outside it are rejected. Created on demand when unset; set this to write elsewhere. |
| `PHANTOM_PROFILES_DIR` | *(built-ins)* | Custom reference profile directory (overrides built-ins). |
| `PHANTOM_METRICS_DIR` | *(platform default)* | Directory for live metrics snapshots: `~/Library/PhantomStudio/metrics` (macOS), `%APPDATA%\PhantomStudio\metrics` (Windows), `~/.config/PhantomStudio/metrics` (Linux). |
| `PHANTOM_MAX_DURATION` | 900 (15 min) | Maximum audio duration in seconds |
| `PHANTOM_MAX_FILE_SIZE` | 500000000 (500 MB) | Maximum file size in bytes |
| `PHANTOM_MAX_DECODED_BYTES` | 1000000000 (1 GB) | Maximum decoded float32 footprint per audio file in bytes |
| `PHANTOM_MAX_AGGREGATE_BYTES` | 4000000000 (4 GB) | Combined decoded-size cap for multi-file tools |

### Analysis Thresholds

| Variable | Default | Description |
|----------|---------|-------------|
| `PHANTOM_POLARITY_THRESHOLD` | -0.5 | Overall L/R correlation below this flags polarity inversion |
| `PHANTOM_PHAT_WINDOW_S` | 10.0 | GCC-PHAT cross-correlation window in seconds |
| `PHANTOM_CREST_FACTOR_LOW_DB` | 6.0 | Crest factor below this marks the track as over-compressed |
| `PHANTOM_CLIPPING_THRESHOLD` | 1.0 | Sample magnitude at or above this counts as clipping |
| `PHANTOM_DC_OFFSET_THRESHOLD` | 0.0005 | Mean sample value above this flags DC offset |
| `PHANTOM_ISP_OVERSHOOT_DB` | 0.5 | True-peak overshoot above this flags inter-sample peaks |
| `PHANTOM_ISP_SEVERE_DBTP` | -1.0 | True peak above this raises ISP severity to significant |
| `PHANTOM_DYNAMIC_SPREAD_MIN_DB` | 10.0 | Minimum P90-P10 block spread to trust a noise-floor estimate |
| `PHANTOM_NOISE_FLOOR_MODERATE_DB` | -50.0 | Noise floor above this is flagged moderate |
| `PHANTOM_NOISE_FLOOR_MINOR_DB` | -60.0 | Noise floor above this is flagged minor |
| `PHANTOM_SNR_PROFESSIONAL_DB` | 60.0 | SNR at or above this counts as professional |
| `PHANTOM_SNR_POOR_DB` | 50.0 | SNR below this is flagged poor/significant |
| `PHANTOM_SPECTRAL_FLATNESS_MIN` | 0.01 | Minimum flatness to run band-excess detectors |
| `PHANTOM_BAND_EXCESS_THRESHOLD_DB` | 6.0 | Band energy above expected level triggers detection |
| `PHANTOM_RESONANCE_MEDIAN_FLOOR_DB` | -40.0 | Median spectral level floor for resonance detection |
| `PHANTOM_RESONANCE_PROMINENCE_DB` | 12 | Peak prominence threshold for resonance detection |
| `PHANTOM_LOSSY_SHELF_DROP_DB` | 20.0 | Shelf drop above this indicates a lossy codec |
| `PHANTOM_MASKING_SEVERITY_HIGH` | 0.6 | Overlap score at or above this is labeled high severity |
| `PHANTOM_MASKING_SEVERITY_MODERATE` | 0.3 | Overlap score at or above this is labeled moderate severity |
| `PHANTOM_MASKING_SEVERITY_LOW` | 0.1 | Overlap score at or above this is labeled low severity |
| `PHANTOM_MASKING_FLOOR_DB` | 40.0 | Bands more than this below the pair peak are zeroed before scoring |

### FFT / Frame Sizes

| Variable | Default | Description |
|----------|---------|-------------|
| `PHANTOM_SPECTRAL_FRAME_SIZE` | 2048 | Frame size of the main spectral analysis pass |
| `PHANTOM_SPECTRAL_HOP_SIZE` | 1024 | Hop size of the main spectral analysis pass |
| `PHANTOM_OCTAVE_FRAME_SIZE` | 4096 | Frame size of the octave-band energy pass (spectral + masking) |
| `PHANTOM_OCTAVE_HOP_SIZE` | 2048 | Hop size of the octave-band energy pass |
| `PHANTOM_FLATNESS_FRAME_SIZE` | 4096 | Frame size of the spectral-flatness gate (band-excess detectors) |
| `PHANTOM_SPECTRUM_FRAME_SIZE` | 8192 | Frame size of the shared power-spectrum pass (resonance, lossy-codec detection) |

> Changing frame sizes changes the analysis geometry, so results are not numerically comparable with the built-in genre profiles or reference-target comparisons, both of which are calibrated to the default frame sizes. Reset the knobs to defaults before comparing, or re-run the comparison under the same tuned geometry.

### Output and Behavior

| Variable | Default | Description |
|----------|---------|-------------|
| `PHANTOM_MASKING_TOP_N` | *(auto)* | Number of top masking pairs returned (scales with stem count when unset) |
| `PHANTOM_PROFILE_MERGE` | *(none)* | Merge a user profile over the built-in instead of replacing it |
| `PHANTOM_PROFILE_OVERRIDE_QUIET` | *(none)* | Silence the user-profile-override log line |
| `PHANTOM_DEBUG` | *(none)* | Enable verbose error output from MCP tools |
| `PHANTOM_QUIET` | *(none)* | Suppress startup preflight messages |

The installers (`install.sh`, `install.ps1`) honor `PHANTOM_NO_TELEMETRY` to opt out of install telemetry; see the Telemetry section.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding conventions, and how to submit changes.

## License

Phantom is licensed under [AGPL-3.0](LICENSE).

**What you can do:**
- Use Phantom for any purpose, personal or commercial
- Modify the code and distribute your modified version
- Use the MCP tools and CLI in your own workflow without restriction

**What AGPL requires:**
- If you modify Phantom and run it as a network service (e.g., a hosted API that wraps Phantom's analysis), you must publish your modified source under AGPL-3.0
- If you distribute a modified version, same thing. Publish the source.
- Using Phantom unmodified as a tool in your workflow does not trigger this

**Want to use Phantom in a proprietary product?** [Commercial licensing](https://fadelab.net?utm_source=github&utm_medium=readme#footer) is available. Contact hello@fadelab.net.

**Patent Notice:** Phantom's weighted frequency masking analysis is patent pending (US Provisional Application 64/055,566). The AGPL-3.0 license includes an automatic patent grant — open source users are covered.

The optional `matchering` dependency uses [GPLv3](https://github.com/sergree/matchering/blob/master/LICENSE), which is compatible with AGPL-3.0.
