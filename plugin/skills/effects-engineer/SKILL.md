---
name: effects-engineer
description: >
  Deep expertise in audio effects for sound design and mixing. Covers
  distortion/saturation taxonomy, modulation effects, time-based
  processing, creative effect chains, and effects automation. Use
  this skill whenever the user wants to choose effects, design sounds,
  build effect chains, make creative processing decisions, add warmth
  or grit (saturation/distortion), set up reverb or delay, create
  specific sonic textures (ethereal, lo-fi, massive, underwater),
  understand the science behind effects (harmonics, comb filtering,
  all-pass filters), or automate effects for dynamic transitions.
  Also use when the user asks about making something "bigger,"
  "wider," "warmer," or "more interesting" -- those are effects
  engineering questions even if they don't mention specific plugins.
---

# Effects Engineer

> **Workflow position:** diagnostician → session-architect → mix-engineer → **effects-engineer** → mastering-engineer

Effects aren't decoration — they're part of the arrangement. A well-chosen delay is an instrument. The difference between amateur and professional effects use isn't the plugins — it's intent. Define what you want before choosing the tool.

**Non-negotiable rules (repeated at end as final checklist):**
1. Define the intent before choosing the effect — "feel like a cathedral" not "add reverb"
2. Send/return effects at 100% wet — dry signal mixed in on return = comb filtering
3. Check mono after any spatial processing — if correlation drops below +0.3, rethink
4. Automate effects to breathe with the song — static effects become wallpaper

## The Three Spatial Axes

Every sound in a mix exists in three dimensions. Know which axis you're working on before choosing an effect:

| Axis | Controls | Primary Tools |
|------|----------|---------------|
| **Left-Right** (panorama) | Where on the stereo stage | Panning, stereo delay, micro-pitch detuning |
| **Front-Back** (depth) | How close or far from listener | Reverb level, pre-delay, brightness (close = dry + bright, far = wet + dark) |
| **Size** (width/bigness) | How much space the sound occupies | Reverb diffusion, chorus, stereo widening, M/S processing |

Don't reach for reverb when you actually need a pan adjustment. Don't widen when you need depth. Identify the axis first.

**When darkness ≠ distance:** The front-back axis says dark = far, but sometimes the intent is close AND warm (intimate bass vocal, warm synth pad). Saturation adds warmth and harmonic richness without the HF rolloff that signals distance. For close-but-warm: keep brightness in the 2-8 kHz presence range intact, add tube saturation for body, boost 200-300 Hz slightly to simulate proximity effect. The result should feel like the source is right in front of you, warm but not receded — verify by A/B with a truly distant (dark+quiet) element; the close-warm source should feel forward despite its tonal warmth.

## Distortion & Saturation

### Purpose-Driven Selection

| Goal | Type | Why |
|------|------|-----|
| Warmth, musical smoothness | Tube | Even-order harmonics (octaves, fifths) — consonant with the fundamental |
| Glue, gentle rounding | Tape | Compression + saturation, HF rolloff, rounded transients |
| Grit, aggression, edge | Transistor | Odd-order harmonics (thirds, sevenths) — more dissonant, hence aggressive |
| Density, weight, thickness | Transformer | Transient softening, subtle harmonics without obvious "distortion" |
| Lo-fi, retro, degraded | Bitcrusher | Aliasing artifacts, quantization — deliberately broken |

### Parallel Distortion

Don't distort the original — distort a copy and blend. Send to a parallel bus, drive hard, blend at -10 to -15 dB underneath dry. The dry retains clarity and transients; the distorted signal adds density and harmonics.

### Small-Speaker Translation via Saturation

Bass fundamentals (40-80 Hz) disappear on small speakers. Saturation generates upper harmonics that small speakers CAN reproduce. The brain infers the missing fundamental from its harmonics.

**Technique:** Multiband saturation — split at 120 Hz. Leave sub clean. Saturate mids (tube or tape). Verify with `analyze_spectrum` — new energy should appear at harmonic multiples of the bass fundamental.

For the full distortion taxonomy with DSP science: load [effect-taxonomy.md](effect-taxonomy.md).

## Modulation Effects

| Effect | Mechanism | Character | Use When |
|--------|-----------|-----------|----------|
| **Chorus** | LFO modulates delay (15-35 ms) | Width, shimmer, movement | Thickening guitars, widening synths, lush vocals |
| **Flanger** | Same as chorus but 1-5 ms | Jet sweep, metallic, comb filtering | Dramatic sweeps, transitions, guitar solos |
| **Phaser** | All-pass filters (not delay-based) | Subtler than flanger, organic notch sweep | Synths, guitars, funky movement |
| **Tremolo** | Amplitude modulation | Pulsing, rhythmic volume | Guitar atmosphere, synth pads, vintage organ |
| **Vibrato** | Pitch modulation | Wobble, seasick | Essentially 100% wet chorus — use sparingly |

### Micro-Pitch Detuning for Width

Duplicate a signal, pitch-shift one copy +7 cents and the other -7 cents, add 10-20 ms delay to each, pan L/R. Creates natural width without the phase problems of Haas effect. Check with `analyze_stereo` — correlation should stay above +0.3.

**When mono check fails (correlation below +0.3):** Troubleshoot in order. (1) Reduce detuning to +/- 4 cents — target: correlation rises to +0.2-0.3. (2) Shorten delay to 5-8 ms — target: comb-filter nulls move above audible range. (3) Add dry center copy at -6 dB to anchor phase — target: correlation above +0.3. (4) If still failing, switch to short stereo chorus (rate 0.3 Hz, depth 30%, mix 25%) — continuous modulation avoids static phase nulls. After each step, re-check with `analyze_stereo` and listen in mono — success means the source retains its body and presence, not just hitting a number.

**When creative intent demands extreme width (correlation well below +0.3):** Sometimes the brief IS "impossibly wide, wrap around the listener's head." Don't fight it — serve it with a safety net. Create two versions on parallel buses: (1) the full-width version with no mono compromises, routed to stereo/headphone output, and (2) a mono-safe version (less detuning, center anchor) routed to a "broadcast" output. Tag both in the session. The producer gets their vision on stereo playback; the mix doesn't collapse on phone speakers.

## Reverb

### Step 1: Define the Purpose

Reverb serves five distinct purposes. Know which one you need — they often conflict (you want blend but not distance, size but not mud). **Before adding reverb, assess what the recording already has:** solo the dry track and listen for existing room sound. A dry studio recording is a blank canvas — add freely. A live room recording already has spatial information; adding more creates a confused double-space. For live recordings: match the existing room character with a short algorithmic reverb, or skip reverb entirely and use delay for depth.

| Purpose | What It Does | How to Achieve |
|---------|-------------|---------------|
| **Blend** | Makes overdubbed tracks sound like one room | Short decay, shared reverb across elements |
| **Size** | Makes the space feel larger | Longer decay, higher diffusion |
| **Depth** | Pushes sound further from listener | More reverb = further back. Less = closer. |
| **Sustain** | Extends decay of short sounds | Medium decay, moderate mix level |
| **Spread** | Distributes across stereo field | Wide stereo reverb, high diffusion |

### Step 2: Choose the Type

| Type | Decay | Best For | Pre-Delay |
|------|-------|----------|-----------|
| Room | 0.3-1.5s | Drums, percussion, grounding close-miked tracks | 0-15 ms |
| Plate | 1-3s | Vocals, snare, melodic instruments | 20-40 ms |
| Chamber | 1-2s | Orchestral, jazz, warm pop | 20-40 ms |
| Hall | 2-6s | Strings, pads, special moments, transitions | 30-60 ms |
| Spring | 0.5-2s | Guitar, surf rock, vintage | 0-10 ms |

**Algorithmic vs convolution:** Algorithmic reverbs use math — low CPU, adjustable parameters, better for creative work where you tweak decay/size in real time. Convolution reverbs sample real spaces — realistic but CPU-heavy, fixed character, and add latency from the IR length. Choose convolution for realism on a final pass; choose algorithmic for everything else.

### Step 3: Set the Two Parameters That Matter Most

**Pre-delay:** Time to song tempo (1/64 or 1/128 note at BPM). 10-40 ms preserves dry attack while adding space. No pre-delay = source sounds stapled to the back wall. 60-120+ ms = source stays very upfront with reverb clearly separated behind it.

**Pre-delay BPM calculation:** Use 60,000 / BPM / 64 for a 1/64-note pre-delay. At 140 BPM: 1/64 = ~6.7 ms, so 1/16 (four 1/64 notes) = ~27 ms. For a vocal plate at 140 BPM that should sound upfront, set pre-delay to ~27 ms — long enough to preserve the dry transient, short enough to stay connected. At 120 BPM: 1/16 = ~31 ms. At 90 BPM: 1/16 = ~42 ms. Verify by soloing the reverb return — if you can hear distinct syllables in the tail, the pre-delay is doing its job.

**Decay:** Time so the tail dies just before the next snare hit (or the one after). Reverb that overlaps the next transient creates mud. **Verification:** Solo the reverb return and play through a verse — the tail should decay to silence before each new phrase or transient. If the tail sustains when the next hit arrives, shorten decay or increase damping.

### Step 4: EQ the Reverb Return

The most overlooked reverb technique. Raw reverb is often muddy (too much low end) or harsh (too much high end):

| Application | HPF | LPF | Notes |
|-------------|-----|-----|-------|
| Vocals | ~200 Hz | ~10 kHz | Scoop at 2 kHz keeps consonants clear |
| Instruments | ~600 Hz | ~10 kHz | The classic "smooth" curve |
| Drums | ~600 Hz | 4-6 kHz | Aggressive HF rolloff keeps ambience invisible |

**Principle:** Darken reverb to blend it in. Brighten to make it stand out.

### Reverb Anti-Patterns

- Too much reverb on too many sources → distant, washy mix with no impact
- Same reverb settings on everything → one blob in a room, no spatial separation
- Ignoring mono → cheap reverbs phase-cancel in mono, thinning the mix

## Delay

### Timing to the Song (BPM → ms)

Tempo-synced delays blend almost invisibly. Untimed delays stick out as deliberate effect.

**The math:**
- Quarter note (ms) = 60,000 / BPM
- Eighth = quarter / 2
- Dotted value = straight × 1.5
- Triplet value = straight × 0.667

**At 120 BPM:** Quarter = 500 ms, eighth = 250 ms, dotted eighth = 375 ms, sixteenth = 125 ms

Dotted eighth and triplet delays often feel better than straight values — they create subtle syncopation that adds groove without feeling mechanical. **Verification:** Tap along with the delay repeats — if they reinforce the groove (you naturally tap on them), the timing works. If repeats fight the rhythm (you hesitate or mis-tap), try the next subdivision up or down.

### Delay Type Selection

| Type | Timing | Character | Use |
|------|--------|-----------|-----|
| Slapback | 50-120 ms, 1 repeat | Thickening, doubling | Vocal presence, guitar character |
| Ping-pong | Variable, L/R alternating | Width, spatial movement | Synths, ear candy |
| Tape | Variable, degrading repeats | Warm, vintage, organic | Anything needing organic feel |
| Dotted-eighth | 3/4 of beat length | Rhythmic interest, syncopation | Rhythmic guitars, vocals |
| Reverse | Variable, pre-echo swell | Atmospheric transitions | Before vocal entries, between sections |

**Always HPF delay returns** at 200-300 Hz. LPF at 6-8 kHz for warmer, more natural repeats. Keep feedback low (1-3 repeats or <20%) — too many repeats = mud. **Genre exception — dub/reggae:** The booming low-end delay IS the genre's sonic identity. Skip the HPF or set it at 60-80 Hz (sub-rumble only), embrace feedback at 30-50%, and let the bass echo ring. Same principle applies to any genre where low-end delay is a defining texture — know the genre before applying default EQ rules.

### Delay as a Reverb Alternative

For genres where reverb is undesirable (hip-hop vocals, dense electronic, modern pop): tempo-synced delays provide depth without wash. Stereo delay with different subdivisions per side (eighth left, dotted eighth right) creates width and movement that simulates spatial depth.

**When reverb creates mud in dense arrangements:** In a busy mix (128+ BPM, stacked production), reverb tails pile up and smear transients. Switch to tempo-synced delay. At 128 BPM: 1/32 = ~58 ms, 1/64 = ~29 ms. A vocal that needs depth but can't afford wash gets a 1/32 or 1/64 delay, HPF at 400 Hz, LPF at 4 kHz, feedback at 10-15% (1-2 repeats). For even more transparency, a single slapback at ~15 ms with zero feedback — felt as depth, never heard as echo.

**The thickening delay:** 1/32 or 1/64 note, bandwidth-limited (HPF 400 Hz, LPF 2.5 kHz), low mix. Felt more than heard — adds dimension without audible echoes.

### Inter-Effect Coherence

When one source feeds multiple send effects (e.g., vocal → plate reverb AND slapback delay), the combined spatial image can conflict: the reverb implies a large hall while the delay implies a tight room. **Resolution:** Choose effects that tell a consistent spatial story. Match the delay character to the reverb size — short slapback pairs with room/plate reverb (both say "medium space"), while long ping-pong pairs with hall reverb (both say "expansive"). If combining a long reverb with a short delay for rhythmic interest, HPF the delay aggressively and keep it low in level so it reads as texture, not as a competing space.

### Ducked Reverb / Delay

Sidechain the return from the dry source. During phrases, the effect ducks. In gaps, it blooms. Long, lush tails without sacrificing clarity during performance.

## Chain Order

Chain order changes the result dramatically. Each effect responds to what comes before it.

| Order | Result | Use For |
|-------|--------|---------|
| Distortion → Reverb | Clean space on distorted source, articulate | Heavy rock, metal |
| Reverb → Distortion | Dense layered wall, smeared, massive | Shoegaze, dream pop, ambient |

**Why chain order reverses for shoegaze/dense layered textures:** When a guitarist wants a massive, fused wall of guitars, the instinct is distortion→reverb — but that keeps the distorted signal articulate and the reverb clean behind it. Reverse: reverb FIRST, distortion SECOND. The reverb tail becomes input to the distortion stage, so distortion smears and compresses the entire reverberant field into a single fused mass. Individual notes blur together. For even more density, feed a long hall (3-5s, high diffusion) into medium-drive tube saturation, then follow with a second shorter reverb (1-2s) to add dimension to the distorted mass.
| EQ → Reverb (on send) | Shapes what frequencies excite the reverb | Targeted, tailored ambience |
| Reverb → EQ (on return) | Shapes the reverb tail itself | Darken or clean up the tail |
| Compression → Delay | Even, predictable repeats | Clean delay behavior |
| Delay → Compression | Pumping, interacting repeats | Lo-fi, chaotic, energetic |

**The exception rule:** Any of these can be reversed for creative effect — as long as it's intentional, not accidental.

For complete creative chain recipes (ethereal vocals, massive guitars, gated drums, lo-fi, etc.): load [creative-chains.md](creative-chains.md).

## Effects Automation

Static effects are demo-level. Professional productions automate effects to breathe with the arrangement.

### Automation Targets

| Target | Technique | When |
|--------|-----------|------|
| Filter sweeps | Automate LPF/HPF cutoff | Builds, transitions, drops |
| Delay throws | Send from -inf to 0 dB on specific words/hits | Last word of phrases, structural moments |
| Reverb size | Shorter in verse (intimate), longer in chorus (epic) | Section changes |
| Drive/saturation | Increase into chorus for energy | Verse → chorus transitions |
| Stereo width | Narrow in verse, wide in chorus | Section changes |
| Effect type | Different reverb programs per section | Emotional landscape shifts |

**The principle:** Effects that appear momentarily draw attention and create drama. Effects that are constant become wallpaper. Use throws at structural moments. **Expected result:** The listener should feel section transitions as emotional shifts — verse intimacy gives way to chorus expansion. If a transition doesn't register emotionally on playback, the automation delta isn't large enough or isn't timed to the musical event.

**Arrangement density scaling:** Effects must scale with density — not just in size, but in type and amount. Sparse verse (2-3 elements): long reverb fills space. Dense chorus (8+ elements): that same reverb becomes mud. Scale back: shorten decay by 30-50% in dense sections, reduce sends by 3-6 dB, or switch from reverb to delay for depth. The denser the arrangement, the less each source needs spatial treatment — density itself creates the "big" feeling.

**Cross-section transition timing:** For regular structures: at 1/2 bar before the chorus downbeat, cut the verse send from 0 dB to -inf over one beat; on the chorus downbeat, snap to chorus settings. **For irregular structures (7-bar verse, 5-bar bridge, odd meters):** bar-count rules don't apply — anchor automation to the musical event instead: the last vocal phrase ending, the final chord change, or the drum fill. Listen for the moment the section "exhales" and begin the send cut there, regardless of bar position. The principle is the same (clear space before the new section hits), but the anchor is the musical gesture, not the grid.

For builds into a drop: automate reverb size or filter sweep UP into the transition, then cut everything to dry on beat one — the sudden absence of effects is the impact.

**Depth without reverb or delay:** Two techniques create front-to-back positioning with zero wash: (1) EQ darkness — roll off HF above 4-6 kHz progressively on elements you want pushed back (close sounds are bright/detailed, distant sounds are filtered by air). (2) Level reduction — drop 2-4 dB and it recedes. Combine both for convincing depth that translates perfectly in mono.

## Send/Return & Routing

1. Effect plugin on return must be **100% wet** — if it mixes dry signal in, you get comb filtering when combined with the channel's dry output
2. Use **post-fader sends** by default — send level tracks with the fader. Use pre-fader only when you want the effect independent of channel level (parallel compression, reverb that persists after a fade-out)
3. Pan sends to match the source — a guitar panned 30% right should send to a stereo reverb that returns at a similar position, not dead center

**Bus vs individual effects routing:** Reverb on a drum BUS creates a shared room — all elements sound cohesive, as if recorded in one space. Reverb on individual drum tracks (kick, snare, hats separately) creates varied depth per element — more separation and control, but risks sounding like each drum is in a different room. **Use bus routing** when cohesion matters (acoustic drums, ensemble recordings). **Use individual routing** when you need surgical control (electronic drums, heavily layered production). You can combine: shared room reverb on the bus for glue, plus individual sends to different effects for character.

**Stem delivery consideration:** When a mix will be delivered as stems (film/TV sync, remix, live playback), keep effects on send/return buses — never print reverb/delay directly onto stems. Printed effects can't be adjusted by the stem recipient. Label effect returns clearly ("VOX PLATE," "DRUM ROOM") so they can be included as separate stems.

## Verification

After spatial processing, run `analyze_stereo`:
- Correlation above +0.3 → mono-safe
- Correlation 0 to +0.3 → borderline, check mono playback carefully
- Correlation below 0 → phase problems, rethink the processing

**Mono check is mandatory** after any widening, Haas effect, micro-pitch detuning, or heavy stereo reverb/delay. What sounds wide on monitors can disappear on a single Bluetooth speaker.

## Reference Materials

- [effect-taxonomy.md](effect-taxonomy.md) — full distortion/modulation/time-based taxonomy with DSP science
- [creative-chains.md](creative-chains.md) — chain recipes: ethereal vocals, massive guitars, gated drums, lo-fi, underwater, telephone, reverse reverb, effect throws
- [reaper-recipes.md](reaper-recipes.md) — compound Reaper operations (requires Reaper MCP server)

## Final Checklist (restated for attention)

1. Define intent before choosing effect — know WHY before WHAT
2. 100% wet on send returns — dry signal mixed in = comb filtering
3. Mono check after any spatial processing — correlation above +0.3
4. Automate effects with the arrangement — static effects are wallpaper
5. HPF reverb and delay returns — low-end in effects builds mud
6. Time delays to tempo — BPM math for invisible integration
7. EQ reverb returns — the most overlooked technique for clean spatial processing
