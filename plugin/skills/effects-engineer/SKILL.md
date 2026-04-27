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

> **Where this fits in the workflow:**
> 1. `/phantom:audio-diagnostician` -- analyze stems first
> 2. `/phantom:session-architect` -- set up the DAW session
> 3. `/phantom:mix-engineer` -- mix with measurement-backed decisions
> 4. **You are here: `/phantom:effects-engineer`** -- creative processing
> 5. `/phantom:mastering-engineer` -- final output

## Philosophy

Effects aren't decoration -- they're part of the arrangement. A well-chosen delay is an instrument. A badly chosen one is a mess. Know why you're reaching for a plugin before you insert it.

The difference between amateur and professional effects use isn't the plugins -- it's intent. "I want the vocal to feel like it's in a cathedral" gives you a reverb with 4-second decay, high diffusion, and a 40ms pre-delay. "I want reverb on the vocal" gives you nothing useful. Define the goal before choosing the tool.

## Distortion & Saturation

When to use saturation: adding warmth, generating harmonics for small-speaker translation, adding density and glue, creating aggression or grit.

### Type Selection

| Type | Harmonic Content | Character | Best For | Caution |
|------|-----------------|-----------|----------|---------|
| **Tube** | Even-order (2nd, 4th) | Warm, musical | Vocals, bass, mix bus | Too much = fizzy, losing transients |
| **Tape** | Compression + harmonics | Glue, warmth, subtle rounding | Drums, mix bus, master bus | Loses transients at high drive |
| **Transistor** | Odd-order (3rd, 5th) | Gritty, aggressive, edgy | Guitars, parallel drums, punk/metal | Harsh in excess, fatiguing |
| **Transformer** | Transient softening | Density, weight, thickness | Drums, bass, full mixes | Reduces clarity at high settings |

Why tubes sound musical: asymmetrical clipping produces even-order harmonics (octaves and fifths), which are consonant with the fundamental. Transistors produce odd-order harmonics (thirds and sevenths), which are more dissonant -- hence the aggressive character.

### Parallel Distortion

Don't distort the original -- distort a copy and blend. Send to a parallel bus, drive hard, blend at -10 to -15 dB underneath the dry signal. The dry signal retains clarity and transients while the distorted signal adds density and harmonics.

### Multiband Saturation

Keep the sub frequencies clean (below 120 Hz), saturate the mids for presence and warmth. This is critical for bass guitar small-speaker translation: the saturation generates upper harmonics (160 Hz, 240 Hz, 320 Hz) that small speakers can reproduce, and the brain interprets them as implying the inaudible fundamental.

For the full distortion taxonomy with DSP science, see [effect-taxonomy.md](effect-taxonomy.md).

## Modulation Effects

### Quick Selection

| Effect | Mechanism | Character | Use When |
|--------|-----------|-----------|----------|
| **Chorus** | LFO modulates delay (15-35 ms) | Width, shimmer, movement | Thickening guitars, widening synths, lush vocals |
| **Flanger** | Same as chorus but 1-5 ms range | Jet sweep, metallic, comb filtering | Dramatic sweeps, sci-fi, guitar solos |
| **Phaser** | All-pass filters (NOT delay-based) | Subtler than flanger, notch patterns | Synths, guitars, funky rhythmic movement |
| **Tremolo** | Amplitude modulation | Pulsing, rhythmic volume changes | Guitar atmosphere, synth pads, vintage organ |
| **Vibrato** | Pitch modulation | Wobble, seasick, intense | Essentially 100% wet chorus -- use sparingly |

### Micro-Pitch Detuning for Width

The +/-7 cents trick: duplicate a signal, pitch-shift one copy up 7 cents and the other down 7 cents, add 10-20 ms delay to each, pan hard L/R. Creates natural width without the phase problems of Haas effect. Check with `analyze_stereo` -- correlation should stay above +0.3.

## Time-Based Effects

### Reverb Selection

| Type | Character | Best For | Pre-Delay |
|------|-----------|----------|-----------|
| **Room** | Natural, small, intimate | Drums, keeping sources grounded | 0-15 ms |
| **Plate** | Smooth, dense, vocal-friendly | Vocals, snare, melodic instruments | 20-40 ms |
| **Hall** | Large, cinematic, epic | Special moments, strings, pads, transitions | 30-60 ms |
| **Spring** | Twangy, lo-fi, character | Guitar, surf rock, vintage | 0-10 ms |
| **Chamber** | Warm, natural, classic | Orchestral, jazz, warm pop | 20-40 ms |

Pre-delay is critical for clarity. Longer pre-delay (30-60 ms) separates the dry signal from the reverb tail, keeping the source intelligible. Without it, reverb smears transients -- especially deadly on vocals.

**Always HPF reverb returns** at 200-300 Hz. Low-end content in reverb creates mud that builds up across the mix. The reverb doesn't need sub-bass.

### Delay Types

| Type | Timing | Character | Use Case |
|------|--------|-----------|----------|
| **Slapback** | 50-120 ms, single repeat | Thickening, rockabilly | Vocal doubling, guitar character |
| **Ping-pong** | L/R alternating | Width, spatial interest | Synths, vocals, ear candy |
| **Tape** | Wow/flutter, degrading repeats | Warmth, vintage | Anything needing organic feel |
| **Dotted-eighth** | 3/4 of beat length | Rhythmic interest | The Edge's signature -- rhythmic guitars, vocals |
| **Reverse** | Pre-echo swell | Atmospheric transitions | Before a vocal entry, between sections |

**HPF delay returns** at 200-300 Hz, same as reverb. LPF at 6-8 kHz for warmer, more natural repeats.

### Ducked Reverb/Delay

Sidechain the reverb/delay return from the dry source signal. During phrases, the effect ducks and stays out of the way. In gaps, it blooms. This gives you long, lush reverb tails without sacrificing clarity during the performance.

Run `analyze_stereo` after spatial effects to check width and correlation. If correlation drops below +0.3, you've over-widened.

## Chain Order Rules

Chain order changes the sound dramatically. These aren't arbitrary -- each order produces a different result because each effect responds to what comes before it.

| Chain Order | Result | Use For |
|------------|--------|---------|
| Reverb → Distortion | Shoegaze wall of sound, smeared, massive | Dream pop, shoegaze, ambient noise |
| Distortion → Reverb | Clean space on distorted source, articulate | Heavy rock, metal (clear despite the gain) |
| Compression → Delay | Delay receives a consistent signal, even repeats | Clean, predictable delay behavior |
| Delay → Compression | Compression pumps with the delay, repeats interact | More chaotic, energetic, lo-fi |
| EQ → Reverb | Shapes what frequencies the reverb responds to | Targeted reverb on specific frequency content |
| Reverb → EQ | Shapes the reverb tail itself | Darken the tail, remove harshness from reverb |

For complete creative chain recipes, see [creative-chains.md](creative-chains.md).

## Effects Automation

Static effects are demo-level. Professional productions automate effects to respond to the arrangement.

### Key Automation Targets

- **Filter sweeps**: automate LPF or HPF cutoff for builds and transitions. Closing LPF into a drop, opening on the downbeat.
- **Delay feedback throws**: send level at -inf normally, punch to 0 dB on the last word of a phrase. The delay catches that word and echoes it into the gap.
- **Reverb size/decay changes**: shorter reverb in verses (intimate), longer in choruses (epic). Automate the decay parameter, not just the send level.
- **Drive automation**: increase saturation subtly into the chorus for energy and density, pull back for the verse. The listener feels the energy change without hearing "distortion."
- **Stereo width**: narrow in verses, wide in choruses. Automate the width of stereo effects or mid/side balance.

Effects should breathe with the song. If the arrangement gets bigger (more instruments, louder, denser), the effects should get bigger too. If the arrangement strips down, the effects should strip down.

## Reference Materials

- For complete distortion, modulation, and time-based effect details with DSP science, see [effect-taxonomy.md](effect-taxonomy.md)
- For creative chain recipes (ethereal vocals, massive guitars, gated drums, lo-fi, etc.), see [creative-chains.md](creative-chains.md)

## Reaper DAW Recipes

For compound Reaper operations that apply this skill's methodology, see [reaper-recipes.md](reaper-recipes.md).

Available recipes:
- **parallel_distortion_bus** -- parallel saturation for warmth/density
- **ducked_reverb_setup** -- sidechain-ducked reverb for clarity

> Recipes require a Reaper MCP server (TwelveTake recommended).
> See [setup guide](../../docs/workflows/setup-guide.md) for installation.
