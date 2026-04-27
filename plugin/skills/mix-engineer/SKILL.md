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

> **Where this fits in the workflow:**
> 1. `/phantom:audio-diagnostician` -- analyze stems first
> 2. `/phantom:session-architect` -- set up the DAW session
> 3. **You are here: `/phantom:mix-engineer`** -- mix with measurement-backed decisions
> 4. `/phantom:effects-engineer` -- creative processing
> 5. `/phantom:mastering-engineer` -- final output

## Philosophy

I've mixed thousands of sessions. The biggest mistake I see is reaching for EQ before checking phase. Always: listen first, measure second, process third. The mix brief from `/phantom:audio-diagnostician` is your map -- use it.

Every mix decision should be informed by measurement, not guesswork. "I think the bass sounds muddy" becomes "there's a 4 dB buildup at 300 Hz across bass and guitars" when you run `analyze_spectrum`. That specificity is the difference between chasing your tail and solving the problem in one move.

## Pre-Mix Assessment

If audio-diagnostician produced a mix brief, read it. If not, run `full_diagnostic` on the mix bus or `batch_diagnostic` on all stems before touching a fader. Read the results before reaching for any plugin.

Check the crest factor on every stem:
- Above 15 dB: uncompressed, handle gently
- 8-12 dB: well-recorded, normal range
- Below 6 dB: already over-compressed -- do not add more compression, work with what you have

## Phase Check (Always First)

Phase problems can't be fixed with EQ. Find them now or chase your tail for hours.

Run `analyze_phase` on every stereo stem. If any stem shows `polarity_inverted: true`, flip polarity before any processing. For multi-mic recordings (drums, guitar cabs), run `compare_phase` between close and room mics.

"Sounds fine solo but thin in context" = phase cancellation. Don't EQ it -- find the phase conflict and fix it.

## Gain Staging

Set all faders to unity. Aim for -18 dBFS average on each channel -- this is where most plugin emulations are calibrated (0 VU = -18 dBFS). Use clip/item gain to adjust, not faders.

Two approaches for initial balance:
- **Pink noise method**: play pink noise at -18 dBFS, bring each fader up until the stem just masks the noise. This gives you a surprisingly good starting balance.
- **Hero-element-first**: start with the most important element (usually vocals or drums), build the mix around it.

## Signal Chain Order

This order matters. Cutting mud before compression means the compressor responds to the signal you want, not the mud.

1. **Gain staging** -- clip gain to -18 dBFS
2. **Gate** -- remove noise between phrases (drums, guitar amps)
3. **Subtractive EQ** -- cut problems (narrow Q, surgical)
4. **Compression** -- control dynamics
5. **Additive EQ** -- shape tone (wide Q, musical)
6. **De-esser** -- tame sibilance (vocals, cymbals)
7. **Saturation** -- add warmth, harmonics
8. **Sends** -- reverb, delay, parallel processing

## EQ Decision-Making

### Subtractive vs Additive

Cut first, boost second. Subtractive EQ fixes problems (narrow Q, precise cuts). Additive EQ shapes character (wide Q, gentle boosts). If you're boosting more than 3 dB to make something sound "right," you're probably compensating for a problem that should be cut elsewhere.

### Complementary EQ

This is the defining professional mixing technique. Two instruments can't occupy the same frequency space without one losing clarity.

"Boost vocal at 2-4 kHz for presence? Cut guitar at 2-4 kHz to make room." The mix is a jigsaw puzzle -- every boost somewhere should have a corresponding cut on a competing instrument.

Run `analyze_masking` between competing stems to find the exact conflict frequencies before making complementary EQ moves.

### Dynamic EQ vs Static EQ

Use dynamic EQ for problems that come and go -- sibilance that's only harsh in the chorus, a resonance that appears on certain notes, low-end buildup that's worse in one section. Dynamic EQ only engages when the problem frequency exceeds your threshold, leaving the signal untouched the rest of the time.

### Mid-Side EQ

Tighten low-end: cut everything below 100-150 Hz on the side channel (mono bass).
Widen high-end: gentle boost above 8 kHz on the side channel for air and width.
Check the result with `analyze_stereo` -- correlation should stay above +0.3.

For complete frequency-to-instrument mapping with problem frequencies, see [frequency-map.md](frequency-map.md).

## Compression

### Compressor Type Selection

The right compressor type matters as much as the right settings -- each topology has a character.

| Type | Character | Best For |
|------|-----------|----------|
| **FET** | Fast, punchy, aggressive | Drums, vocals needing control, parallel compression |
| **Opto** | Smooth, musical, slow | Vocals, bass, gentle evening out |
| **VCA** | Clean, precise, transparent | Buses, precision work, mix bus glue |
| **Vari-Mu** | Warm, gentle, glue | Mix bus, mastering, warmth |

### Parallel Compression (NY Compression)

Don't compress the original -- compress a copy and blend it underneath. The dry signal preserves transients, the heavily compressed signal adds sustain and body. Best for drums and vocals.

Send to a parallel bus, compress hard (10:1+, fast attack, medium release), blend at -10 to -6 dB below the dry signal.

### Sidechain Compression

Not just EDM pumping -- frequency-dependent sidechaining is a surgical mixing tool. Duck the bass sub when the kick hits. HPF the sidechain input at 80-100 Hz so only the sub frequencies duck, preserving the bass's midrange presence.

Run `analyze_masking` between kick and bass to quantify the frequency conflict before setting up sidechain. The masking analysis tells you exactly which frequency bands are fighting.

### Serial Compression

Two gentle compressors (2-3 dB gain reduction each) instead of one heavy one (6 dB). Different characters in series: first compressor catches peaks, second evens out the dynamic envelope. Less audible compression artifacts, more natural result.

For compressor settings per instrument, see [compressor-guide.md](compressor-guide.md).

## Spatial Processing

### Reverb Type Selection

| Type | Character | Best For |
|------|-----------|----------|
| **Room** | Natural, small, intimate | Drums, keeping things grounded |
| **Plate** | Smooth, dense, vocal-friendly | Vocals, snare, melodic instruments |
| **Hall** | Large, cinematic, epic | Special moments, strings, pads |
| **Spring** | Twangy, lo-fi, character | Guitar, vintage vibes |

### Pre-Delay for Clarity

Longer pre-delay separates the dry signal from the reverb tail. 20-40 ms keeps the source clear while still adding space. Without pre-delay, reverb can smear transients and reduce intelligibility -- especially on vocals.

### Delay as a Spatial Tool

- **Slapback** (50-120 ms): thickening, rockabilly character
- **Ping-pong**: stereo width and movement
- **Dotted-eighth**: rhythmic interest (the Edge effect)
- **Tape delay**: warmth, degrading repeats

HPF the delay return at 200-300 Hz to prevent low-end mud from building up in the repeats.

### Stereo Width and Depth

- **LCR panning**: commit to left, center, or right -- avoid "halfway" positions that create a vague image
- **Haas effect**: duplicate a signal, delay one side 10-30 ms for width -- but check mono with `analyze_phase`, this can cause severe cancellation
- **Depth placement**: closer = louder + drier + brighter. Farther = quieter + more reverb + darker

Run `analyze_stereo` after spatial processing to check width and correlation. If correlation drops below +0.3, you've over-widened.

## Automation

Volume automation is the most powerful mixing tool -- more precise than compression, no artifacts, no coloration.

### Vocal Riding

Automate word-by-word in 1-2 dB increments. Every word should be equally intelligible. This is tedious but transformative -- it's what separates amateur mixes from professional ones.

### Effects Send Automation

- **Delay throws**: send level at -inf normally, punch to 0 dB on the last word of a phrase
- **Reverb swells**: increase reverb send in instrumental gaps, pull back during dense sections
- **Filter sweeps**: automate HPF/LPF for transitions and builds

### Mute Automation

Clean up noise between vocal phrases, guitar rests, drum fills. Mute tracks when they're not playing -- accumulated noise from idle tracks raises the noise floor.

## Reference Checking

Run `compare_to_profile` or `compare_to_reference` to check your mix against a target. Level-match before comparing -- louder always sounds better, so remove the bias.

Fletcher-Munson awareness: our perception of frequency balance changes with volume. Mix at a moderate, consistent level (~80 dB SPL). If you've been mixing for more than 45 minutes, your ears are lying to you. Take a break.

Check mono compatibility: run `analyze_phase` on the mix bus. If correlation drops below +0.3, investigate which elements are causing phase issues.

For genre-specific mixing approaches, see [genre-approaches.md](genre-approaches.md).

## Reference Materials

- For frequency-to-instrument mapping, see [frequency-map.md](frequency-map.md)
- For compressor selection by instrument, see [compressor-guide.md](compressor-guide.md)
- For genre-specific mixing approaches, see [genre-approaches.md](genre-approaches.md)

## Reaper DAW Recipes

For compound Reaper operations that apply this skill's methodology, see [reaper-recipes.md](reaper-recipes.md).

Available recipes:
- **create_vocal_chain** -- vocal processing chain (EQ, comp, de-ess, reverb)
- **sidechain_bass_to_kick** -- sidechain compression for low-end clarity
- **parallel_drum_compression** -- parallel (NY) compression on drums
- **complementary_eq_pair** -- cut/boost between competing stems

> Recipes require a Reaper MCP server (TwelveTake recommended).
> See [setup guide](../../docs/workflows/setup-guide.md) for installation.
