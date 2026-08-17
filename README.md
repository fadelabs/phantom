# Phantom

> Makes Claude a professional audio engineer.

[Documentation](https://fadelab.net/docs/overview?utm_source=github&utm_medium=readme) · [Getting Started](https://fadelab.net/docs/getting-started?utm_source=github&utm_medium=readme) · [Tool Reference](https://fadelab.net/docs/tools-index?utm_source=github&utm_medium=readme) · [Website](https://fadelab.net?utm_source=github&utm_medium=readme)

[![Star](https://img.shields.io/github/stars/fadelabs/phantom?style=social)](https://github.com/fadelabs/phantom) &nbsp; [![Support](https://img.shields.io/badge/Buy%20me%20a%20coffee-PayPal-blue?logo=paypal)](https://paypal.me/inkbox)

<!-- TODO: Add terminal screenshot of `phantom analyze` output -->

Phantom gives Claude ears. It's an audio engineering system that combines measurement tools, professional mixing and mastering methodology, genre reference profiles, and Reaper DAW integration. Everything works through Claude Code.

Drop in your stems. Claude analyzes every file: spectral balance, loudness, dynamics, stereo width, phase coherence, frequency masking between instruments, and problems like clipping, hum, and noise. Then it makes the same decisions an experienced engineer would. Where to cut, what to compress, how to route, when to send it back for more work.

Without Claude, Phantom is a capable CLI analysis tool. With Claude, it becomes a full mixing and mastering workflow.

## What It Can Do

**Diagnose before you mix.** Load 15 stems, run one command. Phantom catches phase cancellation between kick mics, sample rate mismatches across files, 60 Hz hum on the bass DI, and frequency masking where guitar and vocals fight at 3 kHz. All before you touch a fader.

**Mix against a reference.** A/B your mix against any reference track or genre profile. Get per-dimension deviation: "Your vocal is 2 dB quieter at 2-4 kHz, low end is 3 dB heavy below 100 Hz, stereo width is narrower than the reference." Claude closes the gap with targeted EQ and level adjustments.

**Master for every platform in one pass.** Claude builds the full chain: HPF, corrective EQ, glue compression, tonal shaping, stereo imaging, limiting. Then it renders three masters. Spotify at -14 LUFS, Apple Music at -16 LUFS, and vinyl with mono bass, de-essing, and HF rolloff at 16 kHz. Different loudness targets, different format constraints, same session.

**Solve problems by measurement, not guesswork.** "The mix sounds muddy" becomes "4 dB buildup at 300 Hz across bass, guitar, and keys. Cut bass at 300 Hz by 3 dB, cut guitar at 250-350 Hz by 2 dB." Every recommendation is backed by a number.

**Set up sessions from a template.** Tell Claude the genre and stem count. It builds the folder hierarchy, bus routing, aux sends (reverb, delay, parallel compression), sidechain routing, color coding, and gain staging. Ready to mix.

**Design creative effects.** "I want Tool-style vocal distortion" or "Make the guitars sound like shoegaze." Claude builds the chain: saturation type, drive amount, chain order, parallel blend level. All calibrated by measurement.

## How It Works

Four layers that work together:

1. **Measurement.** 20 MCP tools that quantify your audio: spectrum, loudness (EBU R128), dynamics, stereo field, phase coherence, frequency masking between stems, and problems like clipping, hum, DC offset, sibilance, and room resonances. Plus automated problem fixing and custom processing chains.

2. **Methodology.** Five domain expert skills that encode how professional engineers actually think. Structured decision-making workflows: when to use FET vs VCA compression, how to read crest factor to choose a handling strategy, when a mix needs more work vs when it's ready for mastering.

3. **Reference.** Nine genre profiles with target loudness, spectral balance, dynamics conventions, and stereo width standards. Your mix gets compared against professional benchmarks for your genre.

4. **Execution.** Reaper DAW integration via MCP. Claude inserts EQ, sets compression ratios, builds sidechain routing, writes automation, and renders deliverables.

## Try It

No install needed. Run this on any audio file:

```bash
uvx --from phantom-audio phantom analyze your-track.wav
```

The distribution is `phantom-audio`; the command it installs is `phantom`. `uvx` assumes those
match, so `--from` is required here.

Or install it:

```bash
curl -sSL https://fadelab.net/install | bash
```

The installer handles everything — installs uv and Python if needed, lets you choose which extras to install, and configures the MCP server, Claude Code plugin, and Reaper bridge.

> **Windows is not supported yet.** `phantom-audio` cannot currently be installed on Windows. Its analysis engine, [essentia](https://essentia.upf.edu/), publishes no Windows package, so the install fails while resolving dependencies. Work to replace that engine with a Windows-capable one is tracked in [#52](https://github.com/fadelabs/phantom/issues/52). Until then, run Phantom on macOS, on Linux, or under [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).

Point it at any WAV file:
```bash
phantom analyze your-track.wav
```

To use with Claude, add to your MCP config (`.mcp.json`):

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

Install the Claude Code plugin for domain expert skills:

```bash
claude plugin install phantom/plugin
```

Then talk to Claude:

> "Analyze my stems and tell me what needs fixing before I start mixing."

> "Compare my master against this reference track and show me what's off."

> "Set up a mixing session for a 5-stem rock track with parallel drum compression."

> "Is this mix ready for mastering, or does it need more work?"

## Analysis Tools

| Category | Tools | What They Measure |
|----------|-------|-------------------|
| Spectral | `analyze_spectrum` | Frequency balance, centroid, rolloff, contrast, flatness, dissonance |
| Loudness | `analyze_loudness` | Integrated LUFS, momentary, short-term, loudness range (EBU R128), true peak |
| Dynamics | `analyze_dynamics` | RMS, peak, crest factor, dynamic range, dynamic complexity |
| Stereo | `analyze_stereo` | Width, balance, mid/side ratio, correlation, panorama distribution |
| Phase | `analyze_phase`, `compare_phase` | Phase coherence per band, polarity, inter-channel delay |
| Problems | `detect_problems` | Clipping, DC offset, inter-sample peaks, noise floor, SNR, hum, sibilance, mud, harshness, resonances, lossy-codec artifacts |
| Masking | `analyze_masking`, `multi_stem_masking` | Per-octave frequency overlap between stems, collision severity ranking |
| Comparison | `compare_to_profile`, `compare_to_reference` | Deviation from genre targets or reference tracks across all dimensions |
| Matching | `match_to_reference` | Automated spectral/loudness/width matching to a reference WAV |
| Separation | `separate_stems` | Isolate vocals, drums, bass, and instruments via Demucs |
| Fixing | `fix_audio` | Automatically fix detected problems (DC offset, clipping, hum, etc.) |
| Processing | `apply_processing` | Apply a custom chain of audio processing operations |
| Profiles | `list_profiles`, `load_profile` | Browse and inspect genre reference profiles |
| Diagnostic | `full_diagnostic`, `batch_diagnostic` | All analysis types on one file, or across up to 50 files in a single call |

## Domain Expert Skills

**Audio Diagnostician.** Runs batch diagnostics on all stems, triages problems by severity (dealbreaker, significant, moderate, minor), maps frequency masking between every stem pair, and produces a structured mix brief. Catches phase cancellation and sample rate mismatches before you waste time mixing.

**Mix Engineer.** Phase-first troubleshooting, gain staging methodology, complementary EQ decisions (boost one stem where you cut its competitor), compressor type selection (FET for punch, Opto for smooth, VCA for transparent, Vari-Mu for glue), sidechain routing, parallel compression, serial compression, spatial processing with reverb type selection, and automation strategy.

**Effects Engineer.** Distortion and saturation taxonomy (tube warmth vs transistor grit vs tape compression), modulation effects, reverb and delay type selection with pre-delay guidance, creative chain recipes (ethereal vocals, massive guitars, Tool-style distortion, lo-fi textures), and effects automation for dynamic transitions.

**Mastering Engineer.** Ten-stage mastering chain in strict order (HPF through dither), send-back criteria (when a mix needs more work, not mastering), platform-specific loudness targeting (Spotify, Apple Music, YouTube, CD, vinyl), reference-based mastering workflow, and format delivery requirements including metadata.

**Session Architect.** Genre-specific session templates, folder/bus hierarchy design, aux channel setup (reverb sends, delay sends, parallel compression), sidechain routing, color coding conventions, automation mode guidance, and render settings per deliverable format.

## Reference Profiles

| Profile | Target LUFS | Character |
|---------|-------------|-----------|
| Pop | -10 to -7 | Polished, vocal-forward, controlled dynamics, 4 kHz presence boost |
| Rock | -12 to -8 | Wide stereo, prominent guitars, punchy drums |
| Hip-Hop | -10 to -7 | Heavy low end, crisp highs, compressed dynamics |
| Electronic | -10 to -7 | Wide stereo, sub-bass emphasis, bright top end |
| EDM | -8 to -5 | Loud, sidechain pumping, wide and bright |
| Metal | -10 to -6 | Dense, scooped mids, aggressive compression |
| Rock-Metal | -10 to -7 | Heavy, mid-present, tight low end |
| Lo-Fi | -14 to -10 | Warm, rolled-off highs, narrow stereo, intentionally quiet |
| Ambient | -20 to -14 | Wide, dynamic, gentle spectral curve |

## Installation

**Core** (analysis + MCP server + CLI):

```bash
uv tool install phantom-audio --python 3.13
```

> **Python 3.13 required.** Essentia (the analysis engine) doesn't support Python 3.14+ yet. The `--python 3.13` flag tells uv to use the right version automatically.
>
> Don't have `uv`? Install it with `curl -LsSf https://astral.sh/uv/install.sh | sh` or `brew install uv`.

Setup runs automatically on first use. To re-run manually: `phantom setup`

**With all extras** (recommended — install everything upfront so stem separation and reference matching are available immediately):

```bash
uv tool install "phantom-audio[all]" --python 3.13
```

> **Why install extras upfront?** `uv tool install` creates an isolated Python environment. If you install extras later, you'll need to reinstall with `--force` to add them to the same environment. Installing everything at once avoids this. Stem separation (Demucs) adds ~2.5GB for PyTorch.

**Or pick only what you need:**

```bash
# Stem separation only (Demucs + PyTorch ~2.5GB)
# Ships as the sibling package phantom-audio-separation; the [separation]
# extra is a backward-compatible meta-installer that pulls it in.
uv tool install "phantom-audio[separation]" --python 3.13

# Reference matching only (GPLv3 -- see License section)
uv tool install "phantom-audio[matching]" --python 3.13

# Audio processing / auto-fix (Pedalboard)
uv tool install "phantom-audio[processing]" --python 3.13
```

**Using uv** (recommended):

```bash
uv add phantom-audio
```

**Development:**

```bash
git clone https://github.com/fadelabs/phantom.git
cd phantom
uv sync --extra dev
```

## Telemetry

Both installers (`install.sh` and `install.ps1`) report anonymized install telemetry to `fadelab.net` at the start, completion, and failure of an install. Each report is a small JSON payload carrying the OS, architecture, phantom version (when known), the chosen extras, and the install method (currently always `uv`), plus a per-run install ID used to join the start and completion events of a single install. A failure report also includes one of six fixed reason codes (`unsupported_os`, `unsupported_arch`, `no_downloader`, `uv_install_failed`, `pkg_install_failed`, `not_on_path`) — never raw error text or log contents. No audio, file names, or other personal data is sent, and the request has no effect on the install.

Two of those codes are specific to `install.sh`: the Windows installer rejects no architecture (`unsupported_arch`) and needs no external downloader (`no_downloader`).

Telemetry is on by default. Opt out by setting the flag on the shell that runs the script:

```bash
# macOS / Linux
curl -sSL https://fadelab.net/install | PHANTOM_NO_TELEMETRY=1 bash
```

The variable has to go on `bash`, not on `curl`. `PHANTOM_NO_TELEMETRY=1 curl ... | bash` exports it
to the download process only, and the installer never sees it.

```powershell
# Windows (install.ps1 honors the same variable, but see the Windows note above —
# the install cannot currently succeed on Windows)
$env:PHANTOM_NO_TELEMETRY = "1"
irm https://raw.githubusercontent.com/fadelabs/phantom/main/install.ps1 | iex
```

## Usage

### With Claude Code (Recommended)

Add the MCP server to your project's `.mcp.json`, install the plugin, and talk to Claude. The tools handle measurement, the skills handle interpretation, and a Reaper MCP server handles applying changes in your DAW.

Example prompts:

- *"Analyze this vocal take and tell me if it needs de-essing."*
- *"Check all my stems for phase issues and frequency masking."*
- *"Compare my master to a pop reference. What's off?"*
- *"Set up a mixing session for a 5-stem rock track."*
- *"I want ethereal reverb on the vocals. Build the chain."*
- *"Is this loud enough for Spotify, or do I need more limiting?"*

### Standalone CLI

Works without AI:

```bash
phantom analyze track.wav              # Full analysis with Rich terminal output
phantom analyze track.wav --json       # Machine-readable JSON
phantom compare track.wav --profile rock  # Compare against genre targets
phantom compare track.wav --reference ref.wav  # A/B against a reference
phantom separate mix.wav --output ./stems/     # Stem separation
phantom fix track.wav                  # Auto-fix detected problems
phantom render mix.wav --reference ref.wav     # Match to reference
phantom doctor                         # Check installation health
phantom serve                          # Start the MCP server
```

### As an MCP Server

Works with any MCP-compatible client. Claude Code, Cursor, Windsurf, or anything that speaks MCP:

```bash
phantom-mcp
```

Connect via stdio transport.

## DAW Integration

Pair Phantom with a Reaper MCP server for full DAW control. Two servers running simultaneously: Phantom handles measurement, Reaper MCP handles tracks, plugins, routing, and automation.

The workflow:

1. **Analyze.** Phantom measures your audio (spectrum, loudness, dynamics, problems, masking)
2. **Decide.** Skills interpret the measurements and choose processing
3. **Execute.** Reaper MCP applies changes in your DAW (EQ, compression, reverb, levels, sidechain routing, automation)

Set up Reaper integration:

```bash
phantom setup-reaper
```

This auto-detects your Reaper installation, clones the bridge, copies the Lua scripts, configures auto-start, and writes MCP config. No prompts. If Reaper is installed, it just works. If Reaper isn't installed, it silently skips. The bridge auto-starts every time you open Reaper.

The Reaper MCP server includes batch tools built for mixing workflows:

| Tool | What It Does |
|------|-------------|
| `batch_set_fx_params` | Set multiple plugin parameters in one call |
| `copy_fx_chain` | Clone all FX from one track to another |
| `batch_create_tracks` | Create multiple named, colored tracks at once |
| `set_fx_params_by_name` | Set parameters by name ("Threshold", "Ratio") instead of index |
| `create_submix` | Create a bus with routing and optional EQ/compression |
| `batch_apply_eq` | Apply identical EQ settings across multiple tracks |
| `configure_multiband_compressor` | Set ReaXcomp band parameters by discovery |
| `setup_sidechain_with_filter` | Sidechain compression with HPF on the sidechain signal |
| `set_fx_preset_batch` | Apply the same preset across multiple tracks |
| `add_pan_automation` | Pan automation with named positions ("center", "hard left") |

These sit on top of 100+ individual tools for tracks, FX, MIDI, routing, markers, envelopes, transport, and rendering.

## Known Limitations

**iZotope Neutron and Ozone module exposure.** Neutron and Ozone use an internal module system where each processing module (EQ, Compressor, Exciter, etc.) must be manually added to the plugin's signal chain before its parameters become visible to external automation. This means Phantom and Reaper MCP cannot see or control a module until you've added it inside the plugin GUI. This is a limitation of how iZotope exposes VST parameters, not a Phantom issue. Once modules are added, their parameters are fully controllable.

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
