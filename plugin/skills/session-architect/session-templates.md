# Genre-Specific Session Templates

Pick the template closest to your project and adapt. These are starting points, not rigid blueprints. Unconventional projects should start from the Rock/Metal template (most comprehensive) and modify.

## Rock / Metal

The most comprehensive template. Use as a base for any project with live drums and guitars.

**Track Hierarchy:**
```
DRUMS (red)
  Kick In
  Kick Out
  Kick Trigger (metal only -- sample replacement/reinforcement)
  Snare Top
  Snare Bottom
  Hi-Hat
  Tom 1, Tom 2, Tom 3
  Overhead L, Overhead R
  Room L, Room R

BASS (blue)
  Bass DI
  Bass Amp

GUITARS (green)
  Rhythm L (hard left)
  Rhythm L2 (slightly left -- for quad-tracked)
  Rhythm R (hard right)
  Rhythm R2 (slightly right -- for quad-tracked)
  Lead
  Clean / Acoustic

VOCALS (yellow)
  Lead Vocal
  Screams / Growls (metal)
  Harmony 1, Harmony 2
  Backing Vocals
  Ad-libs

FX RETURNS (purple)
  Room Verb (short, tight -- drums)
  Plate Verb (medium -- vocals, snare)
  Slapback Delay (50-100 ms)
  Long Delay (quarter note, 3-5 repeats)
  Parallel Comp (drums)

MIX BUS
```

**Routing Notes:**
- Quad-tracked guitars: Rhythm L + L2 panned 100% and 80% left, R + R2 panned 100% and 80% right. Use different amp tones for L vs R for width.
- Sidechain kick to bass (channels 3-4) for low-end clarity
- Parallel compression send from drum bus -- blend heavy compression underneath
- Snare bottom mic almost always needs polarity flip
- Kick trigger track: blend with close mics for consistency, don't replace entirely

**Key Considerations:**
- Low-end management is the critical challenge: kick, bass, and guitar low-end all compete
- HPF guitars at 80-120 Hz minimum, higher for cleaner mixes
- Metal: dedicated trigger tracks for kick and sometimes snare consistency
- Vocal parallel processing aux for density without losing dynamics

---

## Pop

Vocal-forward with polished, wide, bright production.

**Track Hierarchy:**
```
DRUMS (red)
  Kick
  Snare
  Hi-Hat
  Percussion / Shaker
  Drum Loop / Programmed

BASS (blue)
  Bass (DI or synth)
  Sub Bass (808 or synth sub)

KEYS / SYNTHS (orange)
  Piano
  Synth Pad
  Synth Lead
  Arpeggiated Synth

GUITARS (green)
  Acoustic (if present)
  Electric (if present)

VOCALS (yellow)
  Lead Vocal
  Lead Vocal Double
  Harmony High
  Harmony Low
  Backing Vocals (stacked)
  Ad-libs
  Vocal Chops / Effects

FX RETURNS (purple)
  Plate Verb (vocals)
  Room Verb (instruments)
  Hall Verb (specials)
  Slapback Delay
  Dotted-Eighth Delay
  Vocal Throw Delay (automated)
  Parallel Vocal Comp

MIX BUS
```

**Routing Notes:**
- Vocals are king -- more vocal buses and sends than any other genre
- Multiple delay sends for different vocal effects (slapback for thickening, dotted-eighth for rhythmic interest, throw delay for phrase endings)
- Vocal parallel compression bus for density
- Wide effects palette: more FX returns than other genres
- Sub bass and kick need careful sidechain management

**Key Considerations:**
- Heavy compression and automation on vocals -- every word equally audible
- Bright, polished top end (10-16 kHz air shelf common)
- Wide stereo image from panned synths and doubled vocals
- Vocal chain is the most complex: de-esser, compression (often serial), EQ, saturation, sends

---

## Hip-Hop / Trap

808/kick relationship is everything. Vocal clarity paramount.

**Track Hierarchy:**
```
DRUMS (red)
  Kick / 808 Kick
  808 Sub Bass
  Snare / Clap
  Hi-Hat (often with rolls)
  Percussion / Shaker
  Open Hat

BASS (blue)
  808 (if separate from drums)
  Bass Synth

MELODICS (orange)
  Melody Loop
  Counter Melody
  Pad / Atmosphere
  Piano / Keys
  Guitar (if present)

VOCALS (yellow)
  Lead Vocal
  Lead Vocal Double
  Ad-libs
  Backing Vocals
  Vocal Effects / Chops

FX RETURNS (purple)
  Plate Verb (vocals -- subtle)
  Room Verb (drums -- very short)
  Delay (quarter note)
  Vocal Throw
  Distortion Bus (parallel)

MIX BUS
```

**Routing Notes:**
- 808/kick sidechain is THE critical routing decision: duck 808 sub when kick hits
- Keep 808 and kick on separate tracks even if they came from the same beat -- you need independent processing
- Vocal chain: heavy compression, de-esser, saturation for warmth, short plate reverb
- Parallel distortion bus for vocal aggression (blend underneath)
- Simpler instrument routing than rock, but complex vocal routing

**Key Considerations:**
- Low-end balance is everything: 808 sub + kick must be precisely carved
- Mono below 100 Hz (critical for club and car playback)
- Vocal clarity above all -- cut everything else at 2-4 kHz to make room
- Hi-hat rolls need careful level management (can dominate if too loud)
- Less reverb overall than other genres -- tight, dry, punchy aesthetic

---

## Electronic / EDM

Synth-heavy with multiple effect layers and sidechain as a groove tool.

**Track Hierarchy:**
```
DRUMS (red)
  Kick
  Snare / Clap
  Hi-Hat (closed, open)
  Percussion
  Drum Loop / Break

BASS (blue)
  Sub Bass
  Mid Bass / Reese
  Bass FX / Growl

SYNTHS (orange)
  Lead Synth
  Pad
  Pluck / Arp
  Atmosphere / Texture
  FX / Risers / Impacts

VOCALS (yellow -- if present)
  Lead Vocal
  Vocal Chops
  Vocal FX

FX RETURNS (purple)
  Reverb (hall -- big)
  Reverb (room -- tight)
  Delay (ping-pong)
  Delay (synced)
  Filter Sweep Bus
  Parallel Distortion

MIX BUS
```

**Routing Notes:**
- Sidechain EVERYTHING to the kick: bass, pads, synths all duck on kick hits -- this IS the EDM groove
- Multiple sidechain depths: bass ducks hard (-6 dB), pads duck medium (-3 dB), leads duck subtle (-1 dB)
- Stereo imaging is critical: keep sub mono below 100-150 Hz, widen synths and pads
- Filter sweep bus: route synths through an automated filter for builds and drops
- FX/risers/impacts on their own tracks for precise placement

**Key Considerations:**
- The sidechain pump is a musical element, not just a mixing tool
- Bass mono below 100-150 Hz (club systems are mono in the sub)
- Transition design: risers, impacts, filter sweeps, reverb swells between sections
- Loudness competition is fierce: -6 to -8 LUFS final masters are common
- More FX automation than any other genre

---

## Acoustic / Folk

Minimal processing, natural sound, simple routing.

**Track Hierarchy:**
```
ACOUSTIC INSTRUMENTS (green)
  Acoustic Guitar 1
  Acoustic Guitar 2 (if present)
  Banjo / Mandolin / Ukulele
  Piano / Keys

STRINGS (orange -- if present)
  Violin
  Cello
  String Section

BASS (blue)
  Upright Bass / Bass Guitar

DRUMS / PERCUSSION (red -- if present)
  Kick (often cajon or brushes)
  Snare / Side Stick
  Percussion (shaker, tambourine)

VOCALS (yellow)
  Lead Vocal
  Harmony 1, Harmony 2
  Group Vocals

FX RETURNS (purple)
  Room Verb (natural, short-medium)
  Plate Verb (vocals only)
  Slapback Delay (subtle)

MIX BUS
```

**Routing Notes:**
- Fewer buses and sends than other genres -- simplicity is the aesthetic
- Natural reverb: one room reverb shared across most instruments for cohesion
- Minimal compression -- preserve dynamics and performance nuance
- No sidechain compression needed (no competing sub-bass elements)
- Simple panning: instruments spread naturally, vocals centered

**Key Considerations:**
- Less processing overall -- the recording quality matters more than the mix
- Natural room sound preferred over artificial reverb
- Dynamic range preserved: 12-20 LU loudness range is normal
- Proximity effect on vocals and acoustic guitar: HPF at 80-120 Hz
- Bleed between instruments (if recorded live) is part of the sound, not a problem
