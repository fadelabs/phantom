# Audio Diagnostician Skill -- Deep Research Audit

**Date:** 2026-05-02
**Scope:** Gaps, errors, and improvements for SKILL.md
**Sources:** MCP server code analysis, audio engineering fact-check (web sources), cross-skill structural analysis

---

## Errors (fix these)

### E1. True peak dealbreaker threshold is wrong

**Current:** "True peak > 0 dBTP" = dealbreaker

**Problem:** The industry standard maximum is **-1 dBTP**, per EBU R128, ATSC A/85, and every major streaming platform (Spotify, Apple Music, YouTube). Lossy codec encoding (MP3, AAC, Ogg) can increase peaks by up to 1 dB during transcoding. A file at 0 dBTP is already past the professional threshold.

**Fix:** Dealbreaker at > -1 dBTP for distribution-ready material. For raw stems pre-mixing, 0 dBTP is the hard clip line, but -1 dBTP should be flagged as "significant" (tight headroom). The measurement-actions.md already has "> -1 dBTP = near clipping, watch headroom" but SKILL.md severity triage doesn't use it.

**Sources:** EBU R128, Waves mastering guide, Mixing Lessons, SoundBoost

### E2. "Phase problems can't be fixed with EQ, compression, or any amount of processing" is misleading

**Current:** "They can't be fixed with EQ, compression, or any amount of processing."

**Problem:** Phase problems CAN be fixed with specific processing: time alignment (sample-level nudging), polarity flip, phase rotation plugins (Waves InPhase, Sound Radix Auto-Align), and linear-phase EQ. What's true: standard EQ and compression can't fix them and may worsen them.

**Fix:** Rewrite to: "They can't be fixed with EQ or compression -- they require specific phase tools: polarity flip, time alignment, or phase rotation plugins. Standard mixing processing may actually worsen phase issues."

**Sources:** iZotope "5 Ways to Adjust Phase After Recording", Waves phase tips, Production Expert

### E3. Mastering send-back EQ threshold is too lenient

**Current:** "if you'd need more than 4 dB of corrective EQ anywhere"

**Problem:** The widely cited industry guideline is **2-3 dB**, not 4 dB. Multiple mastering engineers and sources confirm 3 dB as the standard limit. 4 dB is more lenient than professional practice.

**Fix:** Change to 3 dB. "If you'd need more than 3 dB of corrective EQ anywhere, it needs more mix work, not mastering."

**Sources:** Waves "10 Tips for Effective EQ in Mastering", Mastering The Mix, Yoad Nevo

---

## Threshold Inconsistencies Between SKILL.md and measurement-actions.md

### I1. SNR thresholds -- SKILL.md skips ranges

**SKILL.md:** >70 dB = Professional, 50-60 dB = Acceptable, <40 dB = Poor

**measurement-actions.md:** >70 dB = Professional, 60-70 dB = Good, 50-60 dB = Acceptable, 40-50 dB = Poor, <40 dB = Unacceptable

SKILL.md skips the 60-70 dB "Good" range entirely and labels <40 dB as "Poor" when measurement-actions.md calls it "Unacceptable." The 40-50 dB "Poor" tier is absent. An agent using only the quick reference table won't flag 40-50 dB stems correctly.

### I2. Noise floor -- SKILL.md collapses a 3-tier range into 1

**SKILL.md triage:** "Noise floor above -50 dBFS" = Significant

**measurement-actions.md:** Below -70 dBFS = Clean, -60 to -50 dBFS = Audible in quiet passages, Above -50 dBFS = Significant

Stems with noise floors between -60 and -50 dBFS aren't flagged by SKILL.md's triage despite measurement-actions.md recommending "gate or noise reduce in quiet sections" for this range.

### I3. Phase correlation -- SKILL.md merges two distinct ranges

**SKILL.md:** +0.3 to +0.8 = "acceptable, monitor during mixing"

**measurement-actions.md:** +0.5 to +0.8 = "Good, normal stereo content", +0.3 to +0.5 = "Wide stereo, approaching risky -- check on mono playback"

A stem at +0.35 correlation is a very different situation than one at +0.75, but SKILL.md treats them identically.

---

## High-Impact Gaps

### G1. Bit depth mismatch not checked

The skill halts on sample rate mismatches but never checks for bit depth mismatches. The mix brief template has a singular "Bit depth" field, implying one value for the whole session. Stems can arrive at 16-bit, 24-bit, and 32-bit float mixed together. Downconverting 32-bit float to 16-bit without dither introduces quantization noise. The session-architect reads this field to configure the project -- if it's wrong, the session gets set up wrong.

### G2. Stem duration/start-time alignment not checked

No step checks whether stems have matching lengths or aligned start times. Stems frequently arrive with different head/tail silence or different export lengths. The `detect_problems` tool mentions "start/stop cut detection" but SKILL.md never tells the diagnostician to interpret or report these as alignment issues. The mix brief has a single "Duration" field with no per-stem duration.

### G3. Silence/near-silence stems not detected

The workflow never flags a stem that is effectively empty (-70 dBFS or below throughout). A silent stem is either an export mistake or a room tone track included unintentionally. Sending it through the full downstream workflow wastes processing.

### G4. Combined headroom assessment missing

True peak is checked per stem, but what happens when all stems sum is never assessed. A collection of stems each at -3 dBTP could easily sum to +6 dBTP on the mix bus. The mix-engineer needs to know the aggregate headroom situation for gain staging decisions.

### G5. Effects-engineer handoff not defined

The mix brief is documented as handoff to "mix-engineer" and "session-architect" only. The effects-engineer makes spatial processing decisions (reverb, delay, stereo width) that are directly affected by masking data and stereo width, but no formal handoff is defined.

### G6. Mastering send-back criteria not fully pre-checked

The mastering-engineer has five specific send-back criteria. The pre-mastering check mentions two (4 dB EQ and balance) but doesn't systematically check all five: corrective EQ needed, fundamental balance, severe phase (<+0.3), baked-in clipping, excessive noise.

---

## Medium-Impact Gaps

### G7. Tempo/BPM detection absent

No step detects or reports tempo. The session-architect needs it for grid alignment and click track. The effects-engineer needs it for tempo-synced delays and modulation. Every downstream skill independently needs BPM but the diagnostician never establishes it.

### G8. Mid-side encoded recordings not addressed

The diagnostician never checks whether a stem is mid-side encoded rather than standard L/R stereo. An M/S file imported as stereo would measure oddly (weird correlation patterns) but the skill has no guidance for identifying this as the cause.

### G9. Stem naming vs content verification missing

The skill never suggests verifying that filenames match actual content. A file named "kick.wav" containing bass guitar would silently corrupt every downstream decision -- the masking map, bus routing, and processing choices would all be wrong. A spectral centroid check against expected range for the named instrument would catch obvious mismatches.

### G10. Click/metronome track detection missing

No check for accidentally included click tracks. A click exported as a stem (regular transients at consistent frequency with perfectly even spacing) is a common mistake that would contaminate masking analysis and processing decisions.

### G11. Multiple takes not handled

When a user provides alternate takes of the same part, the diagnostician runs analysis on all equally and includes all in the masking map. Three vocal takes would show massive masking with each other, creating misleading results. The skill should detect likely alternate takes (by filename or correlation) and advise selection before proceeding.

### G12. DC offset recommendation is incomplete

**Current:** "remove with HPF before processing"

Most DAWs have a dedicated DC offset removal function (mean subtraction) that is more precise than HPF. HPF can attenuate wanted low-frequency content or introduce phase shift depending on cutoff and filter type.

**Better:** "Remove with dedicated DC offset removal tool (available in most DAWs and iZotope RX), or if unavailable, use an HPF set very low (5-20 Hz)."

---

## Low-Impact Gaps

### G13. Spectral centroid lacks numeric guidance

SKILL.md says "unusually low" and "unusually high" but never defines what "unusual" means numerically. Without reference ranges (e.g., typical vocal centroid 1-3 kHz), the agent has to guess.

### G14. Dynamic complexity undefined

measurement-actions.md includes "Dynamic complexity: High -- consider multiband compression" but never defines what "high" means. SKILL.md doesn't mention dynamic complexity at all.

### G15. Loudness range (LRA) missing from quick reference

measurement-actions.md defines LRA interpretation (>15 LU = very dynamic, 7-12 LU = pop/rock, <5 LU = EDM) but SKILL.md quick reference omits it, and the per-stem table doesn't include it.

### G16. Per-stem stereo width missing from mix brief

The per-stem table includes phase correlation but not stereo width. The effects-engineer and mix-engineer both need starting width for stereo processing decisions.

### G17. Genre not always proactively asked for

The "Compare to a reference" step says "if the genre is known" but never guides the agent to ask about genre if the user hasn't mentioned it. Downstream skills need this.

### G18. Crest factor labels are source-dependent

The >15 dB = "uncompressed" label is reasonable for drums but a legato string quartet naturally sits at 6-8 dB without compression. The label needs a note about source material dependency.

### G19. Negative phase correlation oversimplified

"Negative = likely polarity inversion" should be "negative = possible polarity inversion (sustained near -1 = definite inversion; occasional dips are normal with wide stereo content)."

### G20. Mains hum -- dominant frequency often doubled

The dominant hum frequency is often 2x mains (100/120 Hz) because magnetic force is proportional to current squared. The harmonic series is correct but should note this.

---

## MCP Tool Alignment (mostly good news)

The skill's tool references are **accurate**. All tool names, usage patterns, and behavioral descriptions match the actual server implementation. Specific notes:

- `batch_diagnostic` correctly described as running all 6 analysis types and checking sample rate mismatches
- `compare_phase` correctly used for multi-mic pair analysis; implementation uses GCC-PHAT with 50ms search window
- `multi_stem_masking` max 20 stems (not mentioned in skill, should be noted)
- `detect_problems` actually runs 11 detectors including lossy codec detection (not mentioned in skill's triage)

**CLAUDE.md has tool list errors** (not in the skill itself): lists `setup_reaper` and `analyze_masking_matrix` as MCP tools (they're not), omits `list_profiles` and `load_profile` (which are). This should be fixed in CLAUDE.md.

---

## Priority Summary

| Priority | Count | Items |
|----------|-------|-------|
| Errors (fix now) | 3 | E1 true peak, E2 phase wording, E3 send-back threshold |
| Inconsistencies (harmonize) | 3 | I1 SNR, I2 noise floor, I3 phase correlation |
| High-impact gaps | 6 | G1-G6 (bit depth, alignment, silence, headroom, effects handoff, mastering pre-check) |
| Medium-impact gaps | 6 | G7-G12 (tempo, M/S, naming, click, takes, DC offset) |
| Low-impact gaps | 8 | G13-G20 |
