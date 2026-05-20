# Creative Effect Chain Recipes

Specific effect chain recipes for common sound design goals. Each recipe lists the chain order, key parameters, and what makes it work. Adapt settings to taste -- these are starting points, not presets.

## Ethereal Vocals

**Goal:** Dreamy, washed-out, otherworldly vocal that floats above the mix.

**Chain:**
1. Micro-pitch detuning (+/-5-7 cents, 10-20 ms delay, panned L/R) -- width without phase destruction
2. Plate reverb (long decay 3-5s, high diffusion, pre-delay 30-40 ms) -- the space
3. Delay (quarter note, 40-60% feedback, HPF return at 300 Hz) -- rhythmic echoes into the reverb
4. Light chorus (slow rate 0.3 Hz, subtle depth) -- shimmer on the tail

**Why this order works:** The pitch detuning creates width first. The reverb responds to the widened source. The delay feeds into the reverb tail, creating cascading echoes. The chorus adds final movement.

**Tips:** Sidechain the reverb return from the dry vocal so it ducks during phrases and blooms in gaps. Automate reverb send -- more in verses (intimate), slightly less in choruses (let the arrangement provide the energy).

## Massive Guitars

**Goal:** Dense, massive guitar wall that fills the stereo field without losing articulation.

**Chain (for articulate heavy tone):**
1. Amp distortion (the guitar's own gain)
2. Parallel clean blend (DI or clean amp at -12 dB underneath -- restores pick definition)
3. Room reverb (short 0.5-1s, tight, low mix) -- depth without wash
4. Slight chorus on the clean parallel layer only -- width without affecting the distortion

**Chain (for shoegaze wall):**
1. Reverb FIRST (hall, long decay 4-6s, 100% wet on send) -- create the wash
2. Distortion AFTER (medium-high drive, tube or tape) -- saturate the reverb tail
3. The result: everything smears into one massive texture

**The key distinction:** Distortion-into-reverb = you hear the distortion clearly in a space. Reverb-into-distortion = the reverb itself is distorted, creating a wall where individual notes dissolve.

## Aggressive Vocal Distortion

**Goal:** Controlled grit and edge on vocals — focused aggression, not fuzz, not clean. A driven tone that sits in a heavy mix without becoming harsh.

**Chain (direct vocal):**
1. EQ — HPF 80 Hz, gentle cut at 300-400 Hz (remove body mud), presence boost at 3-5 kHz
2. Compressor — aggressive ratio (4:1+), fast attack, auto-gain. Vocals need to be even before distortion hits.
3. Pitch correction — before distortion, not after. Correcting pitch on a distorted signal produces artifacts.
4. Exciter/Saturation — Neutron 4 Exciter with Trash mode on ONE band only (typically band 1, low-mids). **Drive at 10-20%, NOT higher.** 50%+ sounds like a broken speaker, not controlled aggression. Mix at 50-70%.
5. Tone control — dark the exciter output (tone knob toward warm). Aggressive vocals should be gritty but not bright.

**Chain (parallel distortion bus):**
1. Ozone Vintage Tape — input drive 50-60%, harmonics 30-40%, max speed. This is the warmth layer.
2. Compressor — heavy ratio to crush dynamics and create a consistent distortion texture
3. Exciter — Trash mode on bands 1-2, drive 25-35%, dark tone. More aggressive than the direct chain.
4. EQ — roll off highs above 6 kHz. The parallel bus should sit BEHIND the dry vocal, not on top.

**Send level:** Start at -18 dB and bring up slowly. -8 to -12 dB is typical. The parallel bus adds texture, not volume.

**Critical mistake to avoid:** Setting exciter drive above 40% on the direct vocal. Every 10% above 20% adds exponentially more distortion. The sweet spot for aggressive vocal distortion is 10-20% direct, 25-35% parallel.

**Vocal doubler for choruses:**
1. ReaDelay — very short (20-30ms), no feedback, 100% wet (it's a send)
2. ReaPitch — detune -8 to -12 cents. NOT semitones. Cents.
3. Exciter — Trash mode, 20-30% drive, dark tone
4. EQ — high shelf cut at 6-8 kHz to darken
5. Pan opposite to any other width elements (40% L or R)
6. Blend at -8 to -12 dB

**Octave doubler (chorus-only moments):**
1. ReaPitch — -12 semitones (one octave down)
2. EQ — heavy high shelf cut. This should be a dark rumble underneath, not audible as a separate voice.
3. Pan opposite to the detuned doubler
4. Blend at -14 to -18 dB — barely there, felt more than heard
5. Only unmute during choruses or climactic sections for impact

## Gated Drums (80s Style)

**Goal:** Big, explosive drum hits that cut off abruptly — the classic gated reverb effect.

**Chain:**
1. Heavy compression (10:1, fast attack 1-3 ms, fast release 30-50 ms) -- squash the dynamics
2. Short room reverb (0.3-0.8s decay, high density, no pre-delay)
3. Gate on the reverb return (fast attack, short hold 50-100 ms, fast release 20-50 ms)

**Why it works:** The compression makes every hit equally powerful. The room reverb adds explosive ambience. The gate chops the reverb tail, creating that signature "big hit, sudden silence" sound.

**Modern variation:** Instead of gating the reverb, use a transient shaper on the reverb return to exaggerate the attack and kill the sustain.

## Lo-fi Effect

**Goal:** Warm, degraded, vintage character -- old cassette or vinyl vibes.

**Chain:**
1. LPF at 8-10 kHz (roll off the highs FIRST) -- this is the foundation of the lo-fi sound
2. Saturation (tape, medium drive) -- warmth and subtle compression
3. Bitcrusher (12-bit, reduce sample rate to 22 kHz) -- digital grit
4. Optional: subtle vinyl noise layer underneath

**Why this order matters:** Rolling off the highs before saturating means the saturation doesn't generate harsh high-frequency harmonics. If you saturate first and then filter, you get a different (harsher) character. Lo-fi should feel warm, not edgy.

**Tips:** Don't overdo it. Subtlety is the difference between "this sounds vintage" and "this sounds broken."

## Underwater / Submerged

**Goal:** Muffled, deep, like hearing music through water or a wall.

**Chain:**
1. LPF sweep (automate cutoff from 2 kHz down to 200 Hz for submerging, back up for surfacing)
2. Heavy reverb (hall, 4-6s decay, high diffusion, 100% wet on a send)
3. Chorus (slow, deep, 0.2 Hz rate) -- wavering underwater movement

**The automation IS the effect:** The filter cutoff automation creates the illusion of going underwater (closing) and surfacing (opening). Without the automation, it's just a dark sound.

## Telephone / Radio

**Goal:** Bandlimited, distorted, like hearing through a phone speaker or AM radio.

**Chain:**
1. BPF (bandpass filter: HPF at 300 Hz + LPF at 3 kHz) -- the bandwidth restriction IS the effect
2. Saturation (transistor, medium-heavy) -- the speaker distortion
3. Subtle EQ peak at 1 kHz -- nasal telephone resonance

**Tips:** The tighter the bandpass, the more extreme the effect. 300 Hz-3 kHz is classic telephone. 500 Hz-2 kHz is more aggressive "walkie-talkie."

## Reverse Reverb

**Goal:** A swell that builds into a transient -- creates anticipation and atmosphere.

**Technique:**
1. Reverse the audio clip
2. Add reverb (hall or plate, 3-5s, 100% wet)
3. Render/print the reverb tail to a new track
4. Reverse the rendered reverb
5. Place the reversed reverb so it leads into the original (dry) hit

**Result:** A wash of reverb that swells up and ends precisely at the transient. Use before vocal entries, drum hits, or section changes.

**Shortcut:** Some reverb plugins have a "reverse" mode that does this in real-time, though printed reverse reverb gives you more editing control.

**Reaper MCP limitation:** Reverse reverb requires rendering steps (reverse item, apply reverb, render, reverse again) that cannot be fully automated through the Reaper MCP bridge. The item manipulation APIs (split, reverse, position) use raw Reaper API calls that fail due to pointer serialization issues in the file-based bridge. Plan to do this step manually in Reaper or build a ReaScript action for it.

## Effect Throws

**Goal:** Momentary heavy processing on specific hits or words -- not a constant effect.

**Technique:**
1. Set up the effect on a send (delay, reverb, distortion, whatever)
2. Automate the send level: -inf normally, punch to 0 dB on the target moment
3. The effect catches only that specific hit/word and processes it

**Common throws:**
- **Delay throw on last word of vocal phrase:** the delay echoes that word into the gap before the next phrase
- **Reverb swell in instrumental gap:** the reverb fills the space between sections
- **Distortion burst on a specific snare hit:** momentary aggression for emphasis
- **Filter sweep throw:** automate the filter on a delay return for one specific echo

**The principle:** Effects that are constant become wallpaper -- you stop hearing them. Effects that appear momentarily draw attention and create drama. Use throws at structural moments (end of phrases, transitions, hits).
