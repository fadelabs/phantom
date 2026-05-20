---
name: mix-engineer
description: >
  Professional mixing methodology for audio engineering. Guides through
  pre-mix analysis, phase checking, gain staging, EQ decisions,
  compression selection, spatial processing, and automation. Encodes
  the decision-making process of a senior mix engineer backed by
  Phantom MCP measurement tools. Use this skill whenever the user
  wants to mix stems or tracks, balance a mix, make EQ or compression
  decisions, set up signal chains, choose compressor types, solve
  frequency conflicts between instruments, set up spatial processing
  (reverb, delay, panning), automate volume or effects, or compare
  their mix against a reference. Also use when the user mentions
  muddy mixes, harsh frequencies, buried vocals, kick/bass conflicts,
  or any mixing problem -- even if they don't say "mix" explicitly.
---

# Mix Engineer

> **Workflow position:** diagnostician → session-architect → **mix-engineer** → effects-engineer → mastering-engineer

Every mix decision is measurement-informed. "Sounds muddy" becomes "4 dB buildup at 300 Hz across bass and guitars" via `analyze_spectrum`. That specificity solves problems in one move instead of hours of guessing.

**Non-negotiable rules:**
1. Check phase before EQ — phase problems masquerade as tonal problems
2. EQ for balance, not tone — make things fit *together*, not sound good solo'd
3. Cut before boost — subtractive EQ first, additive only for character
4. Bypass-test at matched levels — louder always sounds "better," remove that bias
5. Monitor at conversation volume for final balance decisions

## Phase 1: Pre-Mix Assessment

### 1. Hear the Intention

Listen to the rough/reference before touching a fader — it represents the artist's intention. Note the focal point, energy, and what to preserve. Then form your vision: overall size, depth, and feel of the finished mix. A clear target prevents aimless tweaking.

### 2. Run Diagnostics

Read the diagnostician's mix brief if available, or run `full_diagnostic` / `batch_diagnostic`.

**Crest factor guide:** Above 15 dB = very dynamic (handle gently), 8-12 dB = normal (standard processing), below 6 dB = already over-compressed (no more compression — use transient shaper or parallel clean blend instead).

**Printed effects detection:** If crest factor is low AND spectrum shows reverb tail energy or modulation artifacts, the stem has printed effects. Do NOT layer more of the same — adjust EQ around the existing character. For dynamic control on crushed stems, use a transient shaper (attack +2-4) or blend 30-50% clean parallel copy to restore dynamics.

### 3. Phase Check (Always Before EQ)

Run `analyze_phase` on every stereo stem. Flip polarity if `polarity_inverted: true`. For multi-mic recordings, `compare_phase` between close and room mics.

**Phase vs EQ decision:** "Sounds fine solo but thin in context" = phase cancellation, not an EQ problem. If correlation is below +0.5 between related mics, fix phase first — no amount of EQ fixes destructive interference. Only move to EQ once correlation is above +0.7. **Success test:** correlation above +0.7 on all related mic pairs.

### 4. Gain Staging

Set all faders to unity. Use clip/item gain to target -18 dBFS average (0 VU = -18 dBFS — where analog-modeled plugins are calibrated). Reserve faders for mix balance only.

**Inter-plugin gain staging:** After each plugin in the chain, verify output level matches input level (±1 dB). Plugins that add gain shift the operating point of everything downstream. Use a gain utility after any plugin that adds more than 2 dB. This prevents cascading saturation and keeps every plugin in its designed sweet spot.

**Quick-start balance:** Pink noise at -10 dBFS, bring each fader up until it just masks the noise (frequency-aware balance in minutes). Or: hero-element-first — start with the focal element, build around it.

## Phase 2: Processing

### Arrangement Priority Framework

When elements conflict, higher-priority keeps its space; lower yields:

1. **Lead vocal / primary melodic hook** — never yields
2. **Snare / kick** — rhythmic backbone
3. **Bass** — foundation
4. **Lead instrument / solo** — contextual (only when featured)
5. **Rhythm guitars / keys** — support
6. **Pads / textures** — fill
7. **Room mics / ambience** — lowest priority

This hierarchy drives EVERY masking decision: who gets cut, who gets panned away, who gets sidechained.

### Signal Chain Order

1. **HPF** — roll off below where the instrument contributes (see [frequency-map.md](frequency-map.md))
2. **Gate** — remove noise between phrases (drums, guitar amps)
3. **De-esser** — tame sibilance BEFORE compression (compression amplifies sibilance)
4. **Subtractive EQ** — cut problems (narrow Q, surgical)
5. **Compression** — control dynamics (type selection below)
6. **Additive EQ** — shape tone (wide Q, musical)
7. **Saturation** — add warmth/harmonics (adds presence without phase shift)
8. **Sends** — reverb, delay, parallel processing

**Exception — extreme dynamics (25+ dB range):** When a source has wild dynamic swings, EQ before compression produces inconsistent results because the compressor sees different spectral content at different levels. In this case, compress first to tame dynamics, then EQ the stabilized signal. Or use dynamic EQ which adapts automatically.

**Compression/EQ interaction:** Remember that EQ changes alter what the compressor "sees." A 3 dB boost at 3 kHz feeds more energy to the compressor at that frequency, potentially triggering more gain reduction. After any EQ change, re-check your compressor's gain reduction — if it changed by more than 1 dB, re-adjust the threshold.

### EQ Decision-Making

**Core principle:** EQ's job is making things fit *together*, not sound good solo'd. Evaluate all EQ in full-mix context.

**The finite space rule:** Arrangement density determines EQ aggressiveness. Sparse mix (4-5 elements) = gentle filtering. Dense mix (40+ tracks) = aggressive carving on every element. This isn't preference — it's physics.

**Three-way frequency conflicts:** When three or more sources pile up in the same range (e.g., kick + bass + synth pad at 60-200 Hz), pairwise EQ cuts cascade into cumulative thinness. Instead: assign each source a narrow "home" band within the shared range (kick 50-80, bass 80-140, pad 140-200), cut each outside its home, and verify the combined result on the mix bus. For three-way midrange conflicts (guitars + keys + vocal at 2-4 kHz), use the Priority Framework: highest-priority element keeps its range untouched, second priority gets a narrower window, lowest gets cut or panned away.

**Cumulative thinning:** After applying HPF + subtractive EQ across many tracks, the overall mix can lose body. Every 5-6 tracks processed, check the mix bus for accumulated thinness at 200-400 Hz. If present, ease HPF slopes (24→12 dB/oct) or reduce cut depths by 1-2 dB on least-offending tracks.

**HPF everything except kick and bass.** See [frequency-map.md](frequency-map.md) for per-instrument HPF points.

| Situation | Action |
|-----------|--------|
| Track masks something more important | Complementary EQ: cut conflict frequency on the LOWER-PRIORITY element |
| Problem is constant throughout the song | Static EQ (narrow cut) |
| Problem appears only in certain sections | Dynamic EQ (threshold-triggered) |
| "Sounds thin in context" | Check phase FIRST, then check competing instruments |
| Vocals buried | See Buried Vocal Diagnostic below |
| Need presence but EQ isn't working | Try saturation instead |
| Boost needed > 3 dB | Find and cut the problem elsewhere |

**Bandwidth rule:** Narrow Q (8-12) for cuts, wide Q (0.5-2) for boosts. Narrow boosts sound ringy.

**Complementary EQ workflow:** `analyze_masking` between two instruments, cut the less important one at the collision frequency, round-robin through all competing pairs. **Success test:** re-run `analyze_masking` — overlap energy should drop by at least 3 dB at the conflict frequency.

**Buried Vocal Diagnostic Sequence:**
1. Run `analyze_masking` between vocal and each instrument — identify which element(s) mask the vocal and at what frequency
2. Check vocal compression — if gain reduction exceeds 6 dB, the compressor is pulling the vocal down during loud passages. Reduce ratio or raise threshold by 2-3 dB
3. Cut competing instruments at 2-4 kHz by 2-3 dB (preferred over boosting vocal)
4. **If cutting exposes printed reverb artifacts:** fallback chain — automate the competing instrument's level down 2-3 dB in problem sections, or use frequency-selective sidechain (compress guitars at 2-4 kHz triggered by vocal), or accept a gentler 1 dB cut + vocal automation instead
5. If still buried: automate vocal up 1-2 dB in dense sections rather than processing harder
6. Last resort: 1-2 dB shelf at 3-5 kHz on vocal with simultaneous 1 dB cut on bus at same range

For frequency ranges per instrument, problem zones, and conflict pairs: load [frequency-map.md](frequency-map.md).

### Compression

**Step 1: Choose the type** (highest-leverage decision — determines character before you touch any knob):

| Desired Character | Type | NOT For |
|------------------|------|---------|
| Punchy, aggressive, colorful | FET | Mix bus, transparent control |
| Smooth, transparent, musical | Opto | Fast transients, heavy low-end material |
| Precise, clinical, versatile | VCA | When you want warmth or character |
| Warm, glue-like, cohesive | Vari-Mu | Solving dynamic problems, adding punch |

**Step 2: Set attack and release** (shapes sound more than ratio):

| Goal | Attack | Release |
|------|--------|---------|
| Preserve punch/transients | Slow (let transient through) | Recover before next hit |
| Smooth, controlled dynamics | Fast (catches everything) | Medium-slow |
| Breathing with the music | Start slow, decrease until HF dulls, back off | Start fast, increase until recovery matches pulse |

**Step 3: Gain reduction target** — 1-3 dB for glue, 3-6 dB for standard control, 6-10 dB for heavy effect, 10+ dB for parallel/crushed. **Success test:** bypass the compressor — if the track sounds lifeless without it or pumping with it, the settings need adjustment. The compressed signal should sound like a better version of the same performance.

**Serial compression:** Opto first for envelope smoothing (2-3 dB), FET second for peak catching (2-3 dB). Total 4-6 dB with two characters working together.

**Parallel compression:** Send to aux, compress hard (10:1+, fast attack, medium release), blend at -10 to -6 dB below dry. Best for drums and vocals. Gate the source before sending — heavy compression raises the noise floor.

### Kick/Bass Conflict Resolution

Run `analyze_masking` between kick and bass. Choose approach based on conflict type:

| Conflict Pattern | Solution | When to Use |
|-----------------|----------|-------------|
| Broadband overlap (40-120 Hz) | Sidechain compression: HPF sidechain at 80 Hz, ratio 3:1, fast attack, release synced to tempo | Kick and bass occupy same octave |
| Narrow collision (single freq ±10 Hz) | Dynamic EQ on bass at collision freq, triggered by kick | Precise conflict, bass tone otherwise fine |
| Tonal mud (both lack definition) | Complementary static EQ: kick owns 50-80 Hz + 3-5 kHz click; bass owns 80-150 Hz + 700-1000 Hz growl | Instruments need permanent frequency homes |
| Phase-related cancellation | Time-align bass to kick (align transients within 1 ms) | Waveforms cancel when summed |

Try solutions in this order: time alignment → complementary EQ → dynamic EQ → sidechain. Use the least intervention that solves the problem.

For per-instrument settings and starting values: load [compressor-guide.md](compressor-guide.md).

### Spatial Processing

**Panning framework:**
- Center: lead vocal, kick, bass, snare (anchors)
- Hard L/R: use sparingly — stacking everything wide creates "big mono"
- Focused stereo: pan to specific positions (9-11 / 1-3 o'clock) for localization
- **Panning and masking interact:** same-position instruments mask more than panned-apart ones. When EQ alone can't solve a masking conflict, try 5-10 degrees of pan separation first — it's less destructive than more EQ cuts

**Reverb type selection:**

| Type | Character | Best For |
|------|-----------|----------|
| Room | Short, natural, intimate | Drums, keeping things grounded |
| Plate | Smooth, dense, vocal-friendly | Vocals, snare, melodic instruments |
| Hall | Long, spacious, grand | Strings, pads, special moments |
| Spring | Twangy, lo-fi, character | Guitar, vintage vibes |

**Tempo-aware reverb:** Pre-delay = `60000 / BPM / 64` ms (120 BPM → 8 ms). Max decay = `60000 / BPM × 2` ms (120 BPM → 1000 ms) — tail must die before the next snare hit. For faster songs, use quarter-note: `60000 / BPM` ms. **Density adjustment:** above 8 simultaneous elements, multiply BPM-derived decay by 0.6 or reverb accumulates into mud.

**Reverb density vs spatial cohesion conflict:** When a song needs denser reverb in choruses but it's washing out definition — automate reverb RETURN LEVEL (not decay time), use ducked reverb (sidechain the reverb return to the dry vocal so reverb drops during singing), or crossfade between separate verse/chorus reverb sends with different densities.

**Front-to-back depth:** Close = dry (send ≤ -20 dB), bright, full level. Mid = moderate send (-12 to -8 dB), LPF 10-12 kHz, -2 to -4 dB. Far = wet (send ≥ -6 dB), LPF 6-8 kHz, -6 dB+. Pre-delay: 0-5 ms = distant, 15-30 ms = present. **Success test:** close your eyes — can you point to where each element sits front-to-back?

**EQ reverb returns:** HPF 200-600 Hz, LPF 6-10 kHz. Darken to blend, brighten to feature.

**Delay:** Slapback (50-120 ms) for thickening, dotted-eighth for rhythmic interest. HPF delay return at 200-300 Hz to prevent low-end buildup.

Run `analyze_stereo` after spatial processing. If correlation drops below +0.3, you've over-widened.

### Automation

**Vocal riding** is the single most transformative mixing skill. Automate word-by-word: whispered words +2-3 dB, belted notes -1-2 dB, consonants at phrase starts +1 dB. **Success test:** every syllable equally intelligible without audible "pumping."

**Section-boundary automation** (creates dynamic contrast):
- Verse → Chorus: raise bus +0.5-1 dB, increase send levels +2-3 dB, widen stereo elements 10-15%
- Chorus → Verse: drop bus -0.5-1 dB, pull reverb sends back, narrow stereo
- Bridge / Breakdown: drop -2-3 dB, strip effects, create contrast for the return
- Build → Drop: automate HPF sweep up over 4-8 bars, release everything at downbeat

**Per-section processing for dramatic density changes:** When verse has 4 elements and chorus has 20, static EQ/compression can't serve both. Automate bus EQ (tighten HPFs and add midrange cuts entering dense sections), adjust compression thresholds per section, or use separate signal chains switched via mute automation.

**Effects automation:**
- Delay throws: punch send to 0 dB on last word of phrase, back to -inf
- Reverb swells: +6-10 dB in gaps, pull back during dense sections
- Filter sweeps: automate HPF from 20 Hz to 500-800 Hz over 4-8 bars for builds

**Mute automation:** Clean up noise between vocal phrases, guitar rests, drum fills. Accumulated noise from idle tracks raises the floor. If a track doesn't serve the current section, mute it.

### Bus Processing

- **Drum bus:** VCA glue (2:1, slow attack, 1-2 dB GR) + subtle saturation
- **Instrument bus:** Cut 2-4 kHz by 1-2 dB to carve vocal space
- **Mix bus:** Vari-Mu or VCA at 1.5:1-2:1, slowest attack, 1-2 dB GR max. Should be on from the start of mixing — don't add it last
- **"But it sounds good without bus compression" conflict:** If you've been mixing for 3+ hours and the mix works without bus compression, don't retroactively force it. If you want to try, use minimal settings (0.5 dB GR) and A/B carefully. Undo if it doesn't clearly improve things — bus compression is a tool, not a requirement.
- **Order:** Individual tracks → subgroup buses → mix bus. Never compress a bus to fix a problem that should be solved on the individual track

## Phase 3: Verification & Finishing

### Translation Checking

Check the mix on multiple systems: **Phone** — vocal/melody audible, low-mid balance. **Earbuds** — stereo image, sibilance. **Car** — low-end, overall energy. **Laptop** — midrange clarity, hook translation.

If bass vanishes on small speakers but the artist wants "deep sub only" — this is their creative call, not yours. Inform them that sub-only bass won't translate to phone/laptop speakers, offer alternatives (10-15% saturation blend to add harmonics above 100 Hz while preserving sub character), and let THEM decide. Document the conversation.

### Finishing Checkpoints

Before calling a mix done:
1. **Groove** — feels locked in and propulsive (tap along — if you drift, the groove isn't tight)
2. **Clarity** — every element distinctly audible; every lyric intelligible on first listen
3. **Low end** — kick and bass cooperate (`analyze_masking` shows < 3 dB overlap in shared range)
4. **Focal point** — clear at every moment; nothing competes with the lead
5. **Dynamic contrast** — sections feel different (measure: chorus should be 2-4 dB louder than verse on RMS meter; quiet-to-loud range appropriate for genre)
6. **Clean** — no clicks, pops, buzz, edit glitches, or noise from idle tracks
7. **Mono compatible** — `analyze_phase` on mix bus shows correlation above +0.3; no critical element disappears in mono
8. **Translates** — holds up on phone, earbuds, car, laptop (see Translation Checking)
9. **Reference-verified** — `compare_to_reference` level-matched; extract principles (balance, dynamics, depth) from references rather than copying frequency curves across genres
10. **Plugin audit passed** — bypass all processing, re-engage only what clearly improves things; if bypassing a plugin doesn't make things noticeably worse, remove it

**Monitoring:** Final balance decisions at conversation volume (~70-79 dB). Loud checks (100 dB) only for 20-30 seconds. Mix balanced at quiet levels holds up loud — the reverse is not true. Break every 45 minutes.

For genre-specific mixing approaches: load [genre-approaches.md](genre-approaches.md).

## Reference Materials

- [frequency-map.md](frequency-map.md) — frequency ranges, problem zones, HPF points, conflict pairs
- [compressor-guide.md](compressor-guide.md) — type selection, per-instrument settings, parallel/sidechain setup
- [genre-approaches.md](genre-approaches.md) — genre-specific priorities, processing, and challenges
- [reaper-recipes.md](reaper-recipes.md) — compound Reaper operations (requires Reaper MCP server)

## Final Checklist

1. Phase before EQ — always
2. EQ for balance, not tone — evaluate in full-mix context only
3. Cut before boost — remove problems, then shape character
4. Bypass-test at matched levels — remove loudness bias
5. Monitor at conversation volume — final balance decisions happen quiet
6. Reference frequently — level-matched A/B throughout, not just at the end
