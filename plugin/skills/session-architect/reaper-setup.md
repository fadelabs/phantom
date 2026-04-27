# Reaper-Specific Session Setup

> **Requires a Reaper MCP server.** The commands and automation below
> need a Reaper MCP server connected.
> See the [setup guide](../../docs/workflows/setup-guide.md) for installation.
> Without it, use this as a reference for manual session setup in Reaper.

Reaper-specific session setup knowledge. Reference when configuring tracks, buses, plugins, and routing in Reaper.

## Folder Tracks as Buses

Reaper's killer feature: folder tracks are simultaneously visual containers and audio buses. When you set a track as a folder parent, it automatically receives the summed audio of all child tracks. Put an EQ on the folder track and it's a bus EQ. Put a compressor on it and it's bus compression.

This means your visual organization IS your routing. No separate bus creation needed. Collapse a folder to hide the children, expand to see details. The audio routing follows the folder structure automatically.

**Creating a folder track:**
1. Right-click a track > "Set track as folder parent"
2. Child tracks are any tracks below it until the next "end of folder" track
3. Or: drag tracks into position and use the indent buttons in the track control panel

## 64 Internal Audio Channels

Every Reaper track has 64 internal audio channels, not just stereo. This is what makes Reaper's routing so flexible:

- **Channels 1-2**: Main audio (what you hear by default)
- **Channels 3-4**: Sidechain signal (conventional placement)
- **Channels 5-64**: Available for multi-channel routing, stem delivery, surround

**Sidechain routing via channels 3-4:**
1. Source track (e.g., kick): add a send to the destination track (e.g., bass)
2. In the send dialog: set "Audio: source channels 1-2 > destination channels 3-4"
3. On the destination track's compressor: set detector input to "Auxiliary input channels 3-4"
4. The compressor now keys off the kick while processing the bass

**Why channels 3-4?** Convention, not requirement. You could use any pair. But plugins expect sidechain on 3-4, and other engineers opening your session will look there first.

## Built-in Plugin Reference

Reaper ships with excellent stock plugins that handle 80% of mixing tasks. Learn these before reaching for third-party tools -- they're zero-latency, low-CPU, and consistent across systems.

| Plugin | Purpose | Key Parameters | When to Use |
|--------|---------|---------------|-------------|
| **ReaEQ** | Parametric EQ | Bands (unlimited), Freq, Gain, Q, Type (band/shelf/notch/HP/LP) | Every track. Corrective and tonal EQ. Zero-latency, transparent. |
| **ReaComp** | Compressor | Ratio, Attack, Release, Threshold, Knee, Auto makeup, Sidechain input | Individual tracks and buses. Clean VCA-style compression. |
| **ReaXcomp** | Multiband compressor | 3 bands with independent ratio/attack/release/threshold, crossover frequencies | Mastering, problem frequency control, drum bus taming. |
| **ReaGate** | Noise gate | Threshold, Attack, Hold, Release, Hysteresis | Drum gating (toms, kick), noise cleanup between phrases. |
| **ReaFIR** | FFT-based EQ/dynamics | Mode (EQ/Compressor/Gate/Subtract), FFT size | Surgical frequency work, noise profiling and removal, linear-phase EQ alternative. |
| **ReaDelay** | Delay | Time (ms or musical), Feedback, Filter (LP/HP on repeats) | Tempo-synced delays, slapback, feedback effects. |
| **ReaVerbate** | Reverb | Size, Dampening, Width, Dry/Wet | Room simulation, basic spatial processing. Functional but consider third-party for quality-critical vocal reverb. |
| **ReaLimit** | Brickwall limiter | Threshold, Ceiling, Release | Bus limiting, protection limiting, rough mastering. |

**Plugin insertion:** Right-click the FX button on any track > "Add FX" > search by name. Drag to reorder in the chain. Right-click a plugin for bypass, copy chain, save preset.

## SWS Extensions

SWS is the essential free extension pack for Reaper. It adds:

- **Auto-color**: Color tracks by name pattern (all "Kick*" tracks → red)
- **Advanced routing**: Routing matrix view for complex sessions
- **Markers and regions**: Enhanced marker management for session navigation
- **Snapshots**: Save and recall mixer states
- **Cycle actions**: Chain multiple actions into one shortcut

Install via ReaPack (Reaper's package manager) or download from sws-extension.org.

## ReaPack

Reaper's built-in package manager for scripts, plugins, and extensions:
- Extensions > ReaPack > Browse packages
- Thousands of community JSFX plugins (zero-latency, text-based, editable)
- Useful JSFX examples: utility gain, mid-side encoder/decoder, correlation meter, loudness meter

## Render Settings

| Deliverable | Settings |
|-------------|----------|
| **Stems (32-bit float WAV)** | File > Render > Source: Stems (selected tracks) > WAV 32-bit float > Sample rate: match project > Channels: match source |
| **Mix (24-bit WAV)** | File > Render > Source: Master mix > WAV 24-bit PCM > Sample rate: match project |
| **Preview (MP3 320)** | File > Render > Source: Master mix > MP3 > Bitrate: 320 kbps > Sample rate: 44100 |
| **CD master (16-bit WAV)** | File > Render > Source: Master mix > WAV 16-bit PCM > Sample rate: 44100 > Dither: on (add dither plugin before rendering) |
| **Apple Digital Masters** | File > Render > Source: Master mix > WAV 24-bit PCM > Sample rate: 96000 (if source supports) |

**Render tips:**
- Always render from the master bus for final mixes (captures all routing and bus processing)
- For stems, render individual tracks or buses with "Stems" source mode
- Use "Render to project" for printing effects to audio (committing reverb tails, etc.)
- Enable "Normalize/Limit" only for preview renders, never for mastering deliverables
