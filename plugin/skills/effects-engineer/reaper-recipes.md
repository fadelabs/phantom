# Reaper Effects Recipes

Compound operation recipes for creative effects processing in Reaper. These recipes apply the effects-engineer's creative chain knowledge to Reaper's routing and plugin system. Steps describe what to do, not which API to call -- Claude adapts to whichever Reaper MCP server is connected.

> **Requires a Reaper MCP server.** See the [setup guide](../../docs/workflows/setup-guide.md) for installation.

## parallel_distortion_bus

**Trigger:** Mix needs density/warmth. `analyze_dynamics` shows the target track is dynamic but lacks energy. Or user requests "add warmth," "add grit," "fatten the tone."

**Goal:** Set up parallel distortion for adding harmonic density without destroying the clean signal. Per the effects-engineer's "Parallel Distortion" principle: don't distort the original -- distort a copy and blend it underneath.

**Undo Safety:** Create a Reaper undo point before starting.

**Steps:**
1. Identify the target track (often bass, drums bus, or synth pad)
2. Create a new track "[instrument] Parallel Dist" adjacent to the target
3. Add a send from the target track to the distortion bus (pre-fader)
4. Insert a saturation/distortion plugin on the distortion bus (Reaper's JS Saturation or a tube saturation VST)
5. Insert **ReaEQ** after the distortion -- high-pass at 200 Hz and low-pass at 5 kHz (focus the distortion on the midrange where harmonics help, remove sub-frequency mud and high-frequency fizz that distortion generates)
6. Set distortion bus fader low (-12 to -18 dB below the dry signal)
7. Blend to taste -- the distortion should be felt, not heard. If you can clearly hear the distortion as a separate element, it's too loud

**TwelveTake shortcut:** `add_parallel_compression` can be adapted (creates send + bus structure), but you'll need to swap the compressor for a distortion plugin.

**Expected time:** ~1-2 seconds (5-8 Reaper MCP calls)

**Measurement verification after:** Run `analyze_spectrum` on the target track output. Harmonic content should increase in the 1-5 kHz range. RMS should increase slightly without significant peak increase.

**See also:** `/phantom:effects-engineer` parallel distortion section, [creative-chains.md](creative-chains.md) for creative chain ideas.

---

## ducked_reverb_setup

**Trigger:** User wants reverb clarity on vocals or lead instruments. Current reverb washes over the dry signal (reverb tail conflicts with next phrase). Per the effects-engineer's "Ducked Reverb/Delay" principle: sidechain the reverb return from the dry source so it ducks during phrases and blooms in the gaps.

**Goal:** Set up ducked reverb -- reverb ducks when the dry signal is present and blooms in the gaps between phrases. This gives you long, lush reverb tails without sacrificing clarity during the performance.

**Undo Safety:** Create a Reaper undo point before starting.

**Steps:**
1. Identify the source track (typically lead vocal or lead instrument)
2. Identify or create the reverb return track (plate or hall reverb -- use a long decay 2-4s for the effect to be audible in the gaps)
3. Add a send from the source track to the reverb return
4. Insert a reverb plugin on the return (**ReaVerbate** for basic reverb, or a third-party plate/hall for higher quality)
5. Insert **ReaComp** AFTER the reverb on the return track
6. Add a sidechain send from the source track to the reverb return's **ReaComp** on channels 3-4
7. Configure **ReaComp** on the reverb return: ratio 4:1, fast attack 1-5 ms, medium release 200-300 ms, threshold so reverb ducks ~6-10 dB when the dry signal is present
8. Set **ReaComp** detector input to auxiliary channels 3-4
9. Result: reverb is quiet during vocal phrases, swells up in the gaps between them

**TwelveTake shortcut:** Combine routing operations for the send/sidechain setup. No single compound tool covers the full recipe.

**Expected time:** ~1-2 seconds (6-10 Reaper MCP calls)

**Measurement verification after:** Qualitative -- play back and listen. The reverb should be clearly audible between phrases and nearly inaudible during phrases. No automated measurement captures this well. Optionally run `analyze_stereo` to verify the reverb adds width without dropping correlation below +0.3.

**See also:** `/phantom:effects-engineer` ducked reverb/delay section, [reaper-setup.md](../session-architect/reaper-setup.md) for sidechain routing via channels 3-4, [creative-chains.md](creative-chains.md) for more creative chain ideas.
