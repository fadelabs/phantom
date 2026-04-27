---
name: audio-diagnostician
description: >
  Pre-mix audio analysis and problem detection for audio engineering.
  Runs Phantom MCP diagnostic tools on stems, catalogs issues by
  severity (dealbreaker/significant/moderate/minor), identifies
  frequency masking between stems, and produces a structured mix brief.
  Use this skill whenever the user wants to analyze audio stems or files
  before mixing, diagnose audio problems (phase issues, clipping, noise,
  hum, mud, harshness), assess recording quality, prepare a mix session
  overview, check if a mix is ready for mastering, or investigate why
  something "sounds wrong." Also use when the user provides WAV file
  paths and asks for analysis, quality checks, or problem identification
  -- even if they don't explicitly mention "diagnostics."
---

# Audio Diagnostician

> **Where this fits in the workflow:**
> 1. **You are here: `/phantom:audio-diagnostician`** -- analyze first, always
> 2. `/phantom:session-architect` -- set up the DAW session
> 3. `/phantom:mix-engineer` -- mix with measurement-backed decisions
> 4. `/phantom:effects-engineer` -- creative processing
> 5. `/phantom:mastering-engineer` -- final output

## Philosophy

I've caught polarity issues that would have destroyed an entire mix -- two mics on a snare, one flipped, and the engineer spent three hours trying to EQ body back into the drum before anyone thought to check phase. The 10 minutes you spend on diagnostics saves hours of frustration later.

Never touch a fader before you understand what you're working with. Every stem has a story: its dynamic range tells you how it was tracked, its spectrum tells you what room it was in, its phase tells you whether it's going to play nice with its neighbors. Read those stories first.

## The Diagnostic Workflow

### Gather stems

Collect all stem file paths. Every stem must be WAV format, mono or stereo. If the user provides a directory, list the WAV files in it. Count them -- you need to know what you're working with.

### Run the full diagnostic sweep

Call `batch_diagnostic` with every stem path in one shot. This runs all six analysis types (spectrum, loudness, dynamics, stereo, phase, problems) on every stem simultaneously. One call, complete picture.

The first thing you check in the results: **sample rate mismatch**. If stems have different sample rates, stop everything. That's a dealbreaker -- nothing else matters until they match. Flag it immediately and tell the user which stems are mismatched and what rate to convert to.

### Check phase and polarity

Phase problems are invisible to most analysis but devastating to a mix. They can't be fixed with EQ, compression, or any amount of processing. Find them now.

Run `analyze_phase` on every stereo stem. If any stem shows `polarity_inverted: true`, flag it immediately. A polarity flip takes one click to fix but hours to diagnose by ear.

For multi-mic recordings -- and this is critical for drums, guitar cabs, anything recorded with more than one mic -- run `compare_phase` between the close mic and room/overhead mics:
- Kick in vs kick out
- Snare top vs snare bottom
- Close mic vs room mic on any source

You're looking for time alignment issues. Sound travels at roughly 1ms per foot -- a room mic 10 feet away has a 10ms delay that creates comb filtering at specific frequencies. The `compare_phase` results tell you the delay in samples and whether polarity is inverted between the pair.

**Interpreting phase results:**
- Correlation > +0.8: excellent mono compatibility, no issues
- Correlation +0.3 to +0.8: acceptable, monitor during mixing
- Correlation < +0.3: problem -- stereo width processing may be excessive, or there's a real phase issue
- Correlation negative: likely polarity inversion, flip one channel
- "Sounds fine solo but thin/weird in context" = classic phase cancellation signature -- check correlation between the problem stem and everything it's layered with

### Triage problems by severity

Review the `detect_problems` results from the batch diagnostic. Every problem falls into one of four severity tiers. Address them in order -- dealbreakers first, always.

**Dealbreaker** -- fix before mixing, no exceptions:
- True peak > 0 dBTP (clipping baked into the file)
- Sample rate mismatch between stems
- Severe phase/polarity inversion between related stems
- Corrupted or truncated files (start/stop cut detection)

**Significant** -- address early, before you start building the mix:
- Noise floor above -50 dBFS (noise reduction needed)
- DC offset present (remove with HPF before processing)
- Mains hum detected at 50/60 Hz (notch filter or noise reduction)
- False stereo detected (duplicate channels -- note: mono sources in stereo containers are normal, not a problem)

**Moderate** -- address during mixing:
- Sibilance peaks above normal range
- Mud accumulation in 200-500 Hz across multiple stems
- Moderate harshness in 2-5 kHz
- Room resonances at specific frequencies

**Minor** -- optional cleanup, address if time permits:
- Slight spectral imbalances
- Minor noise bursts
- Low-level clicks below audibility threshold

### Analyze frequency masking between stems

This is where you find the conflicts that make mixes sound muddy or cluttered. Run `multi_stem_masking` with all stems that share frequency range. At minimum, check these common conflict pairs:
- Kick vs bass (the eternal battle at 60-100 Hz)
- Guitars vs vocals (presence fight at 2-4 kHz)
- Keys/synths vs guitars (midrange congestion)
- Multiple vocal layers against each other

The masking results rank pairs by severity and show the worst-offending frequency bands. High masking severity at 200-500 Hz between multiple pairs = your mix will sound muddy without complementary EQ. That's your roadmap for the mix engineer.

### Compare to a reference

If the genre is known, load the genre profile and compare:
- Call `list_profiles` to see available profiles (ambient, edm, electronic, hip-hop, lo-fi, metal, pop, rock, rock-metal)
- Call `load_profile` with the target genre to get reference values
- Call `compare_to_profile` on the mix bus or a rough balance to see where the current state sits relative to genre norms

If the user has a reference track (a WAV file they want to sound like), run `compare_to_reference` instead. This gives per-dimension deviations: spectrum, loudness, dynamics, stereo width.

**Genre context matters for interpretation.** A lo-fi hip-hop track with a noise floor at -55 dBFS and rolled-off highs isn't "problematic" -- that's the aesthetic. An EDM track at -20 LUFS integrated isn't "too quiet" -- it might not be mastered yet. Always interpret measurements through the lens of what the music is trying to be.

### Produce the mix brief

The mix brief is your handoff document. It's a structured summary that any downstream skill (`/phantom:mix-engineer`, `/phantom:session-architect`) can parse. Fill in the template from [mix-brief-template.md](mix-brief-template.md) with the results from all previous steps.

The brief must include:
- Session overview (stem count, sample rate, bit depth, genre/reference)
- Per-stem summary table (LUFS, peak, crest factor, phase correlation, key issues)
- Problems organized by severity tier (dealbreakers first, always)
- Masking map showing the worst frequency conflicts between stem pairs
- Overall assessment -- one paragraph, opinionated, honest
- Recommended processing order -- what to fix first, what to address during mixing

The processing order is important: dealbreakers first, then significant problems, then start mixing with the moderate and minor issues as items to address as you go. The order should also respect signal chain logic -- fix phase before EQ, remove noise before compression.

## Interpretation Quick Reference

These thresholds drive your triage decisions. For the complete measurement-to-action translation tables, see [measurement-actions.md](measurement-actions.md).

| Measurement | Condition | What it means |
|-------------|-----------|---------------|
| Crest factor | > 15 dB | Uncompressed, lots of dynamic range -- handle gently |
| Crest factor | 8-12 dB | Well-recorded, normal range for mixing |
| Crest factor | < 6 dB | Over-compressed -- do not add more compression |
| True peak | > 0 dBTP | Clipping -- dealbreaker |
| True peak | > -1 dBTP | Near clipping -- watch headroom |
| Phase correlation | > +0.8 | Excellent mono compatibility |
| Phase correlation | < +0.3 | Stereo width may be excessive, or real phase issue |
| Phase correlation | negative | Likely polarity inversion |
| SNR | > 70 dB | Professional recording quality |
| SNR | 50-60 dB | Acceptable, may need noise treatment |
| SNR | < 40 dB | Poor -- noise reduction required |
| Noise floor | above -50 dBFS | Significant noise, address before mixing |
| Masking severity | "high" at 200-500 Hz | Mud -- complementary EQ needed between conflicting stems |
| Spectral centroid | unusually low | Dark/muddy recording, may need high-end lift |
| Spectral centroid | unusually high | Bright/thin recording, check for missing body |

## Critical: Never Assume Stem Provenance

Mono stems in stereo containers (correlation = 1.0, width = 0) are completely normal for recorded tracks. A mono mic bounced to a stereo WAV looks identical in analysis to an AI-separated stem. **Never conclude stems are AI-separated, pre-mastered, or otherwise processed unless the user explicitly says so.** The diagnostician reports measurements -- it does not speculate about how the audio was created.

If you see indicators that *could* suggest AI separation (identical phase across all stems, unusual spectral gaps, bleed patterns), note the measurements but do not state conclusions about provenance. If it matters for mixing decisions, ask the user.

## Special Scenarios

### AI-separated stems (Demucs, etc.)
**Only apply this section when the user confirms stems were AI-separated.** AI stem separation introduces predictable artifacts: bleed between stems, phase anomalies from the separation algorithm, and sometimes false stereo (identical L/R). When analyzing confirmed separated stems, expect higher masking between pairs (that's bleed, not arrangement overlap) and check phase coherence between all stems -- separation can introduce subtle phase shifts that cause problems when summed.

### Pre-mastering mix check
When asked "is this ready for mastering?" -- run `full_diagnostic` on the single mix file, then `compare_to_profile` for the genre. The mastering-engineer skill's send-back criteria apply: if you'd need more than 4 dB of corrective EQ anywhere, or the fundamental balance is wrong (vocals buried, bass overwhelming), it needs more mix work, not mastering.

### Quick single-stem assessment
For a single stem with a specific complaint ("this vocal sounds weird"), run `full_diagnostic` on that one file. Don't overcomplicate it. But always check phase if the complaint involves how it sounds *in context* with other stems -- that's the phase cancellation signature.

## Reference Materials

- For complete measurement-to-action translation tables, see [measurement-actions.md](measurement-actions.md)
- For the mix brief output template, see [mix-brief-template.md](mix-brief-template.md)
