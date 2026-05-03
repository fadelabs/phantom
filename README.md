# Phantom

> Makes Claude a professional audio engineer.

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

1. **Measurement.** 17 MCP tools that quantify your audio: spectrum, loudness (EBU R128), dynamics, stereo field, phase coherence, frequency masking between stems, and problems like clipping, hum, DC offset, sibilance, and room resonances.

2. **Methodology.** Five domain expert skills that encode how professional engineers actually think. Structured decision-making workflows: when to use FET vs VCA compression, how to read crest factor to choose a handling strategy, when a mix needs more work vs when it's ready for mastering.

3. **Reference.** Nine genre profiles with target loudness, spectral balance, dynamics conventions, and stereo width standards. Your mix gets compared against professional benchmarks for your genre.

4. **Execution.** Reaper DAW integration via MCP. Claude inserts EQ, sets compression ratios, builds sidechain routing, writes automation, and renders deliverables.

## Try It

No install needed. Run this on any audio file:

```bash
uvx phantom-audio analyze your-track.wav
```

Or install it:

```bash
curl -sSL https://raw.githubusercontent.com/fadelabs/phantom/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/fadelabs/phantom/main/install.ps1 | iex
```

The installer handles everything — installs uv and Python if needed, lets you choose which extras to install, and configures the MCP server, Claude Code plugin, and Reaper bridge.

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
| Problems | `detect_problems` | Clipping, DC offset, inter-sample peaks, hum, sibilance, mud, harshness, resonances |
| Masking | `analyze_masking`, `multi_stem_masking` | Per-octave frequency overlap between stems, collision severity ranking |
| Comparison | `compare_to_profile`, `compare_to_reference` | Deviation from genre targets or reference tracks across all dimensions |
| Matching | `match_to_reference` | Automated spectral/loudness/width matching to a reference WAV |
| Separation | `separate_stems` | Isolate vocals, drums, bass, and instruments via Demucs |
| Diagnostic | `full_diagnostic`, `batch_diagnostic` | All analysis types on one file or up to 50 files in parallel |

## Domain Expert Skills

**Audio Diagnostician.** Runs batch diagnostics on all stems, triages problems by severity (dealbreaker, significant, moderate, minor), maps frequency masking between every stem pair, and produces a structured mix brief. Catches phase cancellation and sample rate mismatches before you waste time mixing.

**Mix Engineer.** Phase-first troubleshooting, gain staging methodology, complementary EQ decisions (boost one stem where you cut its competitor), compressor type selection (FET for punch, Opto for smooth, VCA for transparent, Vari-Mu for glue), sidechain routing, parallel compression, serial compression, spatial processing with reverb type selection, and automation strategy.

**Effects Engineer.** Distortion and saturation taxonomy (tube warmth vs transistor grit vs tape compression), modulation effects, reverb and delay type selection with pre-delay guidance, creative chain recipes (ethereal vocals, massive guitars, Tool-style distortion, lo-fi textures), and effects automation for dynamic transitions.

**Mastering Engineer.** Nine-stage mastering chain in strict order (HPF through dither), send-back criteria (when a mix needs more work, not mastering), platform-specific loudness targeting (Spotify, Apple Music, YouTube, CD, vinyl), reference-based mastering workflow, and format delivery requirements including metadata.

**Session Architect.** Genre-specific session templates, folder/bus hierarchy design, aux channel setup (reverb sends, delay sends, parallel compression), sidechain routing, color coding conventions, automation mode guidance, and render settings per deliverable format.

## Reference Profiles

| Profile | Target LUFS | Character |
|---------|-------------|-----------|
| Pop | -10 to -7 | Polished, vocal-forward, controlled dynamics, 4 kHz presence boost |
| Rock | -10 to -8 | Wide stereo, prominent guitars, punchy drums |
| Hip-Hop | -10 to -6 | Heavy low end, crisp highs, compressed dynamics |
| Electronic | -9 to -6 | Wide stereo, sub-bass emphasis, bright top end |
| EDM | -8 to -5 | Loud, sidechain pumping, wide and bright |
| Metal | -8 to -5 | Dense, scooped mids, aggressive compression |
| Rock-Metal | -9 to -6 | Heavy, mid-present, tight low end |
| Lo-Fi | -16 to -12 | Warm, rolled-off highs, narrow stereo, intentionally quiet |
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
uv tool install "phantom-audio[separation]" --python 3.13

# Reference matching only (GPLv3 -- see License section)
uv tool install "phantom-audio[matching]" --python 3.13
```

**Using uv** (recommended):

```bash
uv add phantom-audio
```

**Development:**

```bash
git clone https://github.com/fadelabs/phantom.git
cd phantom
uv sync --dev
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

Environment variables for security and resource limits:

| Variable | Default | Description |
|----------|---------|-------------|
| `PHANTOM_AUDIO_DIR` | *(none)* | Restrict file access to this directory tree |
| `PHANTOM_OUTPUT_DIR` | *(none)* | Restrict output file paths |
| `PHANTOM_MAX_DURATION` | 900 (15 min) | Maximum audio duration in seconds |
| `PHANTOM_MAX_FILE_SIZE` | 524288000 (500 MB) | Maximum file size in bytes |
| `PHANTOM_PROFILES_DIR` | *(built-in)* | Custom reference profile directory |

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

**Want to use Phantom in a proprietary product?** Commercial licensing is available. Contact hello@leesae.nz.

**Patent Notice:** Phantom's weighted frequency masking analysis is patent pending (US Provisional Application 64/055,566). The AGPL-3.0 license includes an automatic patent grant — open source users are covered.

The optional `matchering` dependency uses [GPLv3](https://github.com/sergree/matchering/blob/master/LICENSE), which is compatible with AGPL-3.0.
