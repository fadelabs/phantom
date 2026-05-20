# iZotope Ozone 11 Module-by-Module Mastering Guide

Reference when using Ozone for mastering. Each module's purpose, key parameters, modes, and when to reach for it. Modules listed in recommended chain order.

## Core Modules

### Equalizer

8-band parametric EQ with three modes:
- **Analog mode**: adds subtle saturation on boosts -- musical, warm. Use for tonal/additive EQ (stage 5).
- **Digital mode**: transparent, surgical. Use for corrective/subtractive EQ (stage 2).
- **Matching mode**: captures a reference spectrum and applies it. See Match EQ below for the advanced version.

Mid/Side processing available per band. Tighten low-end on the mid channel, add air on the side channel.

### Dynamic EQ

Frequency-specific compression or expansion. Each node has its own threshold -- only engages when the problem frequency exceeds it.

Better than multiband compression when the problem is intermittent. A resonance that only appears on certain notes, harshness in the chorus but not the verse. Dynamic EQ leaves the signal untouched when there's no problem.

### Dynamics (Multiband Compressor)

4 bands with independent ratio, attack, release, threshold per band.

Use for controlling low-end rumble without affecting mids, taming harsh 2-4 kHz without dulling the mix, or evening out the low-mid energy that builds up in dense arrangements.

Crossover frequencies are critical -- place them between instruments' frequency ranges, not through them (cutting a kick's fundamental in half between two bands creates artifacts).

### Maximizer

The limiter/loudness stage. The most critical module in mastering.

**IRC modes:**
| Mode | Character | Best For |
|------|-----------|----------|
| **IRC I** | Clean, transparent, minimal coloration | Acoustic, jazz, classical -- where transparency matters most |
| **IRC II** | Balanced, moderate transient preservation | General-purpose workhorse. Default starting point. |
| **IRC III** | Aggressive, audible pumping, more loudness | Rock, metal, EDM -- genres that tolerate or embrace limiting artifacts |
| **IRC IV** | Modern, loudest, optimized for competitive loudness | EDM, pop, hip-hop -- maximum loudness with best artifact management |

Each IRC mode has character variants within it (different transient handling algorithms). Experiment within the mode.

**Settings:**
- **Threshold**: bring down until you hit your LUFS target. The ceiling stays fixed.
- **Ceiling**: set to -1.0 dBTP. Always. Never 0 -- inter-sample peaks will exceed the ceiling.
- **True Peak limiting**: enable. This catches ISPs that sample-peak meters miss.

### Imager

Per-band stereo width control with 4 bands.

- **Width slider per band**: 0% = mono, 100% = original, >100% = widened
- **Stereoize**: adds width to mono sources (use cautiously -- introduces phase artifacts)
- **Mono below control**: make everything below a set frequency mono

**Standard settings:** Mono below 80-150 Hz. Leave midrange at 100%. Optional gentle widening on the highest band (above 8 kHz) for air. Never widen bass -- it destroys low-end focus.

### Master Assistant

AI-powered starting point. Feed it 8+ seconds of the loudest section. Genre-aware targeting.

Use as a starting point, then adjust by ear. It gets you 70% of the way -- the last 30% is your taste and the specific requirements of this track. Don't treat its output as final.

### Match EQ

8000+ band linear-phase EQ that captures a reference track's spectral curve and applies it to your master.

**Workflow:**
1. Load or capture a reference track
2. Match EQ captures the reference spectrum
3. Apply to your master at 50-70% strength (100% sounds like the reference, not your track)
4. Adjust the smoothing control (higher = gentler, broader corrections; lower = more precise matching)
5. Constrain the frequency range if needed (e.g., only match 200 Hz-8 kHz, leaving the extremes alone)

## Secondary Modules

### Exciter

Harmonic exciter with per-band control and multiple modes (tube, tape, transistor, warm). Add sparkle to highs or warmth to lows without EQ boosting -- harmonics add perceived brightness/warmth without increasing the fundamental energy.

### Vintage Limiter

Analog-modeled limiting with Tube and Solid-State modes. Warmer, more colored limiting than Maximizer. Use when you want vintage character on the limiting stage instead of transparency.

### Vintage Tape

Tape saturation emulation. Speed (7.5/15/30 IPS), bias, emphasis controls. Adds warmth and glue before the Maximizer. 15 IPS for balanced frequency response, 30 IPS for extended low-end and highs.

### Vintage EQ

Pultec-style EQ with broad, musical curves. A classic Pultec-style move: boost AND cut at the same low frequency creates a resonant shelf that adds weight and tightness simultaneously.

### Vintage Compressor

Opto, FET, and Tube models. For character compression -- use the Dynamics module when you need transparent, precise control. Use Vintage Compressor when you want the coloration to be part of the sound.

### Codec Preview

AAC and MP3 quality preview at various bit rates. Always preview at the delivery codec before final bounce. Catch codec artifacts (pre-echo, spectral smearing, transient softening) before they reach the listener.

### Stem Focus

AI source separation for targeted mastering. Process vocals, drums, or bass separately within the stereo master -- useful when you can't get stems. Focus on vocals to de-ess the master, focus on drums to add punch, focus on bass to tighten the low end.

Powerful but imperfect -- AI separation introduces artifacts. Use for subtle corrections, not dramatic changes.

## Workflow Notes

- Module order in the chain should match the 9-stage mastering chain from SKILL.md
- Bypass individual modules to A/B their contribution
- Use Ozone's metering panel: integrated LUFS, short-term, true peak, dynamic range
- A/B the entire chain: bypass everything to compare processed vs unprocessed (level-matched)

## Neutron 4 for Stem Mastering

When you have individual stems instead of a stereo mix:

- **Sculptor**: AI tonal shaping per instrument type -- select the instrument, Sculptor applies genre-aware EQ
- **Unmask**: automated masking detection between tracks, applies complementary EQ to reduce frequency conflicts
- **Compressor Punch Mode**: intent-based dynamics -- "more punch," "more sustain" instead of ratio/attack/release
- **Stem mastering workflow**: process individual stems with Neutron, sum to a bus, master the bus with Ozone

## MCP Parameter Reference

When controlling Ozone 11 through the Reaper MCP, param indices shift depending on which modules are loaded. Always re-scan param names after adding/removing modules through the Ozone GUI.

### Typical param index ranges (with EQ + Imager + Dynamics + Maximizer loaded):
- **EQ**: params 0-50 (frequencies 2-9, gains 10-17, Q 18-25, enable 34-41, shape 42-49)
- **Imager**: params 101-119 (width per band 105-108, stereoizer enable 103)
- **Maximizer**: params 118-133 (bypass 118/120, input gain 121, output level 122, character 124)
- **Gain I/O**: params 131-136

### Known MCP issues with Ozone 11:
- **Modules must be added through Ozone's GUI** — setting params via MCP on an empty Ozone instance does nothing visible. The user must click "+" and add modules first.
- **Maximizer ceiling (output level) resets** — the link between input gain and output level (param 121/123) overrides ceiling changes made via MCP. Unlink first (set link param to 0), then set ceiling. Even then, it may reset. Fall back to having the user set ceiling in the GUI.
- **EQ bands default to disabled** — always set the Enable param (34-41) to 1.0 before setting frequency/gain/Q on a band.
- **Param indices shift** — if the user adds or removes modules in Ozone, all param indices after that module change. Always re-discover params with `track_fx_get_param_name` after any module change.

### Radio-ready mastering targets (rock-metal):
| Parameter | Target |
|-----------|--------|
| Integrated LUFS | -10 to -7 |
| True peak | -1.0 dBTP |
| Crest factor | 5-9 dB |
| Stereo width | 0.3-0.7 |
| Bass mono below | 120 Hz |

### Maximizer settings for radio loudness:
- **Ceiling**: -1.0 dB (non-negotiable)
- **Input gain**: push until 6-8 dB gain reduction on loud sections
- **Character/IRC**: IRC III or "Fast and Loud" for rock-metal
- **True Peak limiting**: always enabled
- **Learn Input Gain**: click to auto-target a LUFS value (useful starting point)

### Imager settings for rock-metal:
- Band 1 (lows): 30% width — narrow for tight low end
- Band 2 (low-mids): 50-60% — moderate width
- Band 3 (high-mids): 60-65% — wider for guitar spread
- Band 4 (highs): 50-55% — moderate width, avoid excessive air widening
- Stereoizer: enable for mono source material
