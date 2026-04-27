# Effect Taxonomy: DSP Science & Parameters

Deep dive into every effect category with the science behind why they sound the way they do. Reference when you need precise parameters or want to understand the mechanism.

## Distortion & Saturation

### Harmonic Content by Type

| Type | Clipping Shape | Harmonics Produced | Sonic Character |
|------|---------------|-------------------|-----------------|
| Tube | Asymmetrical soft-clip | Even-order (2nd, 4th, 6th) | Warm, musical -- harmonics are octaves and fifths |
| Tape | Compression + soft saturation | Mix of even and odd, with HF rolloff | Glue, warmth, rounded transients |
| Transistor | Symmetrical hard-clip | Odd-order (3rd, 5th, 7th) | Gritty, aggressive -- dissonant harmonics |
| Transformer | Core saturation | Transient softening, subtle harmonics | Dense, weighty, less "distorted" sounding |
| Digital/Bitcrusher | Quantization + sample rate reduction | Aliasing artifacts, not traditional harmonics | Lo-fi, retro, deliberately degraded |

**Why symmetry matters:** Symmetrical clipping (equal on positive and negative swing) produces only odd-order harmonics. Asymmetrical clipping (different behavior on each swing, like a tube with different plate/cathode characteristics) produces both even and odd harmonics. Even harmonics are musically consonant (the 2nd harmonic is an octave above the fundamental), which is why tube distortion sounds "musical" and transistor distortion sounds "harsh."

### Drive Staging

Low drive (subtle): adds warmth and presence without audible distortion. The harmonics are there but blend with the source.

Medium drive: audible coloration, noticeable density. The source character is still dominant but the effect is part of the sound.

High drive: the distortion IS the sound. Source character is secondary to the distortion character. Use for effect, not as a mixing tool.

### Small-Speaker Translation via Saturation

Bass fundamentals at 40-80 Hz disappear on laptop speakers and phones. Saturation generates upper harmonics that small speakers CAN reproduce. The brain uses "the missing fundamental" phenomenon -- hearing the harmonics (160 Hz, 240 Hz, 320 Hz) and inferring the fundamental.

**Technique:** Multiband saturation. Split at 120 Hz. Leave sub clean (no saturation below 120 Hz). Saturate mids (tube or tape character). The sub stays tight and clean while the upper harmonics provide small-speaker presence.

Verify with `analyze_spectrum` -- you should see new energy appearing at harmonic multiples of the bass fundamental.

## Modulation Effects

### Chorus

**Mechanism:** An LFO (low-frequency oscillator) modulates the delay time of a copy of the signal, typically in the 15-35 ms range. The varying delay creates slight pitch shifts (Doppler effect), and combining the modulated copy with the original creates the characteristic shimmering width.

**Key parameters:** Rate (LFO speed, 0.1-5 Hz), Depth (how far the delay time varies), Mix (dry/wet blend), Voices (number of modulated copies -- more = thicker)

### Flanger

**Mechanism:** Same principle as chorus but with much shorter delay times (1-5 ms). At these short delays, comb filtering dominates -- the constructive and destructive interference between the direct and delayed signal creates the characteristic "jet sweep" sound. Feedback amplifies the effect.

**Key parameters:** Rate, Depth, Feedback (resonance of the comb filter), Mix

**Flanger vs Chorus:** It's the same algorithm with different delay ranges. Chorus = 15-35 ms (pitch modulation dominates). Flanger = 1-5 ms (comb filtering dominates).

### Phaser

**Mechanism:** All-pass filters shift the phase of specific frequencies. When combined with the original signal, the shifted frequencies partially cancel, creating moving notches. Unlike flangers, phasers create irregularly spaced notches (flangers create harmonically related notches).

**Key parameters:** Rate, Depth, Stages (more stages = more notches = deeper effect), Feedback

**Phaser vs Flanger:** Phasers use all-pass filters. Flangers use delay. The resulting notch patterns are different -- phasers have a more organic, less metallic sweep.

### Tremolo vs Vibrato

**Tremolo:** Amplitude modulation. The volume goes up and down rhythmically. The pitch stays constant.

**Vibrato:** Pitch modulation. The pitch goes up and down. 100% wet chorus is essentially vibrato.

These are frequently mislabeled (Fender amps labeled "vibrato" are actually tremolo). The distinction matters when communicating with other engineers.

### Ring Modulation

Multiplies two signals together. Unlike mixing (additive), multiplication creates sum and difference frequencies and removes the originals. A 440 Hz signal ring-modulated with a 100 Hz carrier produces 540 Hz and 340 Hz -- neither harmonically related to the original. This is why ring mod sounds inharmonic and metallic.

## Time-Based Effects

### Delay Taxonomy

| Type | Delay Time | Repeats | Character | Mechanism |
|------|-----------|---------|-----------|-----------|
| Slapback | 50-120 ms | 1 | Thickening, doubling | Simple delay, no feedback |
| Ping-pong | Variable | Multiple, alternating L/R | Width, spatial movement | Stereo delay with alternating output |
| Tape | Variable | Degrading | Warm, vintage, organic | Wow/flutter modulation, HF rolloff on repeats |
| Analog/BBD | Variable | Dark, warm | Lo-fi warmth | Bucket-brigade device emulation, noise and artifacts |
| Digital | Variable | Clean, precise | Transparent, modern | Pure delay, no coloration |
| Granular | Variable | Fragmented, textural | Experimental, ambient | Audio split into grains, rearranged |
| Reverse | Variable | Pre-echo swell | Atmospheric, transitional | Reversed delay buffer |
| Multi-tap | Variable patterns | Rhythmic | Complex grooves, polyrhythmic | Multiple delay taps at different times |

### Reverb Deep Dive

**Algorithmic vs Convolution:**
- Algorithmic: mathematically generated, fully adjustable (size, decay, diffusion, damping). Consistent character. Lower CPU. Better for creative use where you need to adjust parameters.
- Convolution: captured from real spaces (impulse response). Realistic but static -- you can't change the size of a real room. Higher CPU. Better for realistic acoustic simulation.

**Key reverb parameters:**
- **Pre-delay** (0-100 ms): gap between dry signal and reverb onset. Crucial for clarity.
- **Early reflections**: the first bounces off nearby surfaces. Defines the room character (small/large, reflective/absorbent).
- **Diffusion**: how quickly the reflections smear into a continuous tail. High diffusion = smooth. Low diffusion = more discrete echoes.
- **Density**: number of reflections per second. Dense = smooth wash. Sparse = more "echoey."
- **Damping**: HF absorption over time. High damping = reverb gets darker as it decays (natural -- air absorbs high frequencies). Low damping = bright, ringy tail.
- **Decay time**: how long the tail lasts. Room: 0.3-1s. Plate: 1-3s. Hall: 2-6s.

## Producer Signature Techniques

Techniques worth studying, described by approach rather than attribution (per privacy guidelines):

- **The Soundtoys stack approach**: per-song delay patches using character plugins, heavy harmonic saturation for grit on every source, treating plugins as instruments rather than corrective tools
- **SansAmp-on-everything approach**: overdriving every channel for high-contrast mixing, binaural recording techniques for width, aggressive tonal shaping that makes every element occupy a distinct sonic space
- **Hardware-first approach**: analog modular processing, finding sounds through physical interaction with equipment, pushing creative boundaries by embracing imperfection and happy accidents
