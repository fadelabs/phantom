# Compressor Selection, Settings & Dynamics Techniques

## Table of Contents
- Compressor Type Selection (The First Decision)
- Attack & Release Tuning Method
- Starting Settings Per Instrument
- Serial Compression
- Parallel Compression (NY Compression)
- Sidechain Compression
- De-Essing
- Gain Reduction Targets
- The Bypass Test

---

## Compressor Type Selection (The First Decision)

The type determines character before you touch any knob. A VCA will never sound like an optical regardless of settings. Start by asking "what character do I want?"

| Type | Harmonic Character | Best For | NOT For |
|------|-------------------|----------|---------|
| **Opto** (LA-2A style) | Minimal coloration, warm | Vocals, bass, strings, gentle level control | Fast transients (drums), heavy low-end material (causes pumping) |
| **FET** (1176 style) | Odd-order harmonics, colorful | Drums, vocals needing attitude, room mics, parallel buses | Mix bus (too aggressive), transparent control (always adds color) |
| **VCA** (SSL/dbx style) | Transparent, clean | Drum bus, mix bus, precision work, peak-heavy material | When you want warmth or character (tends clinical) |
| **Vari-Mu** (Fairchild style) | Even-order harmonics, fat | Mix bus, subgroups, master bus warmth, glue | Solving dynamic problems (too slow), adding punch (softens transients) |
| **Digital** (stock DAW) | None | Surgical precision, anything needing exact control | When you want tonal character |

---

## Attack & Release Tuning Method

Attack and release shape the sound more than ratio. Don't leave them on defaults.

### The Procedure

1. Start with attack fully slow and release fully fast
2. Decrease attack until the high-frequency transient begins to dull, then back off slightly — you've found the sweet spot where the transient passes through but the body is controlled
3. Increase release until the gain reduction meter recovers just before the next musical event (beat, note, phrase) — the compressor should breathe with the song's pulse
4. If release is too fast: audible pumping/distortion. Too slow: cumulative gain reduction sucks life out of the track.

### By Musical Timing

| Musical Value (at tempo) | Use For |
|--------------------------|---------|
| 1/64 note attack | Drums (catches just enough without killing punch) |
| 1/16 note attack | Vocals (allows consonant transients through) |
| 1/16 note release | Drums (recovers between hits) |
| 1/4 note release | Vocals, bass (recovers between phrases) |
| Auto release | Mix bus (adapts to varying density) |

### Attack/Release by Intent

| Goal | Attack | Release | Result |
|------|--------|---------|--------|
| Maximum punch | Slow (30-50 ms) | Fast enough to recover before next hit | Transient preserved, body controlled |
| Smooth control | Fast (1-10 ms) | Medium (100-200 ms) | Even dynamics, less punch |
| Sustain emphasis | Fast (1-5 ms) | Slow (200-500 ms) | Attack reduced, sustain brought forward |
| Breathing/pumping | Medium (10-20 ms) | Timed to tempo | Musical compression artifact (intentional in EDM) |

---

## Starting Settings Per Instrument

| Instrument | Type | Ratio | Attack | Release | GR Target | Key Notes |
|-----------|------|-------|--------|---------|-----------|-----------|
| Kick | FET or VCA | 4:1 | 10-30 ms | 50-100 ms | 3-6 dB | Slow attack = punchy. Fast attack = pillowy. |
| Snare | FET | 4:1-6:1 | 5-15 ms | 50-100 ms | 3-6 dB | Slow attack (15ms+) preserves crack. Long release emphasizes sustain/fatness. |
| Drum bus | VCA | 2:1-4:1 | 10-30 ms | Auto or 100-300 ms | 2-4 dB | Glue, not squash. Should make drums feel like one instrument. |
| Bass | Opto or FET | 3:1-8:1 | 20-40 ms | 100-200 ms | 3-6 dB | Opto for smooth. FET for punch. May need limiting (8:1+) for immovable foundation. |
| Lead vocal | Opto → FET (serial) | 3:1-4:1 each | 10-30 ms | 50-150 ms | 2-3 dB each stage | Serial preferred. See Serial Compression section. |
| Acoustic guitar | Opto | 2:1-3:1 | 20-40 ms | 100-200 ms | 2-4 dB | Gentle. Don't kill dynamics — that's the instrument's expression. |
| Electric guitar | VCA or FET | 3:1-4:1 | 10-20 ms | 50-100 ms | 2-4 dB | Already compressed by amp. Light touch unless very dynamic clean parts. |
| Mix bus | VCA or Vari-Mu | 1.5:1-2:1 | 10-30 ms | Auto or 300 ms | 1-3 dB | Glue not squash. More than 3 dB on the bus = too much. Start early in the mix. |
| Room mics | FET | 4:1-10:1 | 5-15 ms | 50-200 ms | 6-20 dB | Heavy = bigger room sound. Only works if the room sounds good. |

---

## Serial Compression

Two gentle compressors (2-3 dB GR each) instead of one heavy one (6 dB). Each does less work, fewer artifacts, two characters working together.

**Standard vocal serial chain:**
1. **Opto** (LA-2A style): Slow, smooth, catches the broad dynamic envelope. 3:1, 2-3 dB GR. Leveling.
2. **FET** (1176 style): Faster, catches remaining peaks. 4:1, 2-3 dB GR. Peak control.

**Alternative for bass with harsh pick transients:**
1. **Limiter** (fast attack, fast release): Catches only the pick transients. 8:1+, 2-3 dB GR.
2. **Opto** (medium attack, medium release): Controls overall level. 3:1, 3-4 dB GR.

---

## Parallel Compression (NY Compression)

Dry signal preserves transients. Heavily compressed signal adds sustain and body. Blend for the best of both.

**Setup:**
1. Send source to a parallel bus (pre-fader send)
2. On the parallel bus: compress hard — 10:1+, fast attack (1-5 ms), medium release (50-100 ms), 10-15 dB gain reduction
3. Blend parallel bus at -10 to -6 dB below the dry signal
4. Adjust until you feel density increase without hearing obvious compression

**The NYC trick (expanded):** On the compressed return, add 6-10 dB boost at 100 Hz and 10 kHz via EQ. This is what makes NYC compression sound bigger/punchier than standard parallel — the EQ on the crushed signal adds weight and air without affecting the dry signal's transients.

**Best for:** Drums (most common), vocals, bass, full drum bus.

**Caution:** Heavy compression raises the noise floor. Gate or noise-reduce the source before the parallel send.

---

## Sidechain Compression

### Frequency-Dependent Sidechaining (Kick/Bass)

Don't duck the whole bass — that kills midrange presence. HPF the sidechain input so only sub frequencies duck.

**Setup:**
1. Send kick to bass compressor's sidechain input (Reaper: channels 3-4)
2. Set compressor detector input to sidechain
3. Add HPF at 80-100 Hz on the sidechain input (compressor only responds to kick's sub energy)
4. Fast attack (1-5 ms), fast release (50-100 ms), 2:1-3:1 ratio

Run `analyze_masking` between kick and bass first — the masking analysis tells you exactly which frequency bands fight, so you set the sidechain filter precisely.

### Beyond Kick/Bass

| Source → Target | Amount | Purpose |
|----------------|--------|---------|
| Vocal → Guitar bus | 1-2 dB, slow attack | Guitars subtly yield to vocal phrases |
| Vocal → Reverb return | 3-6 dB, medium attack | Reverb ducks during singing, blooms in gaps |
| Kick → Synth pad | 3-6 dB, fast attack | Rhythmic pumping (intentional in EDM, subtle elsewhere) |
| Kick → Bass (sub only) | 3-6 dB, fast attack | Low-end clarity without killing bass midrange |

---

## De-Essing

### Placement

De-ess BEFORE compression in the signal chain. If you de-ess after compression, the compressor has already amplified sibilance, making the de-esser work harder and less transparently.

### Procedure

1. Solo the vocal and identify where sibilance lives (typically 4-8 kHz — varies per singer)
2. Set de-esser frequency to that zone
3. Lower threshold until S sounds are reduced but still natural — completely eliminating them sounds like a lisp
4. Validate in full-mix context (not solo)

### Multi-Band De-Essing

Some vocalists have sibilance at multiple frequency points. A dynamic EQ with 2-3 targeted bands (each with its own threshold) is more effective than stacking multiple single-band de-essers.

---

## Gain Reduction Targets

| Amount | Character | Typical Use |
|--------|-----------|-------------|
| 1-3 dB | Subtle tonal shaping, barely audible | Mix bus glue, gentle leveling |
| 3-6 dB | Noticeable control, character changes | Standard vocal/instrument work |
| 6-10 dB | Heavy, compressor clearly audible | Room mics, aggressive drums, parallel sends |
| 10-20 dB | Extreme, deliberate effect | Crushed room mics, NYC compression, "all buttons" sound |

---

## The Bypass Test

**Before committing to any compression setting:**

1. Match the output level to the bypassed input level (use makeup gain)
2. A/B with the compressor bypassed
3. Ask: "Is this actually better, or just louder?"

Louder always sounds "better" to human ears. If you don't level-match before comparing, every compression setting sounds like an improvement because it adds makeup gain. This single habit prevents more bad compression decisions than any other technique.
