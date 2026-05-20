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

> **Workflow position:** **audio-diagnostician** → session-architect → mix-engineer → effects-engineer → mastering-engineer. Always analyze first.

The diagnostic's job is to find problems BEFORE they waste mixing time. Phase issues masquerading as tonal problems. Noise that accumulates across stems. Masking conflicts that no amount of EQ can fix. Every problem found here saves an hour of guessing later.

**Non-negotiable rules (repeated at end as final checklist):**
1. Check phase before anything else — phase problems masquerade as tonal problems
2. Interpret every measurement in instrument context — drums at 15 dB crest factor is normal, vocals at 15 dB is uncompressed
3. Genre context matters — lo-fi at -55 dBFS noise with rolled-off highs is aesthetic, not a problem
4. Never assume stem provenance — mono in stereo containers is normal, don't speculate on AI separation

## Step 1: Gather Stems

Collect all stem file paths (WAV, mono or stereo). If given a directory, list WAV files.

If genre or reference track is unknown, **ask now** — every downstream skill needs genre context.

**Alternate takes:** If filenames suggest multiple takes, ask which to use. Exclude unused takes — they corrupt masking analysis.

`multi_stem_masking` accepts max 20 stems. If session has more, group by instrument family and run multiple passes.

## Step 2: Run the Full Diagnostic Sweep

Call `batch_diagnostic` with every stem path in one shot.

### First Checks (in order — each can stop the session)

| Check | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Sample rate mismatch | Different rates between stems | **Dealbreaker** | Stop. Flag which stems mismatch. Convert to highest rate. |
| Silent stems | Integrated LUFS below -70 or None | **Dealbreaker** | Likely export mistake. Ask user before including. |
| Bit depth mix | 16/24/32 mixed | **Flag** | Note highest depth for session-architect. 32→16 without dither = quantization noise. |
| Duration mismatch | Stems differ by > few seconds | **Flag** | Different export sections or excess head/tail silence. |
| Loudness spread | > 20 LU between loudest and quietest | **Flag** | Gain staging problem. Multi-session recording or inconsistent preamp. |
| Pre-printed effects | Crest factor < 6 on naturally dynamic source, OR spectral tilt doesn't match instrument type, OR flat loudness contour over time | **Flag** | Distinguish musician's tone (pedal compression, amp distortion, instrument through effects at tracking) from post-production processing. A bass through a compressor pedal = the player's sound, not a problem. Ask about the signal chain before flagging. Printed EQ narrows later options; printed compression on top of more compression destroys transients; printed reverb cannot be removed. |
| Timing drift | Transient misalignment between stems > 5 ms | **Significant** | Measure using `compare_phase` time-delay value between stems sharing transient events. For non-transient stems, cross-correlate against the reference stem (usually drums). Drift > 5 ms = separate sessions or DAW latency offset. Nudge to align. |

**Bit depth note:** 16-bit = ~96 dB dynamic range, 24-bit = ~144 dB. 16-bit stems with noise floor above -70 dBFS may be quantization-limited — flag as re-export candidates.

## Step 3: Phase and Polarity Check

Phase problems require specific tools (polarity flip, time alignment). Standard EQ/compression worsens them. Find them now.

Run `analyze_phase` on every stereo stem. Flag any `polarity_inverted: true` immediately.

**M/S detection (check BEFORE interpreting correlation):** Very low/negative correlation across all bands + one channel sounding "hollow" = possibly mid-side encoded. Run `analyze_stereo` to confirm. M/S files show expected negative correlation — do NOT flag as phase problems. Ask user before proceeding.

For multi-mic recordings, run `compare_phase` in this order (fix highest-energy pair first — its correction changes the summed phase picture for subsequent checks):
1. **Kick in vs kick out** — highest-energy low-frequency pair, most damaging if out of phase
2. **Snare top vs snare bottom** — flip bottom mic polarity if correlation < +0.3
3. **Close mic vs room mic** — sound travels ~1 ms/foot — a room mic 10 feet away = 10 ms delay = comb filtering
4. **DI vs amped version** of same instrument — latency offset from amp processing chain

Re-run `compare_phase` after each fix to confirm improvement before moving to the next pair.

### Phase Correlation Interpretation (Instrument-Aware)

| Correlation | Bass/Kick/Snare/Lead Vocal | Overheads/Room/Stereo Keys | Anything with Widening |
|-------------|---------------------------|---------------------------|----------------------|
| > +0.8 | Excellent | Excellent | Excellent |
| +0.5 to +0.8 | Good | Good | Good |
| +0.3 to +0.5 | **Problem — flag** | Normal wide stereo | Borderline — check if mono drops > 3 dB |
| < +0.3 | **Problem** | **Problem** | **Problem** |
| Sustained negative | Polarity inversion — flip one channel (unless M/S encoded — see above) | Polarity inversion | Polarity inversion |

**Diagnostic pattern:** "Sounds fine solo but thin/weird in context" = phase cancellation. Run `compare_phase` between the problem stem and everything it's layered with.

**"Fixed enough" threshold:** After correction, correlation should improve by at least +0.2 AND reach the "Good" row for that instrument type. Soloing both stems together should sound full, not hollow or thin. If correction yields only marginal improvement, the problem may be comb filtering from reflections — note this for mix-engineer.

## Step 4: Triage Problems by Severity

Review `detect_problems` results. Four severity tiers — dealbreakers first. **Confidence prefix** each finding: **Definite** (clipping, polarity inversion — measurable, unambiguous), **Likely** (noise above threshold, clear masking), **Possible** (borderline values, context-dependent — needs engineer judgment).

**Intent check:** Before flagging unconventional measurements (distorted vocals, transient-free drums, deliberately clipped signals), consider whether the measurement reflects a creative choice. If the result could be intentional, mark as **Possible** and ask before escalating.

**Dealbreaker** (fix before mixing):
- True peak > 0 dBTP (baked clipping)
- Sample rate mismatch
- Severe phase/polarity inversion between related stems

**Significant** (address before building mix — report with **playback context**: headphone listeners hear noise at -52 dBFS; club/PA playback masks it under ambient noise):
- True peak > -1 dBTP (tight headroom)
- Noise floor -60 to -50 dBFS — gate during silence or spectral de-noise. **Cumulative math:** Calculate per-section, not total stem count. If verse has 4 active stems at -58 dBFS → -52 dBFS floor; chorus with 12 stems at -58 → -47 dBFS. Report worst-case section. **Verification:** After reduction, noise floor should drop to -60 dBFS or below. A/B with original — if you hear "underwater" artifacts or loss of air/breath, the reduction was too aggressive.
- Noise floor above -50 dBFS — dedicated noise reduction required. Within lo-fi/tape genres, distinguish **aesthetic noise** (tape hiss, vinyl crackle — keep, it's the texture) from **technical noise** (60 Hz hum, ground loop buzz, digital artifacts — always remove regardless of genre).
- DC offset — remove with DC offset tool or HPF at 5-20 Hz
- Mains hum at 50/60 Hz — notch at fundamental + harmonics (50/100/150/200 or 60/120/180/240 Hz). The loudest harmonic is often 2× mains frequency.
- Lossy codec artifacts detected

**Moderate** (address during mixing):
- Sibilance 4-10 kHz (male 3-6 kHz, female 6-8 kHz) — de-esser or dynamic EQ, 3-6 dB reduction
- Mud 200-500 Hz across stems — HPF everything except kick/bass, complementary EQ between conflicting pairs
- Harshness 2-5 kHz
- Room resonances at specific frequencies

**Minor** (optional): spectral imbalances, minor noise bursts, low-level clicks.

## Step 5: Frequency Masking Analysis

Run `multi_stem_masking` with all stems. **Pan-aware masking:** If stems are hard-panned to opposite sides (known from session notes or stereo analysis), discount masking severity — L/R separation reduces perceptual masking. Only flag masking between stems sharing the same stereo position. Key conflict pairs:

| Pair | Conflict Zone | Downstream Action |
|------|--------------|-------------------|
| Kick vs Bass | 60-100 Hz | → session-architect: prewire sidechain. → mix-engineer: complementary EQ. |
| Guitars vs Vocals | 2-4 kHz | → mix-engineer: cut guitars at vocal presence frequency. |
| Keys vs Guitars | 300 Hz-1 kHz | → mix-engineer: pan separation + complementary EQ. |
| Multiple vocals | 1-5 kHz | → mix-engineer: slight frequency offset per voice + different reverb sends. |
| 4+ stems masking same band | Arrangement problem | Flag — EQ carving won't fix it. Recommend thinning simultaneous elements. |

**Gain-stage before masking analysis:** If stems differ by more than 12 LU, normalize to common monitoring level (e.g., -18 LUFS) before running masking analysis. Analysis normalization only — do not alter stem files.

**Live recordings:** Bleed causes overreported masking. Discount bleed-frequency masking by one tier. Focus on direct signal energy.

**Expected outcome after masking fixes:** Complementary EQ should drop masking score from "high" to "moderate" or lower. If it doesn't, the conflict is arrangement-level, not mix-level.

## Step 6: Produce the Mix Brief

1. **Session overview** — stem count, sample rate, bit depth, genre/reference, BPM if known, aggregate headroom
2. **Per-stem summary table** — LUFS, peak, crest factor, phase correlation, stereo width, key issues
3. **Problems by severity** — dealbreakers first, always
4. **Masking map** — worst frequency conflicts between pairs, with downstream routing recommendations
5. **Overall assessment** — one paragraph, opinionated, honest
6. **Processing order** — the ordered checklist below

This order matters — each step depends on the previous:

1. **Fix sample rate mismatches** (offline SRC)
2. **Remove DC offset** (RX or DAW utility)
3. **Fix polarity inversions** (flip on channel)
4. **Time-align multi-mic pairs** (Auto-Align or manual nudge by ms from `compare_phase`)
5. **Remove noise/hum** (spectral de-noise, de-hum — BEFORE any compression, which amplifies noise)
6. **Address clipping** (RX De-clip if baked; otherwise re-export from session)
7. **Apply HPFs** on non-bass stems (vocals 80-100 Hz, guitars 80 Hz, keys 60-80 Hz)
8. **Begin mixing** — address sibilance, masking EQ, harshness during mix

### Handoff to Downstream Skills

Explicitly tell downstream skills what to do:

| Finding | → Session Architect | → Mix Engineer |
|---------|-------------------|----------------|
| Kick/bass masking | Prewire sidechain routing | Complementary EQ + sidechain |
| Phase issues | Route multi-mic to alignment sub-bus | Check phase before EQ |
| Over-compressed stems | Mark "no comp needed" | Skip compression on those tracks |
| Severe noise | Insert gate as first plugin | Noise gate before any dynamics |
| Guitar/vocal masking | Route guitars through vocal-sidechain bus | Cut guitars at 2-4 kHz |

## Interpretation Quick Reference

For the complete measurement-to-action tables: load [measurement-actions.md](measurement-actions.md).

### Crest Factor (Instrument & Playing-Style Aware)

| Crest Factor | Drums/Percussion | Vocals/Guitar/Keys | Synth Pads/Strings |
|-------------|-----------------|-------------------|-------------------|
| > 15 dB | Normal — transient-heavy | Very dynamic, handle gently | Unusual — unless plucked/arpeggiated (then normal) |
| 8-12 dB | Light compression applied | Well-recorded, standard processing | Normal |
| < 6 dB | Over-compressed | Over-compressed | Normal for sustained sources |

**Playing style override:** When crest factor contradicts the instrument label, check the actual waveform envelope. A "synth bass" with 14 dB crest factor and percussive transients = plucky playing style, not a problem. A "drum" stem with 5 dB crest = either heavy compression or electronic/programmed drums. Use envelope shape, not instrument name, as the ground truth.

### Key Thresholds

| Measurement | Threshold | Action |
|-------------|-----------|--------|
| True peak > 0 dBTP | Dealbreaker | Baked clipping — de-clip or re-export |
| True peak > -1 dBTP | Significant | Tight headroom — leave for mastering to address |
| Phase correlation < +0.3 | Problem (center sources) | Check for polarity flip or time offset |
| Noise floor > -50 dBFS | Significant | Dedicated noise reduction — verify with A/B |
| SNR < 40 dB | Re-record if possible | Noise reduction cannot recover this cleanly |

## Special Scenarios

### Pre-Mastering Mix Check

Run `full_diagnostic` on mix file, then `compare_to_profile` for genre:

| Check | Pass | Borderline | Fail |
|-------|------|------------|------|
| Corrective EQ needed | < 2 dB | 2-3 dB in 1-2 bands | > 3 dB or multiple bands |
| Balance | Vocals/bass/drums sit naturally | One element slightly off | Vocals buried or bass overwhelming |
| Phase (mix bus) | > +0.5 | +0.3 to +0.5 | < +0.3 |
| True peak | < -1 dBTP | -1 to 0 dBTP | > 0 dBTP |
| Noise floor | < -60 dBFS | -60 to -50 dBFS | > -50 dBFS |

1-2 borderline = proceed to mastering with notes. 3+ borderline = another mix pass. Any fail = send back with specific fix: "Corrective EQ fail" → identify which bands and by how much; "Vocals buried" → raise 2-4 kHz by estimated amount; "True peak fail" → pull master fader down by excess amount.

### Mid-Mix Diagnostics

When running on a mix-in-progress (not raw stems), processing is already applied. Don't flag compression as "over-compressed stems" or EQ curves as problems if the engineer applied them intentionally. Ask what processing has been done before diagnosing. Focus on: new problems introduced by processing (distortion from overdriven plugins, phase shift from linear-phase EQ on transients), and remaining issues the current processing hasn't addressed.

### Quick Single-Stem Assessment

For "this vocal sounds weird" — run `full_diagnostic` on that one file. But always check phase if the complaint involves how it sounds *in context* — that's the phase cancellation signature.

## Reference Materials

- [measurement-actions.md](measurement-actions.md) — complete measurement-to-action translation tables
- [mix-brief-template.md](mix-brief-template.md) — structured brief template for downstream skills
- Spectral centroid reference ranges and stem content verification rules are in measurement-actions.md

## Final Checklist (restated for attention)

1. Phase before everything — find phase problems before they waste mixing hours
2. Interpret in instrument context — crest factor, centroid, and correlation all depend on source type
3. Genre context — lo-fi noise and rolled-off highs are aesthetic, not problems
4. Don't speculate on provenance — mono in stereo is normal, don't assume AI separation
5. Processing order matters — noise removal before compression, phase before EQ
6. Handoff explicitly — tell downstream skills exactly what to do with each finding
7. Confidence always — prefix every finding with Definite/Likely/Possible so engineers know what to trust
