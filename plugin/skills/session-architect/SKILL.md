---
name: session-architect
description: >
  Session setup methodology for Reaper DAW. Guides track hierarchy,
  bus routing, send/receive configuration, sidechain setup, and
  genre-specific session templates. Use this skill whenever the user
  wants to set up a new mixing session, organize tracks into folders
  and buses, create routing for sends and returns, build a session
  from a genre template, configure sidechain compression routing,
  set up color coding and naming conventions, or prepare render
  settings. Also use when the user has a mix brief from
  /phantom:audio-diagnostician and needs to translate diagnostic
  findings into session architecture decisions, or when they ask
  about Reaper-specific track setup, folder structures, or plugin
  routing -- even if they don't say "session setup" explicitly.
---

# Session Architect

> **Where this fits in the workflow:**
> 1. `/phantom:audio-diagnostician` -- analyze stems first
> 2. **You are here: `/phantom:session-architect`** -- set up the session
> 3. `/phantom:mix-engineer` -- mix with measurement-backed decisions
> 4. `/phantom:effects-engineer` -- creative processing
> 5. `/phantom:mastering-engineer` -- final output

## Philosophy

A well-organized session is half the mix. I've seen engineers waste hours hunting for the right track or untangling routing because they skipped the 15-minute setup. A clean session flows -- you make mixing decisions instead of debugging signal path problems. Color every track, name every bus, route every send before you touch a fader.

If `/phantom:audio-diagnostician` produced a mix brief, read it first. The stem count, sample rates, problem stems, and masking conflicts all inform how you structure this session. A session built around the diagnostic findings puts the solutions in your signal path from the start.

## Session Setup Workflow

### Review the mix brief

If audio-diagnostician produced a mix brief, start there. Pull out:
- **Stem count and names** -- determines your track layout
- **Sample rate and bit depth** -- set the project to match
- **Dealbreaker problems** -- stems with phase issues need routing that facilitates polarity flips and time alignment
- **Masking conflicts** -- knowing that kick and bass fight at 60-100 Hz tells you to set up sidechain routing from the start, not discover you need it mid-mix

If there's no mix brief, gather this information manually before building the session.

### Choose a template

Pick the genre template closest to your project from [session-templates.md](session-templates.md) and adapt it. Don't force unconventional projects into a standard template -- start with the closest match and modify. For unusual instrumentation (no drums, orchestral instruments, synth percussion), start from the rock/metal template (the most comprehensive) and strip out what you don't need, rename what doesn't fit.

### Create the track hierarchy

Reaper's folder tracks serve double duty: visual grouping AND audio bus. A track set as a folder automatically sums its children -- put your compressor on the folder track and it's a bus compressor. This is Reaper's superpower and the foundation of every session.

Standard bus architecture (adapt per genre):

```
DRUMS (folder/bus) -- color: red
  Kick In
  Kick Out
  Snare Top
  Snare Bottom
  Hi-Hat
  Toms (1, 2, 3)
  Overhead L, Overhead R
  Room L, Room R

BASS (folder/bus) -- color: blue
  Bass DI
  Bass Amp (if present)

GUITARS (folder/bus) -- color: green
  Rhythm L, Rhythm R
  Lead
  Clean / Acoustic

VOCALS (folder/bus) -- color: yellow
  Lead Vocal
  Harmonies
  Backing Vocals
  Ad-libs

KEYS / SYNTHS (folder/bus) -- color: orange
  Piano, Organ, Synth Pad, Synth Lead

FX RETURNS (folder/bus) -- color: purple
  Room Verb
  Plate Verb
  Slapback Delay
  Long Delay
  Parallel Compression

MIX BUS (master parent)
```

> **Requires a Reaper MCP server.** Automated track creation, folder
> setup, and color assignment need a Reaper MCP server connected.
> See the [setup guide](../../docs/workflows/setup-guide.md) for installation.
> Without it, use this as a reference for manual session setup in Reaper.

### Set up auxiliary channels

**Reverb sends:**
- Room reverb (short, natural) -- primarily for drums
- Plate reverb (medium, vocal-focused) -- vocals, snare, sometimes guitars
- Hall reverb (long, cinematic) -- for special moments, strings, pads

**Delay sends:**
- Slapback delay (50-120 ms, single repeat) -- vocal thickening, rockabilly guitar
- Long delay (quarter note or dotted eighth, 3-5 repeats with feedback) -- vocal phrases, guitar leads

**Parallel compression:**
- Parallel drum bus -- heavy compression (10:1+), blend underneath the dry drum bus
- Parallel vocal bus -- aggressive compression for density, blend at -10 to -6 dB

All send levels start at -inf (negative infinity). Bring up to taste during mixing. Never set sends at 0 dB as a starting point -- that's the maximum, not the default.

### Configure sidechain routing

Sidechain bass to kick is the most common sidechain setup. In Reaper, sidechain signals travel on channels 3-4 (the first pair beyond the main stereo out on channels 1-2).

**How to set up sidechain in Reaper:**
1. On the kick track, add a send to the bass track
2. Set the send to channels 3-4 (not 1-2)
3. On the bass track's compressor (ReaComp), set the sidechain input to channels 3-4
4. The compressor now responds to the kick signal while processing the bass audio

This makes the bass duck briefly when the kick hits -- creating space in the low end without EQ. For frequency-dependent sidechaining, HPF the sidechain input at 80-100 Hz so only the sub frequencies duck (not the kick's attack).

Other common sidechain setups:
- Synth pad sidechained to vocal (gentle ducking for vocal clarity)
- Rhythm guitar sidechained to vocal (duck 1-2 dB during vocal phrases)
- Reverb return sidechained to dry source (ducked reverb for clarity)

### Color coding and naming

Consistency matters more than the specific scheme. Pick colors per instrument group and stick with them across all sessions:

| Group | Color | Why |
|-------|-------|-----|
| Drums | Red | High energy, attention-grabbing -- drums are the foundation |
| Bass | Blue | Cool, low -- visually opposite to drums |
| Guitars | Green | Middle ground, organic |
| Vocals | Yellow | Bright, stands out -- vocals should always be easy to find |
| Keys/Synths | Orange | Warm, between guitars and vocals |
| FX Returns | Purple | Distinct from all instrument groups |

Name tracks descriptively: "Kick In" not "Audio 1", "Lead Vox" not "Track 14". When you come back to a session after a week, the names should tell you exactly what each track is without soloing.

### Reaper MCP Reliability Notes

When building sessions through the Reaper MCP:

- **Always set track names explicitly** with `set_track_name` after `insert_track` — the name parameter on insert is unreliable
- **Verify audio landed on the correct track** after each `insert_audio_file` call — check with `get_track_items`
- **Check FX indices after deletions** — deleting a track shifts all subsequent track indices. Always re-query `get_project_summary` after structural changes
- **iZotope plugins need modules added through their GUI** — Ozone 11 starts empty even when MCP params are set. The user must add modules (EQ, Imager, Dynamics, Maximizer) through Ozone's interface before params take effect
- **Verify param values after setting** — some plugins have internal linking that overrides MCP-set values. Always read back critical params to confirm they held

### Render settings

Set the project sample rate to match the stems (don't let Reaper resample on import). Internal processing: 32-bit float (Reaper's default, leave it).

| Deliverable | Format | Sample Rate | Bit Depth | Notes |
|-------------|--------|-------------|-----------|-------|
| Stems for mixing | WAV | Match project | 32-bit float | Preserves full dynamic range |
| Mix for mastering | WAV | Match project | 24-bit | Standard delivery to mastering |
| Preview / client approval | MP3 | 44.1 kHz | 320 kbps | Lossy but good enough for review |
| Apple Digital Masters | WAV | 96 kHz (if source supports) | 24-bit | Submit highest quality available |

### Gain staging

Before any processing, set all faders to unity (0 dB) and check levels. Aim for -18 dBFS average on each channel -- this gives plugins the headroom they expect (most plugin emulations are calibrated to -18 dBFS = 0 VU). If a stem is significantly hotter or quieter, use the item/clip gain (not the fader) to bring it to the right level.

## Automation Setup

Envelopes are how you make a mix breathe. Set them up during session creation so they're ready when you need them.

**Essential envelope types:**
- Volume -- the most powerful mixing tool. Word-by-word vocal riding, section dynamics
- Pan -- rarely automated, but useful for stereo effects and movement
- Mute -- clean transitions, removing noise between phrases
- Send level -- delay throws (punch send to 0 dB on the last word of a phrase), reverb swells
- FX parameters -- filter sweeps, drive changes, EQ automation

**Automation modes:**
- Trim/Read -- reads existing automation, fader trims on top (default, start here)
- Touch -- writes while you touch the fader, returns to previous value on release
- Latch -- writes while you touch, holds the last value after release
- Write -- overwrites everything, destructive (use sparingly)

## Reaper-Specific Knowledge

For detailed Reaper track, bus, plugin, and routing setup, see [reaper-setup.md](reaper-setup.md).

This covers:
- Folder tracks as buses (dual-purpose architecture)
- 64 internal audio channels and sidechain routing
- Built-in plugin reference (ReaEQ, ReaComp, ReaXcomp, ReaGate, ReaFIR, ReaDelay, ReaVerbate, ReaLimit)
- SWS Extensions and ReaPack
- Render settings for all delivery formats

## Genre Templates

For genre-specific session templates (track layouts, routing conventions, color schemes), see [session-templates.md](session-templates.md).

Available templates:
- Rock/Metal (most comprehensive -- use as starting point for unusual projects)
- Pop
- Hip-Hop/Trap
- Electronic/EDM
- Acoustic/Folk

## Reaper DAW Recipes

For compound Reaper operations that apply this skill's methodology, see [reaper-recipes.md](reaper-recipes.md).

Available recipes:
- **setup_metal_session** -- creates rock/metal session from template
- **setup_pop_session** -- creates pop session from template
- **setup_hiphop_session** -- creates hip-hop/trap session from template
- **setup_electronic_session** -- creates electronic/EDM session from template
- **setup_from_diagnostic** -- adapts template based on diagnostic findings

> Recipes require a Reaper MCP server (TwelveTake recommended).
> See [setup guide](../../docs/workflows/setup-guide.md) for installation.
