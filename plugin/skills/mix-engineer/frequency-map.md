# Frequency Map: Instruments, Problem Zones & Conflict Resolution

## Table of Contents
- Six Universal Problem Zones
- High-Pass Filter Points (Per Instrument)
- Instrument Frequency Anatomy
- Multi-Stem Conflict Resolution

---

## Six Universal Problem Zones

When something sounds wrong, check these first:

| Zone | Frequency | Excess = | Deficit = | Fix |
|------|-----------|----------|-----------|-----|
| Mud | 200-350 Hz | Thick, undefined, boomy | Thin, no warmth | Cut 2-3 dB on offending tracks (accumulates across close-miked sources) |
| Boxiness | 300-500 Hz | Cardboard, hollow, cheap | Loss of body | Narrow cut on the worst offenders (guitars, toms, room mics) |
| Honk/nasal | 800 Hz-1.5 kHz | Congested, telephone-like | Loss of midrange presence | Narrow cut if objectionable; leave if it's body |
| Harshness | 2-6 kHz | Fatiguing, sibilant, piercing | Dull, distant, buried | Dynamic EQ (problems often intermittent); check if condenser presence peaks are stacking |
| Presence | 4-6 kHz | Ear fatigue after 30 seconds | Lacks definition/clarity | Boost gently on the lead element; cut competing elements |
| Air | 10 kHz+ | Excessive brightness, hiss | Closed, unrealistic, dark | Shelf boost for openness; LPF if it's noise not content |

**Critical insight:** 200-600 Hz and 2-4 kHz accumulate fastest in dense mixes. Proximity effect creates bass buildup on every close-miked track. Condenser presence peaks at 3 kHz stack across multiple sources. Cut these zones across the session, not just on individual tracks.

---

## High-Pass Filter Points

The single most impactful EQ move. Adjust based on arrangement density — push higher in dense mixes.

| Source | HPF Point | Notes |
|--------|-----------|-------|
| Kick drum | 30-50 Hz | Only to remove sub-rumble |
| Bass guitar | 30-60 Hz | Protect the fundamental |
| Piano/keys | 60-80 Hz | Lower if the part goes deep |
| Lead vocal | 80-120 Hz | Higher for thin voices (100-120), lower for bass voices (60-80) |
| Acoustic guitar | 80-100 Hz | Higher if close-miked (proximity effect) |
| Electric guitar | 80-120 Hz | Higher for distorted (nothing useful below) |
| Strings/pads | 80-100 Hz | |
| Room/ambient mics | 100-200 Hz | Aggressive — these contribute space, not low-end |
| Toms | 60-100 Hz | Floor tom lower, rack toms higher |
| Cymbals/overheads | 200-500 Hz | For "cymbal only" sound; lower (100-200) if you want kit body |
| Hi-hat | 300-600 Hz | Aggressive — fundamental is above this |

---

## Instrument Frequency Anatomy

### Kick Drum

| Range | Character | Common Issues |
|-------|-----------|---------------|
| 30-60 Hz | Sub-feel (full-range systems only) | Rumble in untreated rooms; won't translate on small speakers |
| 60-100 Hz | Fundamental, weight, punch | Masking with bass — one must yield via complementary EQ |
| 100-250 Hz | Body, boominess | Cut to tighten — almost always too much |
| 250-600 Hz | Cardboard/box | Cut 3-5 dB for clarity |
| 2-5 kHz | Beater attack, click | Boost for definition in dense mixes |

### Snare Drum

| Range | Character | Common Issues |
|-------|-----------|---------------|
| 120-200 Hz | Body, weight | Thin if absent, boomy if excessive |
| 300-500 Hz | Boxiness | Almost always cut |
| 900 Hz-2 kHz | Crack, snap (the defining characteristic) | Boost for presence and cut-through |
| 5-10 kHz | Sizzle, wires, crispness | Bottom mic captures most |

### Bass Guitar

| Range | Character | Common Issues |
|-------|-----------|---------------|
| 40-80 Hz | Sub fundamental | Keep mono below 120 Hz |
| 80-200 Hz | Body, warmth | Fights kick at 60-100 Hz |
| 200-400 Hz | Mud zone | Cut here — the single most impactful bass EQ move |
| 600 Hz-1.2 kHz | Growl, definition, small-speaker translation | Boost for clarity in dense mixes |
| 2-4 kHz | String noise, fret buzz | Cut if distracting |

### Electric Guitar

| Range | Character | Common Issues |
|-------|-----------|---------------|
| Below 80 Hz | Rumble | HPF always — no useful content |
| 100-250 Hz | Body, warmth | Can be too thick with multiple guitars |
| 250-500 Hz | Mud, boxiness | Cut to clean up rhythm guitars |
| 2-4 kHz | Presence, bite | Fights vocals — THE critical complementary EQ zone |
| 4-6 kHz | Edge, aggression | Fatiguing if too much |
| Above 8-10 kHz | Air, noise | LPF here for distorted guitars (nothing useful above) |

### Acoustic Guitar

| Range | Character | Common Issues |
|-------|-----------|---------------|
| 100-250 Hz | Body, fullness | Proximity effect if close-miked |
| 250-500 Hz | Boxiness | Cut 2-3 dB for clarity |
| 2-5 kHz | Clarity, pick attack (sparkle zone) | Boost gently |
| 5-10 kHz | Sparkle, air | Also reveals string noise |

### Vocals

| Range | Character | Common Issues |
|-------|-----------|---------------|
| Below 200 Hz | Proximity rumble | HPF at 80-120 Hz on every vocal |
| 200-500 Hz | Body, chest resonance | Too much = muddy/thick, too little = thin |
| 800 Hz-1.5 kHz | Nasal, honk | Narrow cut if congested |
| 2-5 kHz | Presence — the money zone | Where vocals cut through. Boost vocal OR cut instruments here. |
| 5-8 kHz | Sibilance | Dynamic EQ or de-esser. Frequency varies per singer — sweep to find it. |
| 10-16 kHz | Air, breathiness | Gentle shelf boost for intimacy and expensive sheen |

**The 3 kHz trick:** Rather than boosting vocals at 3 kHz (adds sibilance), cut 3 kHz on competing instruments. Creates space for the vocal without adding harshness.

### Piano / Keys

| Range | Character | Common Issues |
|-------|-----------|---------------|
| Below 60 Hz | Sub rumble | HPF |
| 100-300 Hz | Body, warmth | Can mask bass guitar |
| 300-500 Hz | Mud | Cut for clarity in dense mixes |
| 2-5 kHz | Clarity, attack | Fights with vocals |
| 5-10 kHz | Brilliance | Can be harsh on synth patches |

### Synths

| Range | Character | Common Issues |
|-------|-----------|---------------|
| 20-60 Hz | Sub bass | Keep mono, careful not to mask kick |
| 100-300 Hz | Warmth | Context-dependent — thickens or muddies |
| 300 Hz-1 kHz | Body | Mid-heavy synths fight guitars |
| 2-5 kHz | Presence, edge | Can mask vocals — complementary EQ needed |
| 5-10 kHz | Brightness | Supersaw/pad HF content eats headroom |

---

## Multi-Stem Conflict Resolution

Run `analyze_masking` between each pair. Apply complementary EQ: cut the conflict zone on the less important element.

| Conflict Pair | Zone | Resolution Strategy |
|---------------|------|-------------------|
| Kick vs Bass | 60-100 Hz | One gets the sub, the other gets the punch. Sidechain the sustained element (bass) to the transient (kick). |
| Bass vs Guitars | 100-250 Hz | HPF guitars at 80-120 Hz. Cut bass mud at 200-400 Hz. |
| Guitars vs Vocals | 2-4 kHz | Vocals own this range. Cut guitars here — the defining mix EQ move. |
| Keys vs Guitars | 300 Hz-1 kHz | Pan separation first, then complementary midrange carving. |
| Multiple Vocals | 1-5 kHz | Slight frequency offset per voice (each harmony owns a slightly different presence peak). Different reverb sends add separation. |
| Kick vs Toms | 100-250 Hz | Cut tom body slightly, or time-gate toms so they don't overlap kick. |
| Cymbals vs Vocals | 5-10 kHz | LPF overheads aggressively if cymbals compete with vocal air. |

**When complementary EQ isn't enough:** The arrangement has a problem EQ can't fix. Use the mute button — if two elements truly can't coexist, the less important one should be absent in that section.
