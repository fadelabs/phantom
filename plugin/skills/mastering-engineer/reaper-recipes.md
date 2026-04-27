# Reaper Mastering Recipes

Compound operation recipes for mastering workflows in Reaper, driven by Phantom analysis measurements and reference comparisons. Each recipe starts with a Phantom measurement trigger and describes step-by-step outcomes. Steps describe what to do, not which API to call -- Claude adapts to whichever Reaper MCP server is connected.

> **Requires a Reaper MCP server.** See the [setup guide](../../docs/workflows/setup-guide.md) for installation.

## mastering_chain_streaming

**Trigger:** Mix bounce ready for mastering. `compare_to_profile` deviations show how the mix compares to a genre target. `analyze_loudness` shows current LUFS. Target delivery: Spotify (-14 LUFS), Apple Music (-16 LUFS), YouTube (-14 LUFS), Tidal (-14 LUFS).

**Goal:** Build a streaming-optimized mastering chain following the mastering-engineer's complete chain methodology (stages 1-9 from SKILL.md).

**Undo Safety:** Create a Reaper undo point before starting.

**Steps:**
1. Create a dedicated mastering track or use the MIX BUS output
2. Insert **ReaEQ** (stage 1: high-pass at 20-30 Hz to remove sub-rumble -- this content is inaudible but wastes headroom and causes the limiter to react to energy you can't hear)
3. Insert **ReaEQ** (stage 2: corrective/subtractive EQ -- address `compare_to_profile` frequency deviations with gentle cuts, narrow Q for problem frequencies, wider Q for broad tonal issues)
4. Insert **ReaComp** (stage 3: broadband compression -- ratio 1.5-2:1, slow attack 30 ms, auto release, 1-3 dB gain reduction for glue. VCA-style for transparency. If hitting more than 3 dB, the mix needs more compression in the mix stage, not the master)
5. Insert **ReaXcomp** (stage 4: multiband compression -- target problem bands identified by `compare_to_profile` deviations, gentle ratios. Place crossover frequencies between instruments' frequency ranges, not through them)
6. Insert **ReaEQ** (stage 5: tonal/additive EQ -- broad gentle boosts to match genre target curve from `compare_to_profile`. Air shelf above 10 kHz if needed, warmth at 100-200 Hz. Keep boosts under 2 dB)
7. Configure stereo imaging if needed (stage 6: narrow the low end below the genre's mono-below frequency, widen highs if `analyze_stereo` shows narrow imaging. Check that correlation stays above +0.3)
8. Insert **ReaLimit** (stage 8: brickwall limiter -- set ceiling to -1.0 dBTP for streaming. Never 0 dBTP -- inter-sample peaks can exceed the ceiling. Set threshold to achieve target LUFS)
9. Apply dither if delivering 16-bit (stage 9 -- always the last stage, nothing after dither)

**LUFS targets:**
| Platform | Target LUFS | Ceiling |
|----------|-------------|---------|
| Spotify | -14 LUFS | -1.0 dBTP |
| Apple Music | -16 LUFS | -1.0 dBTP |
| YouTube | -14 LUFS | -1.0 dBTP |
| Tidal | -14 LUFS | -1.0 dBTP |

**TwelveTake shortcut:** `add_mastering_chain` inserts EQ -> Comp -> EQ -> Limiter in one call. Then adjust parameters per the measurements.

**Expected time:** ~2-3 seconds (10-15 Reaper MCP calls, or fewer with TwelveTake's compound tool)

**Measurement verification after:** Run `analyze_loudness` on the mastered output. Integrated LUFS should be within 0.5 LU of target. True peak should be below -1.0 dBTP. Run `compare_to_profile` to verify deviations decreased.

**See also:** `/phantom:mastering-engineer` complete mastering chain (stages 1-9), [ozone-guide.md](ozone-guide.md) for Ozone alternative, [format-targets.md](format-targets.md) for platform-specific delivery specs.

---

## mastering_chain_vinyl

**Trigger:** User requests vinyl/physical media delivery. Same analysis as streaming chain (`compare_to_profile`, `analyze_loudness`, `analyze_stereo`) plus awareness of vinyl's physical medium constraints.

**Goal:** Build a vinyl-optimized mastering chain that respects the physical limitations of vinyl cutting and playback.

**Undo Safety:** Create a Reaper undo point before starting.

**Steps:**
1. Create a dedicated mastering track or use the MIX BUS output (consider a separate vinyl master render -- don't just reuse the streaming master)
2. Insert **ReaEQ** -- high-pass at 30-40 Hz (vinyl can't reproduce extreme sub-bass; too much sub-bass causes groove spacing issues during cutting, wasting space on the lacquer and reducing playback time)
3. Insert **ReaEQ** -- corrective EQ per `compare_to_profile` deviations, same approach as streaming chain
4. Insert **ReaComp** -- broadband compression, ratio 1.5-2:1, 1-3 dB gain reduction for glue
5. Insert **ReaXcomp** -- multiband compression for problem frequencies
6. Insert **ReaEQ** -- tonal/additive EQ. Be cautious with high-frequency boosts above 15 kHz -- excessive high-frequency content can cause sibilance artifacts during vinyl cutting
7. Configure stereo imaging -- keep stereo width narrow below 300 Hz (mono below this frequency prevents groove cancellation. The cutting needle must track both channels simultaneously, and wide low-frequency content creates opposing groove movements that the stylus can't follow)
8. Insert **ReaLimit** -- ceiling at -0.5 dBTP (more headroom than streaming to account for vinyl pressing variability)
9. Target LUFS: -12 to -14 LUFS (vinyl has less dynamic range than digital but still more than streaming-loudness targets)
10. Apply dither if delivering 16-bit

**TwelveTake shortcut:** `add_mastering_chain` for initial chain, then adjust parameters for vinyl constraints.

**Expected time:** ~2-3 seconds (10-15 Reaper MCP calls, or fewer with TwelveTake's compound tool)

**Measurement verification after:** Run `analyze_loudness` -- verify LUFS is within -12 to -14 LUFS range. Run `analyze_stereo` -- verify low-end is mono-correlated below 300 Hz (correlation should be > +0.9 in the sub band). Run `analyze_spectrum` -- verify no excessive sub-bass below 30 Hz or extreme high-frequency content above 15 kHz.

**See also:** `/phantom:mastering-engineer` loudness targeting and reference-based mastering sections, [format-targets.md](format-targets.md) for vinyl delivery specs.
