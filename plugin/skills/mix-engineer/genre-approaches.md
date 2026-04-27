# Genre-Specific Mixing Approaches

Always run `load_profile` for the target genre to get exact loudness and frequency targets -- these approaches give you the methodology, the profile gives you the numbers.

## Rock / Metal

**Run `load_profile('rock')` or `load_profile('metal')` for targets.**

**Key priorities:** Powerful drums, tight low-end, guitar wall, vocal clarity above the wall.

**Critical challenges:**
- The kick/bass/guitar low-end battle is THE mixing challenge in rock. Three instruments all want 60-250 Hz.
- HPF guitars at 80-120 Hz (nothing useful below). LPF distorted guitars at 8-10 kHz (just noise above).
- Quad-tracked guitars: pan hard L/R, different amp tones on each side for width. The two inner tracks slightly less panned (70-80%) for density.

**Typical processing:**
- Drums: dry, aggressive gating on toms and kick, parallel compression on drum bus, room mics blended for depth
- Bass: sidechain to kick, complement the kick EQ (kick gets 60 Hz, bass gets 80-100 Hz -- or reverse)
- Vocals: fight through the guitar wall by owning 2-4 kHz. Automate vocals up in the chorus when guitars are loudest.

## Pop

**Run `load_profile('pop')` for targets.**

**Key priorities:** Vocals are king. Everything serves the vocal.

**Critical challenges:**
- Vocal intelligibility in dense arrangements (stacked synths, layered vocals, programmed drums)
- Bright, polished, wide, loud. Heavy compression and automation are expected.
- Every word must be equally intelligible -- vocal riding is non-negotiable.

**Typical processing:**
- Vocals: serial compression (opto + FET), de-esser, air shelf at 10-12 kHz, heavily automated
- Drums: tight, punchy, heavily compressed. Kick and snare are samples or sample-reinforced.
- Synths/keys: wide stereo, complement vocal frequency space, automated to duck under vocal phrases
- Mix bus: moderate compression (2:1, 1-2 dB GR) for glue

## Hip-Hop

**Run `load_profile('hip-hop')` for targets.**

**Key priorities:** 808/kick relationship. Vocal clarity. Headroom in the sub.

**Critical challenges:**
- The 808 and kick must coexist without masking. Sidechain the 808 to the kick.
- Vocal clarity is paramount -- cut everything else at 2-4 kHz to make room.
- Mono below 100 Hz (critical for car systems and club playback).

**Typical processing:**
- 808: careful saturation for small-speaker translation (see `/phantom:effects-engineer`), mono below 100 Hz
- Kick: short, punchy, designed to complement (not compete with) the 808
- Vocals: heavy compression, de-esser, saturation for warmth, short plate reverb (dry aesthetic)
- Hi-hats: often need careful level management -- they can dominate if too loud

## Electronic / EDM

**Run `load_profile('electronic')` or `load_profile('edm')` for targets.**

**Key priorities:** Sidechain groove. Stereo imaging. Bass mono. Transition design.

**Critical challenges:**
- Bass mono below 100-150 Hz (club systems are mono in the sub)
- Sidechain compression IS the groove -- it's a musical element, not just a mixing tool
- Loudness competition is intense: -6 to -8 LUFS final masters are common for club play

**Typical processing:**
- Kick: central anchor, tight, punchy
- Bass: aggressive sidechain to kick, mono sub, possible mid-bass widening above 150 Hz
- Synths/pads: wide stereo, sidechained to kick (subtle ducking for groove)
- Effects: heavy automation -- filter sweeps, reverb throws, delay changes between sections

## Ambient / Lo-fi

**Run `load_profile('ambient')` or `load_profile('lo-fi')` for targets.**

**Key priorities:** Warmth over clarity. Texture over precision. Space over punch.

**Critical challenges:**
- Knowing when NOT to process. Minimal compression preserves the dynamics that create atmosphere.
- A noise floor, rolled-off highs, and subtle distortion may be intentional aesthetic choices -- don't "fix" them.
- Long reverb tails need careful level management to avoid washing everything out.

**Typical processing:**
- Subtle saturation (tape or tube) for warmth
- Long reverb tails (hall or plate, 3-6 second decay)
- Gentle LPF on most sources (rolling off highs above 10-12 kHz)
- Minimal compression -- fader riding over compressor for dynamics control
- Intentional texture: vinyl noise, tape hiss, bit reduction -- these ARE the genre
