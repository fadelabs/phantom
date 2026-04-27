---
name: mastering-engineer
description: >
  Professional mastering methodology for audio engineering. Covers the
  complete mastering chain (HPF through dither), corrective vs
  enhancement mastering, when to send a mix back, loudness targeting
  per platform, iZotope Ozone 11 workflow, and reference-based
  mastering. Use this skill whenever the user wants to master a mix,
  prepare audio for distribution, target a specific loudness standard,
  compare against a reference track, decide whether a mix needs more
  work or is ready for mastering, deliver for streaming (Spotify,
  Apple Music, YouTube), CD, or vinyl, or make any mastering decision.
  Also use when the user asks about LUFS, true peak, limiting,
  dithering, loudness normalization, or format-specific delivery
  requirements -- even if they don't say "mastering" explicitly.
---

# Mastering Engineer

> **Where this fits in the workflow:**
> 1. `/phantom:audio-diagnostician` -- analyze stems first
> 2. `/phantom:session-architect` -- set up the DAW session
> 3. `/phantom:mix-engineer` -- mix with measurement-backed decisions
> 4. `/phantom:effects-engineer` -- creative processing
> 5. **You are here: `/phantom:mastering-engineer`** -- the final stage

## Philosophy

Don't fix it if it isn't broken. The best mastering enhances what's already good -- it doesn't rescue a bad mix. If you're reaching for 4 dB of EQ, the mix needs work, not mastering. Know when to send it back.

Mastering is the last creative decision and the first technical one. You're simultaneously making the music sound its best AND ensuring it meets the technical requirements of every delivery platform. Both matter.

## When to Send a Mix Back vs Work With It

Run `detect_problems` and `analyze_loudness` on the mix first. Measurement, not opinion, drives this decision.

### Send it back

- More than 4 dB of corrective EQ needed anywhere -- that's a mix problem
- Fundamental balance issues (vocals buried, bass overwhelming, drums too loud/quiet)
- Severe phase problems (correlation < +0.3 on the mix bus)
- Baked-in clipping or distortion (true peak > 0 dBTP that can't be undone)
- Excessive noise floor that should have been addressed at the stem level

### Work with it

- Correctable tonal imbalances (< 2-3 dB of EQ)
- Gentle dynamic reshaping (broadband compression, mild limiting)
- Slight stereo adjustments (mono bass, subtle widening)
- Format-specific optimization (loudness targeting, dither for CD)

Deliver this assessment honestly. "Your mix needs a 6 dB cut at 300 Hz -- I can do 2-3 dB in mastering, but the rest needs to happen in the mix" is more helpful than silently trying to fix it.

## Corrective vs Enhancement Mastering

**Corrective first, enhancement second.** Never enhance before correcting -- you'll be polishing problems.

**Corrective mastering:** fixing what the mix engineer missed or couldn't solve. Tonal imbalances, excessive dynamics, phase issues, noise. This is surgical, necessary work.

**Enhancement mastering:** elevating what's already good. Adding air, optimizing loudness for the target platform, subtle widening, warmth. This is the creative, satisfying part.

## The Complete Mastering Chain

Nine stages in strict order. Each stage feeds the next -- skipping or reordering changes the result.

### 1. High-Pass Filter

Remove sub-bass rumble below 20-30 Hz. This content is inaudible but wastes headroom and causes the limiter to react to energy you can't hear. A gentle HPF here gives you 1-2 dB of free headroom.

### 2. Corrective / Subtractive EQ

Linear-phase EQ for surgical cuts. Fix problems identified by `analyze_spectrum` -- resonances, tonal imbalances, mud. Narrow Q for problem frequencies, wider Q for broad tonal issues.

Run `analyze_spectrum` first. If the spectral centroid is unusually low (dark/muddy mix), you'll need a broad tilt or shelf. If there are narrow peaks, surgical notch cuts.

### 3. Broadband Compression

Glue, not squash. 1.5:1-3:1 ratio, 30-100 ms attack, auto or 200-300 ms release. Target 1-3 dB of gain reduction. If you're hitting more than 3 dB, the mix needs more compression in the mix stage, not the master.

VCA or Vari-Mu character. VCA for transparency, Vari-Mu for warmth and glue.

### 4. Dynamic EQ / Multiband Compression

Frequency-specific control for problems that broadband compression can't solve. A bass note that rings too loud on certain hits. A harshness at 3 kHz that only appears in the chorus. Multiband lets you control one frequency range without affecting the others.

Use dynamic EQ over multiband compression when the problem is intermittent -- dynamic EQ only engages when the threshold is exceeded, leaving the signal untouched the rest of the time.

### 5. Tonal / Additive EQ

Shape the final tone. This is the enhancement stage -- air (gentle shelf above 10 kHz), warmth (subtle 100-200 Hz), presence (2-4 kHz). Wide Q, gentle boosts. If you're boosting more than 2 dB, reconsider whether this should have been a corrective cut elsewhere.

### 6. Stereo Imaging

Make bass mono below 80-150 Hz. Low-end stereo content causes problems on every playback system -- vinyl needles skip, club subs cancel, headphones create an unstable image. Mono the sub.

Optional: gentle high-end widening above 8 kHz for air and spaciousness. Check with `analyze_stereo` -- correlation should stay above +0.3 after widening.

### 7. Saturation / Exciter

Optional warmth before the limiter. Add character before the limiter flattens it. Tube saturation for warmth, tape for glue. Light touch -- this is mastering, not mixing.

### 8. Limiting / Maximizer

True peak ceiling at -1 dBTP (never 0 -- inter-sample peaks can exceed 0 dBTP even when the meter shows -0.1). Set the ceiling, then bring the threshold down until you reach your loudness target.

Run `analyze_loudness` after limiting to verify integrated LUFS and true peak meet your platform target.

For platform-specific loudness targets, see [format-targets.md](format-targets.md).

### 9. Dither

Only when reducing bit depth (24-bit to 16-bit for CD). Always the absolute last stage in the chain -- nothing after dither. TPDF for transparency, MBIT+ noise shaping for perceptually optimized dither (pushes dither noise into frequencies where hearing is least sensitive).

Never dither twice. Never dither when staying at the same bit depth. Never dither when going up in bit depth.

## Loudness Targeting

Run `analyze_loudness` to check integrated LUFS and true peak. Run `compare_to_profile` for genre-appropriate targets. Run `compare_to_reference` for A/B against a reference track.

**Level-match before A/B comparison.** Louder always sounds better -- remove the bias. Match the integrated LUFS of your master to the reference before comparing.

**Match direction not destination.** The reference is a compass, not GPS. If the reference has more high-end sparkle, add some sparkle -- but don't try to make your track sound identical.

**Different references for different aspects.** One reference for low-end balance, another for vocal clarity, another for overall loudness. No single reference is perfect in every dimension.

For platform-specific loudness and format specs, see [format-targets.md](format-targets.md).

## Reference-Based Mastering

Use `match_to_reference` for automated spectral/loudness/width matching if Matchering is installed. This gives you a starting point -- then adjust by ear. Apply the automated match at 50-70% strength, not 100%.

Use `compare_to_reference` to see per-dimension deviations between your master and the reference. This shows you exactly where your master differs -- spectrum, loudness, dynamics, stereo width -- so you can make targeted corrections.

## Plugin Workflow

### iZotope Ozone 11

For module-by-module Ozone 11 guidance (Equalizer, Dynamic EQ, Dynamics, Maximizer, Imager, Master Assistant, Match EQ, Exciter, Vintage modules, Codec Preview, Stem Focus), see [ozone-guide.md](ozone-guide.md).

### Reaper Built-in Chain

> **Requires a Reaper MCP server** for automated plugin insertion.
> See the [setup guide](../../docs/workflows/setup-guide.md) for installation.

The Reaper stock plugins handle 80% of mastering tasks:
- **ReaEQ** -- corrective + tonal EQ (stages 2 and 5)
- **ReaComp** -- broadband compression (stage 3)
- **ReaXcomp** -- multiband compression (stage 4)
- **ReaFIR** -- linear-phase EQ alternative (stage 2)
- **ReaLimit** -- brickwall limiter (stage 8)

## Reference Materials

- For iZotope Ozone 11 module-by-module guidance, see [ozone-guide.md](ozone-guide.md)
- For platform-specific delivery requirements, see [format-targets.md](format-targets.md)

## Reaper DAW Recipes

For compound Reaper operations that apply this skill's methodology, see [reaper-recipes.md](reaper-recipes.md).

Available recipes:
- **mastering_chain_streaming** -- streaming-optimized mastering chain (Spotify -14 LUFS, Apple Music -16 LUFS)
- **mastering_chain_vinyl** -- vinyl-optimized mastering chain (physical media constraints)

> Recipes require a Reaper MCP server (TwelveTake recommended).
> See [setup guide](../../docs/workflows/setup-guide.md) for installation.
