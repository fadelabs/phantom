# Reaper Mixing Recipes

Compound operation recipes for common mixing tasks in Reaper, driven by Phantom analysis measurements. Each recipe starts with a Phantom measurement trigger and describes step-by-step outcomes. Steps describe what to do, not which API to call -- Claude adapts to whichever Reaper MCP server is connected.

> **Requires a Reaper MCP server.** See the [setup guide](../../docs/workflows/setup-guide.md) for installation.

## create_vocal_chain

**Trigger:** Vocal stem identified in `batch_diagnostic`. `detect_problems` may show sibilance, dynamic range issues. `analyze_dynamics` shows crest factor and RMS.

**Goal:** Build a professional vocal processing chain on the vocal track.

**Undo Safety:** Create a Reaper undo point before starting.

**Steps:**
1. Identify the lead vocal track by name
2. Insert **ReaEQ** -- high-pass at 80 Hz (remove rumble), cut at 200-300 Hz if `detect_problems` shows mud, presence boost at 3-5 kHz if `analyze_spectrum` shows dull vocal
3. Insert **ReaComp** -- ratio 3:1, attack 10-20 ms (preserve transients), release 100-150 ms, threshold set to catch peaks (aim for 3-6 dB gain reduction)
4. Insert de-esser (if `detect_problems` shows sibilance) -- target 5-8 kHz, gentle ratio
5. Insert **ReaEQ** (second instance) -- additive "air" boost at 10-12 kHz shelf if needed
6. Insert **ReaDelay** on send -- short slap delay (80-120 ms, one repeat) for depth
7. Set up reverb send to the session's plate reverb return

**TwelveTake shortcut:** No single compound tool -- use sequential FX operations.

**Expected time:** ~1-2 seconds (8-12 Reaper MCP calls at ~50ms each)

**Measurement verification after:** Run `analyze_spectrum` on the vocal track. Compare before/after spectral shape. Run `analyze_dynamics` to confirm compression is working (crest factor should decrease by 2-4 dB).

**See also:** `/phantom:mix-engineer` EQ and compression sections, [reaper-setup.md](../session-architect/reaper-setup.md) for plugin parameters.

---

## sidechain_bass_to_kick

**Trigger:** `multi_stem_masking` shows HIGH masking between kick and bass at 60-100 Hz (masking_severity "high" in the sub/low bands).

**Goal:** Duck bass sub-frequencies when the kick hits, creating separation without EQ cuts.

**Undo Safety:** Create a Reaper undo point before starting. TwelveTake's `setup_sidechain_compression` wraps in undo block natively.

**Steps:**
1. Identify the kick and bass tracks by name
2. Add a send from the kick track to the bass track on channels 3-4
3. Insert **ReaComp** on the bass track (if not already present)
4. Configure **ReaComp**: ratio 4:1, attack 0.5 ms, release 100 ms, threshold to taste (-20 to -30 dBFS)
5. Set **ReaComp** detector input to auxiliary channels 3-4
6. Verify by soloing bass -- should duck rhythmically with the kick

**TwelveTake shortcut:** `setup_sidechain_compression` does steps 2-5 in a single call.

**Expected time:** ~1-2 seconds (3-5 Reaper MCP calls, or 1 call with TwelveTake's compound tool)

**Measurement verification after:** Run `multi_stem_masking` between kick and bass again -- masking severity should decrease at 60-100 Hz.

**See also:** `/phantom:mix-engineer` sidechain compression section, [reaper-setup.md](../session-architect/reaper-setup.md) for channel routing details.

---

## parallel_drum_compression

**Trigger:** `analyze_dynamics` on drum bus shows high crest factor (>12 dB) -- drums have punch but lack sustain/body. Or user requests "fatter drums" / "more drum energy."

**Goal:** Add parallel (New York) compression to drums -- heavy compression blended underneath the dry signal for body without killing transients.

**Undo Safety:** Create a Reaper undo point before starting.

**Steps:**
1. Identify the DRUMS folder track
2. Create a new track "Drum Parallel" adjacent to the drums folder
3. Add a send from DRUMS folder to Drum Parallel (pre-fader)
4. Insert **ReaComp** on Drum Parallel: ratio 10:1, attack 1-3 ms (fast), release 30-50 ms, threshold low enough for 10-15 dB gain reduction (heavy squash)
5. Set Drum Parallel fader to -inf initially
6. Slowly bring up Drum Parallel fader until the drums gain body without losing transient punch (typically -6 to -12 dB below main drums)

**TwelveTake shortcut:** `add_parallel_compression` creates the send, bus, and heavy compression in one call.

**Expected time:** ~1 second (3-5 Reaper MCP calls, or 1 call with TwelveTake)

**Measurement verification after:** Run `analyze_dynamics` on drum bus output. Crest factor should decrease by 2-4 dB. RMS should increase slightly.

**See also:** `/phantom:mix-engineer` parallel compression section.

---

## complementary_eq_pair

**Trigger:** `multi_stem_masking` or `analyze_masking` shows HIGH masking between two stems in a specific frequency band (e.g., guitars and vocals competing at 2-4 kHz).

**Goal:** Apply complementary EQ -- cut the competing frequency in one stem, boost it in the other -- so both elements are clear without volume fights.

**Undo Safety:** Create a Reaper undo point before starting.

**Steps:**
1. Identify the two competing tracks from the masking analysis
2. Determine which track "owns" the contested frequency range (e.g., vocals own 2-4 kHz presence, guitars should yield)
3. On the yielding track: Insert or modify **ReaEQ** -- cut 2-3 dB at the contested center frequency with moderate Q (1.5-2.5)
4. On the owning track: Insert or modify **ReaEQ** -- gentle boost 1-2 dB at the same frequency (optional, only if needed)
5. Both EQ moves should be subtle (2-3 dB) -- if you need more, the arrangement has a problem EQ can't fix

**TwelveTake shortcut:** No single compound tool -- use FX parameter setting operations.

**Expected time:** ~1 second (4-6 Reaper MCP calls)

**Measurement verification after:** Run `multi_stem_masking` between the two stems again. Masking severity in the contested band should drop from "high" to "moderate" or "low."

**See also:** `/phantom:mix-engineer` complementary EQ section.

---

## vocal_level_calibration

**Trigger:** Vocals sound too loud or too quiet relative to instruments after FX chain is applied. User adjusts fader manually.

**Goal:** Set the correct vocal fader position relative to the rest of the mix, accounting for FX chain gain changes.

**Undo Safety:** Create a Reaper undo point before starting.

**Steps:**
1. Bypass ALL FX on the vocal track temporarily
2. Set the vocal fader to 0 dB
3. Play back — ask the user if the raw vocal level feels right relative to instruments
4. If too loud, note how many dB the user pulls it down. This is the "raw balance" offset.
5. Re-enable FX one at a time, checking level after each:
   - Enable EQ — if level drops significantly, the EQ is cutting too much. Reduce cuts or add output gain.
   - Enable Compressor — with auto-gain on, level should stay roughly the same. If it drops, auto-gain isn't compensating enough.
   - Enable Exciter/Saturation — should add a small amount of perceived loudness. If it drops level, check the plugin's output gain.
6. After all FX are re-enabled, adjust the fader to compensate for any cumulative gain change.

**Critical learning:** Neutron 4 EQ gain scale uses 0.6667 = 0 dB, NOT 0.25 like ReaEQ. Setting Neutron EQ gain to values like 0.55 or 0.58 (which look like "small cuts") actually creates -4 to -5 dB cuts. Small-sounding normalized values can mean large gain changes. **Always verify by ear after setting iZotope plugin parameters.**

**iZotope vs Reaper plugin parameter scaling:**
| Plugin | 0 dB Gain | Scale |
|--------|-----------|-------|
| ReaEQ | 0.25 | 0-0.5 maps to -18 to +18 dB |
| Neutron 4 EQ | 0.6667 | 0-1 maps to roughly -18 to +9 dB |
| Neutron 4 Compressor threshold | 1.0 | 1.0 = no compression (threshold at max) |
| Ozone Maximizer output | ~0.94 | ~0.94 = -1 dBTP ceiling |

**Measurement verification after:** Render vocal solo to WAV, run `full_diagnostic` and `compare_to_reference` against raw stem to verify the FX chain isn't eating signal.
