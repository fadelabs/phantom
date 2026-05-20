# Genre-Specific Mixing Approaches

Run `load_profile` for the target genre to get exact loudness and frequency targets. These approaches give methodology; the profile gives numbers.

---

## Rock / Metal

**Run `load_profile('rock')` or `load_profile('metal')` for targets.**

**Key priorities:** Powerful drums, tight low-end, guitar wall, vocal clarity above the wall.

**The central challenge:** The kick/bass/guitar low-end battle. Three instruments all want 60-250 Hz. This is THE mixing problem in rock.

**Processing approach:**

| Element | Treatment |
|---------|-----------|
| Guitars | HPF at 80-120 Hz. LPF distorted guitars at 8-10 kHz. Quad-tracked: hard L/R with different amp tones per side, inner tracks at 70-80% for density. |
| Drums | Dry, aggressive gating on toms/kick. Parallel compression on drum bus (near-universal). Room mics blended for depth. |
| Bass | Sidechain to kick. Complement kick EQ (kick gets 60 Hz → bass gets 80-100 Hz, or reverse). |
| Vocals | Own 2-4 kHz by cutting guitars there. Automate vocals UP in chorus when guitars are loudest. |
| Mix bus | More aggressive bus compression than other genres (3-4 dB VCA, glue everything). |

**Pacing:** Drum sound is a major time investment — many engineers spend the first hour+ just on the drum bus. Accept this.

---

## Pop

**Run `load_profile('pop')` for targets.**

**Key priorities:** Vocals are king. Everything serves the vocal. Every word equally intelligible.

**The central challenge:** Vocal intelligibility in dense arrangements (stacked synths, layered vocals, programmed drums). Bright, polished, wide, loud.

**Processing approach:**

| Element | Treatment |
|---------|-----------|
| Lead vocal | Serial compression (opto + FET), de-esser, air shelf at 10-12 kHz, word-by-word automation (non-negotiable). |
| Background vocals | Tucked 3-6 dB below lead, wider stereo spread, slightly darker EQ. |
| Drums | Tight, punchy, heavily compressed. Kick/snare sample-reinforced. |
| Synths/keys | Wide stereo, complement vocal frequency space, sidechained to duck under vocal phrases. |
| Mix bus | Moderate compression (2:1, 1-2 dB GR) for glue. |

**The rough mix problem:** Pop producers and artists are most likely to be attached to the rough. Match its vocal balance and energy, then improve everything else.

---

## Hip-Hop / R&B

**Run `load_profile('hip-hop')` for targets.**

**Key priorities:** 808/kick relationship. Vocal clarity. Headroom in the sub. Mono below 100 Hz.

**The central challenge:** The 808 and kick must coexist without masking. Vocal clarity is paramount.

**Processing approach:**

| Element | Treatment |
|---------|-----------|
| 808 | Careful saturation for small-speaker translation. Mono below 100 Hz. Sidechain to kick. |
| Kick | Short, punchy, designed to complement (not compete with) the 808. Tune to key of the bass line. |
| Vocals | Heavy compression, de-esser, saturation for warmth, short plate reverb (dry aesthetic). Cut everything else at 2-4 kHz. |
| Hi-hats | Careful level management — can dominate if too loud. |
| Effects | Delay over reverb for vocal treatment. Vocal effects (pitch, delay, creative processing) are integral to style, not decorative. |

**Speed:** Sessions arrive fast. Hip-hop mixing averages faster turnaround than other genres. Efficiency matters.

---

## Electronic / EDM

**Run `load_profile('electronic')` or `load_profile('edm')` for targets.**

**Key priorities:** Sidechain groove. Stereo imaging. Bass mono. Transition design.

**The central challenge:** Bass mono below 100-150 Hz (club systems are mono in the sub). Sidechain compression IS the groove — it's a musical element, not just a mixing tool.

**Processing approach:**

| Element | Treatment |
|---------|-----------|
| Kick | Central anchor, tight, punchy. The mix is built around the kick pattern. |
| Bass | Aggressive sidechain to kick, mono sub, possible mid-bass widening above 150 Hz. |
| Synths/pads | Wide stereo, sidechained to kick (subtle ducking for groove). Keep within 10-2 o'clock for club playback. |
| Effects | Heavy automation — filter sweeps, reverb throws, delay changes between sections. These are structural, not decorative. |
| Mix bus | Loudness competition is intense: -6 to -8 LUFS final masters for club play. |

**Club considerations:** Keep important elements within 10 o'clock to 2 o'clock pan range. Extreme panning is inaudible to half the club audience.

---

## Ambient / Lo-fi

**Run `load_profile('ambient')` or `load_profile('lo-fi')` for targets.**

**Key priorities:** Warmth over clarity. Texture over precision. Space over punch.

**The central challenge:** Knowing when NOT to process. A noise floor, rolled-off highs, and subtle distortion may be intentional aesthetic choices — don't "fix" them.

**Processing approach:**

| Element | Treatment |
|---------|-----------|
| Everything | Subtle tape/tube saturation for warmth. |
| Reverb | Long tails (hall or plate, 3-6 sec decay). Careful level management so they don't wash everything. |
| High end | Gentle LPF on most sources (10-12 kHz). The genre is intentionally dark/warm. |
| Dynamics | Minimal compression. Fader riding over compressor for dynamics control. |
| Texture | Vinyl noise, tape hiss, bit reduction — these ARE the genre, not problems to solve. |

---

## Country

**Run `load_profile('country')` for targets.**

**Key priorities:** Vocal clarity above all. Every lyric audible. Natural, authentic vocal treatment.

**The central challenge:** Keeping the vocal on top without making the track sound empty. Traditional instruments (steel, fiddle, banjo) need their own space alongside modern production.

**Processing approach:**

| Element | Treatment |
|---------|-----------|
| Lead vocal | Less compression than pop — the genre values vocal authenticity and dynamics. Still automate word-by-word. |
| Steel guitar | Occupies a unique frequency space (~800 Hz-3 kHz presence). Don't EQ it to sound like electric guitar. |
| Fiddle | Bright, forward. Careful not to compete with vocal presence range. |
| Acoustic instruments | Preserve natural dynamics. The "live" quality is valued. |
| Production elements | If modern pop-country elements are present, treat them as supporting, not competing with traditional instruments. |

---

## Jazz / Acoustic

**Run `load_profile('jazz')` or `load_profile('acoustic')` for targets.**

**Key priorities:** Natural balance. Room sound. Minimal processing. Respect the performance.

**The central challenge:** Sessions are simple (10-20 tracks) but demand the most careful monitoring because there's nowhere for problems to hide. Every processing choice is audible.

**Processing approach:**

| Element | Treatment |
|---------|-----------|
| Everything | Minimal — gain staging and room mic blending are the primary tasks. |
| Room mics | Critical. The room IS the sound. Blend carefully with close mics. |
| Compression | Use sparingly or not at all. If the dynamic range is part of the performance, preserve it. |
| EQ | Mostly HPF and gentle problem cuts. No aggressive shaping. |
| Effects | One room verb for blend (if the recorded room isn't enough). Almost no delay or creative effects. |

**Philosophy:** The mixer's job in jazz/acoustic is to present the performance, not reshape it. If you're processing heavily, you're working against the genre.
