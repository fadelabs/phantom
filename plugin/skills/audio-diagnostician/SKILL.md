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

If the user hasn't mentioned the genre or provided a reference track, ask now. Every downstream skill needs genre context -- the session-architect for templates, the mix-engineer for tonal targets, the effects-engineer for tempo-synced processing, the mastering-engineer for loudness targets. Get it early.

**Watch for alternate takes.** If filenames suggest multiple takes of the same part (e.g., `vocal_take1.wav`, `vocal_take2.wav`, `vocal_comp.wav`), ask the user which take they're using before running analysis. Including alternate takes in the masking analysis produces misleading results -- of course three takes of the same vocal show massive masking with each other. Exclude unused takes from the diagnostic sweep entirely.

`multi_stem_masking` accepts a maximum of 20 stems. If the session has more, group stems by instrument family and run multiple passes.

### Run the full diagnostic sweep

Call `batch_diagnostic` with every stem path in one shot. This runs all six analysis types (spectrum, loudness, dynamics, stereo, phase, problems) on every stem simultaneously. One call, complete picture.

#### First checks from batch results

Work through these in order -- each one can be a session-stopper:

1. **Sample rate mismatch.** If stems have different sample rates, stop everything. That's a dealbreaker -- nothing else matters until they match. Flag it immediately and tell the user which stems are mismatched and what rate to convert to.

2. **Bit depth.** Note the bit depth of each stem from the file metadata. If stems mix 16-bit, 24-bit, and 32-bit float, flag it in the brief. The session-architect needs to know the highest bit depth to set the project correctly. Downconverting 32-bit float to 16-bit without dither introduces quantization noise.

3. **Silent or near-silent stems.** Check the integrated LUFS of every stem. If a stem reads below -70 LUFS or the loudness analysis returns None (near-silent), flag it immediately -- it's likely an export mistake (empty track, muted channel accidentally bounced) or an unintended room tone track. Ask the user before including it in further analysis.

4. **Duration alignment.** Compare the durations from batch results. If stems differ by more than a few seconds, note it -- one stem may have been exported from a different section, or some stems may have excessive head/tail silence. The session-architect needs this to position stems correctly.

### Check phase and polarity

Phase problems are invisible to most analysis but devastating to a mix. They can't be fixed with EQ or compression -- they require specific phase tools: polarity flip, time alignment, or phase rotation plugins (like Waves InPhase or Sound Radix Auto-Align). Standard mixing processing can actually worsen phase issues, which is why you find them now before anyone reaches for an EQ.

Run `analyze_phase` on every stereo stem. If any stem shows `polarity_inverted: true`, flag it immediately. A polarity flip takes one click to fix but hours to diagnose by ear.

For multi-mic recordings -- and this is critical for drums, guitar cabs, anything recorded with more than one mic -- run `compare_phase` between the close mic and room/overhead mics:
- Kick in vs kick out
- Snare top vs snare bottom
- Close mic vs room mic on any source

You're looking for time alignment issues. Sound travels at roughly 1ms per foot -- a room mic 10 feet away has a 10ms delay that creates comb filtering at specific frequencies. The `compare_phase` results tell you the delay in samples and whether polarity is inverted between the pair.

**Interpreting phase results:**
- Correlation > +0.8: excellent mono compatibility, no issues
- Correlation +0.5 to +0.8: good, normal stereo content -- no action needed
- Correlation +0.3 to +0.5: wide stereo, approaching risky -- check on mono playback systems
- Correlation < +0.3: problem -- stereo width processing may be excessive, or there's a real phase issue
- Sustained negative correlation: possible polarity inversion -- flip one channel. Occasional negative dips are normal with wide stereo content; sustained readings near -1 indicate definite inversion
- "Sounds fine solo but thin/weird in context" = classic phase cancellation signature -- check correlation between the problem stem and everything it's layered with

**Identifying mid-side encoded files.** If a stereo stem shows unusual phase analysis results -- very low or negative correlation across all bands, with one channel sounding "hollow" or "ambient" compared to the other -- it may be mid-side encoded rather than standard L/R stereo. An M/S file imported as regular stereo will sound wrong and measure oddly. If you suspect M/S encoding, ask the user before proceeding. The stereo analysis (`analyze_stereo`) can help confirm: M/S files show distinctive width and balance patterns.

### Triage problems by severity

Review the `detect_problems` results from the batch diagnostic. The tool runs 11 detectors including clipping, DC offset, inter-sample peaks, noise floor, SNR, hum, sibilance, mud, harshness, resonant peaks, and lossy codec artifacts. Every problem falls into one of four severity tiers. Address them in order -- dealbreakers first, always.

**Dealbreaker** -- fix before mixing, no exceptions:
- True peak > 0 dBTP (clipping baked into the file -- samples are hard-clipped)
- Sample rate mismatch between stems
- Severe phase/polarity inversion between related stems
- Corrupted or truncated files (start/stop cut detection)

**Significant** -- address early, before you start building the mix:
- True peak > -1 dBTP (exceeds EBU R128 and streaming platform limits -- tight headroom that limits mastering options)
- Noise floor between -60 and -50 dBFS (audible in quiet passages -- gate during silence or apply noise reduction in quiet sections)
- Noise floor above -50 dBFS (significant noise -- dedicated noise reduction required before mixing)
- DC offset present (remove with a dedicated DC offset removal tool, available in most DAWs and iZotope RX; if unavailable, use an HPF set very low at 5-20 Hz)
- Mains hum detected at 50/60 Hz (notch filter at the fundamental plus harmonics: 50/100/150/200 Hz or 60/120/180/240 Hz). Note: the dominant hum frequency is often 2x the mains frequency (100 Hz or 120 Hz) because magnetic force is proportional to the square of the current. Listen to identify the loudest harmonic before notching.
- False stereo detected (duplicate channels -- note: mono sources in stereo containers are normal, not a problem)
- Lossy codec artifacts detected (the source file may have been transcoded from a lossy format)

**Moderate** -- address during mixing:
- Sibilance peaks in the 4-10 kHz range (most problematic at 5-8 kHz; male voices tend 3-6 kHz, female voices 6-8 kHz)
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

### Assess aggregate headroom

Individual stems may each peak at safe levels, but when summed they can easily clip the mix bus. Estimate the combined headroom situation: if most stems peak above -6 dBTP, flag that gain staging will be critical. The mix-engineer needs to know this upfront -- a session where every stem is hot requires pulling faders down before any processing starts.

Note the approximate aggregate headroom in the mix brief so the session-architect and mix-engineer can set gain staging targets from the beginning.

### Compare to a reference

If the genre is known, load the genre profile and compare:
- Call `list_profiles` to see available profiles (ambient, edm, electronic, hip-hop, lo-fi, metal, pop, rock, rock-metal)
- Call `load_profile` with the target genre to get reference values
- Call `compare_to_profile` on the mix bus or a rough balance to see where the current state sits relative to genre norms

If the user has a reference track (a WAV file they want to sound like), run `compare_to_reference` instead. This gives per-dimension deviations: spectrum, loudness, dynamics, stereo width.

**Genre context matters for interpretation.** A lo-fi hip-hop track with a noise floor at -55 dBFS and rolled-off highs isn't "problematic" -- that's the aesthetic. An EDM track at -20 LUFS integrated isn't "too quiet" -- it might not be mastered yet. Always interpret measurements through the lens of what the music is trying to be.

### Produce the mix brief

The mix brief is your handoff document. It's a structured summary that any downstream skill (`/phantom:mix-engineer`, `/phantom:session-architect`, `/phantom:effects-engineer`) can parse. The effects-engineer benefits from the masking map (spatial processing decisions depend on which stems are fighting for space) and per-stem stereo width (widening a stem that's already wide is different from widening a narrow one). Fill in the template from [mix-brief-template.md](mix-brief-template.md) with the results from all previous steps.

The brief must include:
- Session overview (stem count, sample rate, bit depth, genre/reference, BPM if known, aggregate headroom estimate)
- Per-stem summary table (LUFS, peak, crest factor, phase correlation, stereo width, duration, key issues)
- Problems organized by severity tier (dealbreakers first, always)
- Masking map showing the worst frequency conflicts between stem pairs
- Overall assessment -- one paragraph, opinionated, honest
- Recommended processing order -- what to fix first, what to address during mixing

The processing order is important: dealbreakers first, then significant problems, then start mixing with the moderate and minor issues as items to address as you go. The order should also respect signal chain logic -- fix phase before EQ, remove noise before compression.

## Interpretation Quick Reference

These thresholds drive your triage decisions. For the complete measurement-to-action translation tables, see [measurement-actions.md](measurement-actions.md).

| Measurement | Condition | What it means |
|-------------|-----------|---------------|
| Crest factor | > 15 dB | Highly dynamic, likely uncompressed (note: source-dependent -- drums and transient material naturally sit higher; a legato string section may be 6-8 dB without any compression) |
| Crest factor | 8-12 dB | Well-recorded, normal range for mixing |
| Crest factor | < 6 dB | Over-compressed -- do not add more compression |
| True peak | > 0 dBTP | Hard clipping -- dealbreaker |
| True peak | > -1 dBTP | Exceeds EBU R128 / streaming limits -- significant |
| True peak | > -3 dBTP | Tight headroom for mastering |
| Phase correlation | > +0.8 | Excellent mono compatibility |
| Phase correlation | +0.5 to +0.8 | Good, normal stereo content |
| Phase correlation | +0.3 to +0.5 | Wide stereo, approaching risky -- check mono playback |
| Phase correlation | < +0.3 | Problem -- real phase issue or excessive widening |
| Phase correlation | sustained negative | Possible polarity inversion (near -1 = definite) |
| SNR | > 70 dB | Professional recording quality |
| SNR | 60-70 dB | Good -- acceptable, gate during silence if needed |
| SNR | 50-60 dB | Acceptable, may need noise treatment |
| SNR | 40-50 dB | Poor -- dedicated noise reduction required |
| SNR | < 40 dB | Unacceptable -- re-record if possible |
| Noise floor | below -70 dBFS | Clean, no treatment needed |
| Noise floor | -60 to -50 dBFS | Audible in quiet passages -- gate or treat quiet sections |
| Noise floor | above -50 dBFS | Significant noise, address before mixing |
| Masking severity | "high" at 200-500 Hz | Mud -- complementary EQ needed between conflicting stems |
| Spectral centroid | below 1 kHz (non-bass) | Dark/muddy recording, may need high-end lift |
| Spectral centroid | above 5 kHz | Bright/thin recording, check for missing body |
| LRA | > 15 LU | Very dynamic -- classical, ambient, some jazz |
| LRA | 7-12 LU | Normal range for pop/rock |
| LRA | < 5 LU | Heavily compressed -- expected for EDM/hip-hop |

**Typical spectral centroid reference ranges:** vocals 1-3 kHz, full mix 2-4 kHz, bass guitar 200-800 Hz, acoustic guitar 1-3 kHz, drums (overhead) 3-6 kHz. If a stem's centroid falls far outside the expected range for its instrument, investigate -- it may indicate a naming mismatch, heavy filtering, or unusual recording.

## Critical: Never Assume Stem Provenance

Mono stems in stereo containers (correlation = 1.0, width = 0) are completely normal for recorded tracks. A mono mic bounced to a stereo WAV looks identical in analysis to an AI-separated stem. **Never conclude stems are AI-separated, pre-mastered, or otherwise processed unless the user explicitly says so.** The diagnostician reports measurements -- it does not speculate about how the audio was created.

If you see indicators that *could* suggest AI separation (identical phase across all stems, unusual spectral gaps, bleed patterns), note the measurements but do not state conclusions about provenance. If it matters for mixing decisions, ask the user.

## Special Scenarios

### AI-separated stems (Demucs, etc.)
**Only apply this section when the user confirms stems were AI-separated.** AI stem separation introduces predictable artifacts: bleed between stems, phase anomalies from the separation algorithm, and sometimes false stereo (identical L/R). When analyzing confirmed separated stems, expect higher masking between pairs (that's bleed, not arrangement overlap) and check phase coherence between all stems -- separation can introduce subtle phase shifts that cause problems when summed.

### Pre-mastering mix check
When asked "is this ready for mastering?" -- run `full_diagnostic` on the single mix file, then `compare_to_profile` for the genre. Check against the mastering-engineer's full send-back criteria:

1. **Corrective EQ needed:** Would you need more than 3 dB of corrective EQ anywhere? If yes, it needs more mix work. (The widely cited mastering guideline is 2-3 dB max.)
2. **Fundamental balance:** Are vocals buried, bass overwhelming, or drums too loud/quiet? These are mix problems, not mastering problems.
3. **Phase:** Is the mix bus correlation below +0.3? Severe phase issues need to be resolved at the stem level.
4. **Clipping:** Is there baked-in clipping (true peak > 0 dBTP) that can't be undone? And is the true peak above -1 dBTP, limiting the mastering engineer's headroom?
5. **Noise:** Is there an excessive noise floor that should have been addressed during mixing?

If any of these fail, recommend going back to the mix. Be specific about what needs fixing.

### Quick single-stem assessment
For a single stem with a specific complaint ("this vocal sounds weird"), run `full_diagnostic` on that one file. Don't overcomplicate it. But always check phase if the complaint involves how it sounds *in context* with other stems -- that's the phase cancellation signature.

### Stem content verification
If you notice a stem's spectral characteristics don't match its filename -- a "kick.wav" with a spectral centroid at 2 kHz, or a "bass.wav" with most energy above 1 kHz -- flag it. A mislabeled stem will silently corrupt every downstream decision: the masking map, bus routing, and processing choices. When in doubt, note the anomaly and ask the user to confirm.

### Click or metronome bleed
If a stem shows perfectly regular transient peaks at a consistent frequency (often around 1 kHz or 2-3 kHz for woodblock samples), it may contain click track bleed or an accidentally exported metronome. Flag it for the user -- a click track in the masking analysis would produce misleading results.

## Reference Materials

- For complete measurement-to-action translation tables, see [measurement-actions.md](measurement-actions.md)
- For the mix brief output template, see [mix-brief-template.md](mix-brief-template.md)
