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

> **Workflow:** diagnostician -> session-architect -> mix-engineer -> effects-engineer -> mastering-engineer. Always analyze first.

## The Diagnostic Workflow

### Gather stems

Collect all stem file paths (WAV, mono or stereo). If given a directory, list WAV files.

If genre or reference track is unknown, ask now -- every downstream skill needs genre context.

**Alternate takes:** If filenames suggest multiple takes, ask which to use. Exclude unused takes -- they corrupt masking analysis.

`multi_stem_masking` accepts a maximum of 20 stems. If the session has more, group stems by instrument family and run multiple passes.

### Run the full diagnostic sweep

Call `batch_diagnostic` with every stem path in one shot. This runs all six analysis types (spectrum, loudness, dynamics, stereo, phase, problems) on every stem simultaneously. One call, complete picture.

#### First checks from batch results

Work through in order -- each can stop the session:

1. **Sample rate mismatch.** Different rates = dealbreaker. Stop, flag which stems mismatch and what to convert to.

2. **Bit depth and dynamic range.** Note bit depth of each stem. If stems mix 16-bit, 24-bit, and 32-bit float, flag it. The session-architect needs the highest bit depth to set the project. Bit depth determines theoretical dynamic range: 16-bit = 96 dB, 24-bit = 144 dB, 32-bit float = ~1500 dB. Downconverting 32-bit float to 16-bit without dither introduces quantization noise.

3. **Silent or near-silent stems.** Check the integrated LUFS of every stem. If a stem reads below -70 LUFS or the loudness analysis returns None (near-silent), flag it immediately -- it's likely an export mistake (empty track, muted channel accidentally bounced) or an unintended room tone track. Ask the user before including it in further analysis.

4. **Duration alignment.** If stems differ by more than a few seconds, note it -- may indicate different export sections or excessive head/tail silence.

5. **Loudness level spread.** Compare integrated LUFS across all stems. If the loudest and quietest differ by more than 20 LU (excluding intentionally quiet elements like room mics or pads), flag a gain staging problem. Stems tracked at wildly different levels suggest a multi-session recording or inconsistent preamp gain.

6. **Pre-printed effects detection.** If a stem shows very low crest factor (<6 dB) on a source that should be dynamic (acoustic guitar, vocals), or if the spectral balance shows steep filter slopes that look like intentional EQ rather than mic character, flag it as "possibly pre-printed effects." Pre-printed reverb, compression, or EQ limits mixing options. Ask the user if effects were intentionally printed.

7. **Timing drift between stems.** If stems were recorded in separate sessions, check for timing drift: compare transient alignment at the start and end of the files. Even 5-10ms of drift over a 4-minute song creates audible flamming and phase smear.

### Check phase and polarity

Phase problems require specific tools (polarity flip, time alignment, phase rotation plugins like Waves InPhase or Sound Radix Auto-Align). Standard EQ/compression worsens them. Find them now.

Run `analyze_phase` on every stereo stem. Flag any `polarity_inverted: true` immediately.

For multi-mic recordings (drums, guitar cabs), run `compare_phase` between close and room/overhead mics:
- Kick in vs kick out
- Snare top vs snare bottom
- Close mic vs room mic on any source

Sound travels ~1ms/foot. A room mic 10 feet away has 10ms delay causing comb filtering.

**Interpreting phase results (instrument-aware):**
- Correlation > +0.8: excellent mono compatibility, no issues
- Correlation +0.5 to +0.8: good, normal stereo content -- no action needed
- Correlation +0.3 to +0.5: context-dependent.
  - For bass, kick, snare, lead vocal: this is a problem. Low-end and center-image sources must be mono-compatible. Flag and recommend narrowing or phase-aligning.
  - For drum overheads, room mics, stereo keyboards, acoustic guitar (XY/ORTF): this is normal wide stereo. Note for mono-check but don't flag as an issue.
  - For anything with stereo widening applied: borderline. Check mono playback -- if level drops >3 dB when summed to mono, the widening is excessive.
- Correlation < +0.3: problem for any source. Investigate cause.
- Sustained negative: polarity inversion. Flip one channel. Occasional negative dips are normal; sustained near -1 = definite inversion.
- "Sounds fine solo but thin/weird in context" = phase cancellation -- run `compare_phase` between the problem stem and everything it's layered with.

**Mid-side encoded files.** Very low/negative correlation across all bands with one channel sounding "hollow" = possibly M/S encoded. Confirm with `analyze_stereo` (distinctive width/balance patterns). Ask user before proceeding.

### Triage problems by severity

Review `detect_problems` results (11 detectors: clipping, DC offset, ISPs, noise floor, SNR, hum, sibilance, mud, harshness, resonant peaks, lossy artifacts). Four severity tiers -- dealbreakers first.

**Dealbreaker** -- fix before mixing, no exceptions:
- True peak > 0 dBTP (clipping baked into the file -- samples are hard-clipped)
- Sample rate mismatch between stems
- Severe phase/polarity inversion between related stems
- Corrupted or truncated files (start/stop cut detection)

**Significant** -- address early, before you start building the mix:
- True peak > -1 dBTP (exceeds EBU R128 and streaming platform limits -- tight headroom that limits mastering options)
- Noise floor -60 to -50 dBFS: gate during silence or use iZotope RX Spectral De-noise (learn noise profile from a silent section, reduce 6-10 dB). **Cumulative noise math:** N stems at same floor sum to `floor + 10*log10(N)` dB. Examples: 4@-55 = -49 dBFS; 6@-58 = -50.2 dBFS; 8@-58 = -49 dBFS; 16@-60 = -48 dBFS. Calculate and report the actual summed floor.
- Noise floor above -50 dBFS: dedicated noise reduction required (RX Spectral De-noise or Waves NS1/WNS)
- DC offset present (remove with a dedicated DC offset removal tool, available in most DAWs and iZotope RX; if unavailable, use an HPF set very low at 5-20 Hz)
- Mains hum detected at 50/60 Hz (notch filter at the fundamental plus harmonics: 50/100/150/200 Hz or 60/120/180/240 Hz). Note: the dominant hum frequency is often 2x the mains frequency (100 Hz or 120 Hz) because magnetic force is proportional to the square of the current. Listen to identify the loudest harmonic before notching.
- False stereo detected (duplicate channels -- note: mono sources in stereo containers are normal, not a problem)
- Lossy codec artifacts detected (the source file may have been transcoded from a lossy format)

**Moderate** -- address during mixing:
- Sibilance 4-10 kHz (male 3-6 kHz, female 6-8 kHz). Use de-esser or dynamic EQ band with 3-6 dB reduction at Q ~2.
- Mud 200-500 Hz across stems. **Priority fix:** HPF everything that isn't kick or bass: vocals 80-100 Hz, guitars 80 Hz, keys 60-80 Hz. For remaining mud between pairs, cut 2-4 dB with Q 1.5-3 on the less important stem in the conflict band.
- Moderate harshness in 2-5 kHz
- Room resonances at specific frequencies

**Minor** -- optional: slight spectral imbalances, minor noise bursts, low-level clicks.

### Analyze frequency masking between stems

Run `multi_stem_masking` with all stems. Key conflict pairs:
- Kick vs bass (60-100 Hz)
- Guitars vs vocals (2-4 kHz)
- Keys/synths vs guitars (midrange congestion)
- Multiple vocal layers

High masking at 200-500 Hz = mud. **EQ prescription:** Cut 2-4 dB at Q 1.5-3 on the less important stem in each pair. Boost the other 1-2 dB only if needed.

**Masking vs bleed (live recordings).** Bleed causes overreported masking. Ask about recording setup, discount severity in bleed frequencies, focus on each instrument's *direct* signal energy.

**When masking is actually an arrangement problem.** If 4+ stems show high masking in the same band, EQ carving won't fix it. Flag as an arrangement issue -- recommend thinning simultaneous elements.

### Assess aggregate headroom

If most stems peak above -6 dBTP, flag that gain staging is critical. Note aggregate headroom in the mix brief.

### Compare to a reference

If genre is known: `list_profiles` -> `load_profile` -> `compare_to_profile`. Available: ambient, edm, electronic, hip-hop, lo-fi, metal, pop, rock, rock-metal. If user has a reference WAV: `compare_to_reference` (spectrum, loudness, dynamics, stereo width deviations).

**Genre context matters.** Lo-fi at -55 dBFS noise with rolled-off highs = aesthetic, not a problem. Always interpret through genre intent.

### Produce the mix brief

Fill in [mix-brief-template.md](mix-brief-template.md). The brief must include:
- Session overview (stem count, sample rate, bit depth, genre/reference, BPM if known, aggregate headroom estimate)
- Per-stem summary table (LUFS, peak, crest factor, phase correlation, stereo width, duration, key issues)
- Problems organized by severity tier (dealbreakers first, always)
- Masking map showing the worst frequency conflicts between stem pairs
- Overall assessment -- one paragraph, opinionated, honest
- Processing order checklist (below)

**Processing order checklist** (include in brief with stem-specific details):
1. Fix sample rate mismatches (offline SRC in DAW or SoX: `sox in.wav -r 48000 out.wav`)
2. Remove DC offset (RX DC Offset module or DAW utility)
3. Fix polarity inversions (polarity flip on the channel)
4. Time-align multi-mic pairs (Auto-Align or manual nudge by ms shown in `compare_phase`)
5. Remove noise/hum (RX Spectral De-noise, De-hum -- before any compression)
6. Address clipping (RX De-clip if baked in; otherwise re-export from session)
7. Apply HPFs on non-bass stems (vocals 80-100 Hz, guitars 80 Hz, keys 60-80 Hz)
8. Begin mixing -- address sibilance, masking EQ, harshness during mix

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
| Phase correlation | +0.3 to +0.5 | **Instrument-dependent** -- problem for bass/kick/vocal; normal for overheads/rooms/stereo keys |
| Phase correlation | < +0.3 | Problem for any source |
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

**Spectral centroid reference ranges by instrument:**
| Instrument | Expected range | Edge cases |
|------------|---------------|------------|
| Vocals | 1-3 kHz | Falsetto/whisper can push to 4+ kHz |
| Bass guitar (fingerstyle) | 200-600 Hz | Normal -- low centroid expected |
| Bass guitar (pick/aggressive) | 400-1.2 kHz | Higher centroid is normal, not a mislabel |
| Distorted/overdriven bass | 800-2 kHz | Harmonics shift centroid up -- expected with distortion |
| Acoustic guitar | 1-3 kHz | Nylon-string sits lower (800 Hz-2 kHz) |
| Electric guitar (clean) | 1-3 kHz | |
| Electric guitar (distorted) | 2-5 kHz | Distortion adds upper harmonics |
| Drums (overhead) | 3-6 kHz | |
| Drums (kick) | 60-150 Hz | A "kick" at 2 kHz = mislabeled stem |
| Synth pad | 500 Hz-3 kHz | Extremely variable by design |
| Full mix | 2-4 kHz | Genre-dependent: metal 3-5 kHz, lo-fi 1-2 kHz |

If a stem's centroid falls far outside its expected range, investigate: possible naming mismatch, heavy filtering, or unusual recording technique.

## Critical: Never Assume Stem Provenance

Mono in stereo containers (correlation=1.0, width=0) is normal. **Never conclude stems are AI-separated or pre-processed unless the user says so.** Note unusual measurements neutrally; don't speculate on provenance.

## Special Scenarios

### AI-separated stems (Demucs, etc.)
**Only when user confirms.** Expect: bleed between stems (higher masking than real recordings), phase anomalies from the algorithm, possible false stereo. Check phase coherence between all stems.

### Pre-mastering mix check
Run `full_diagnostic` on the mix file, then `compare_to_profile` for the genre. Check these criteria:

| # | Check | Pass | Borderline | Fail |
|---|-------|------|------------|------|
| 1 | Corrective EQ needed | < 2 dB anywhere | 2-3 dB in 1-2 bands | > 3 dB or multiple bands |
| 2 | Fundamental balance | Vocals, bass, drums sit naturally | One element slightly off | Vocals buried, bass overwhelming, or drums dominating |
| 3 | Phase (mix bus correlation) | > +0.5 | +0.3 to +0.5 | < +0.3 |
| 4 | True peak | < -1 dBTP | -1 to 0 dBTP (tight but workable) | > 0 dBTP (baked clipping) |
| 5 | Noise floor | < -60 dBFS | -60 to -50 dBFS | > -50 dBFS |
| 6 | Dynamic range (LRA) | Within genre norms +/- 3 LU | 3-5 LU outside norms | > 5 LU outside genre norms |

**Borderline handling:** If all checks pass but 1-2 are borderline, the mix *can* go to mastering with a note. If 3+ are borderline, recommend another mix pass. Any single fail = send back with specific fix instructions.

### Quick single-stem assessment
For a single stem with a specific complaint ("this vocal sounds weird"), run `full_diagnostic` on that one file. Don't overcomplicate it. But always check phase if the complaint involves how it sounds *in context* with other stems -- that's the phase cancellation signature.

### Stem content verification
If you notice a stem's spectral characteristics don't match its filename -- a "kick.wav" with a spectral centroid at 2 kHz, or a "bass.wav" with most energy above 1 kHz -- flag it. A mislabeled stem will silently corrupt every downstream decision: the masking map, bus routing, and processing choices. When in doubt, note the anomaly and ask the user to confirm.

### Click or metronome bleed
If a stem shows perfectly regular transient peaks at a consistent frequency (often around 1 kHz or 2-3 kHz for woodblock samples), it may contain click track bleed or an accidentally exported metronome. Flag it for the user -- a click track in the masking analysis would produce misleading results.

## Reference Materials

See [measurement-actions.md](measurement-actions.md) and [mix-brief-template.md](mix-brief-template.md).
