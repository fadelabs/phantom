# Reaper Session Setup Recipes

Compound operation recipes for creating Reaper sessions from Phantom analysis results. Each recipe starts with a Phantom measurement trigger and describes step-by-step outcomes to achieve in Reaper. Steps describe what to do, not which API to call -- Claude adapts to whichever Reaper MCP server is connected.

> **Requires a Reaper MCP server.** See the [setup guide](../../docs/workflows/setup-guide.md) for installation.

## setup_metal_session

**Trigger:** User requests rock/metal session. `batch_diagnostic` results available for all stems. `compare_to_profile(mix, "rock-metal")` or `compare_to_profile(mix, "metal")` shows reference deviations.

**Goal:** Create a complete Reaper session following the Rock/Metal template from [session-templates.md](session-templates.md) with tracks, folders, colors, routing, and initial FX.

**Undo Safety:** Create a Reaper undo point before starting. If any step fails, undo returns to empty session.

**Steps:**
1. Create folder track "DRUMS" (color: red). Create child tracks: Kick In, Kick Out, Snare Top, Snare Bottom, Hi-Hat, Toms (x2-3), OH L, OH R, Room L, Room R
2. Create folder track "BASS" (color: blue). Create child tracks: Bass DI, Bass Amp
3. Create folder track "GUITARS" (color: green). Create child tracks: Rhythm L, Rhythm R, Rhythm L2, Rhythm R2, Lead, Clean
4. Create folder track "VOCALS" (color: yellow). Create child tracks: Lead Vox, Harmony 1, Harmony 2, Doubles, Ad-libs
5. Create folder track "KEYS/SYNTHS" (color: purple). Create child tracks as needed from stems
6. Create folder track "FX RETURNS" (color: orange). Create child tracks: Room Verb, Plate Verb, Slap Delay, Long Delay
7. Create "MIX BUS" track at the end (receives all folder outputs)
8. Import stem WAV files to matching tracks by name
9. Set project sample rate to match stems (from `batch_diagnostic` sample rate field)
10. Add sidechain send from Kick In to Bass DI (channels 3-4) for low-end clarity
11. Insert **ReaEQ** on each folder track (subtractive EQ starting point)
12. Insert **ReaComp** on DRUMS and VOCALS folder tracks

**TwelveTake shortcut:** No single compound tool -- use track creation and FX operations sequentially. `create_bus` helps with FX returns.

**Expected time:** ~2-4 seconds (30-50 Reaper MCP calls at ~50ms each)

**Measurement verification after:** Run `batch_diagnostic` on imported stems to confirm they loaded correctly. Verify stem count matches expected track count.

**See also:** [session-templates.md](session-templates.md) for full track hierarchy, [reaper-setup.md](reaper-setup.md) for Reaper routing details.

---

## setup_pop_session

**Trigger:** User requests pop session. `batch_diagnostic` results available for all stems.

**Goal:** Create a Pop template session from [session-templates.md](session-templates.md). Pop sessions are vocal-forward with polished, wide, bright production.

**Undo Safety:** Create a Reaper undo point before starting. If any step fails, undo returns to empty session.

**Steps:**
1. Create folder track "VOCALS" (color: yellow) -- priority, built first. Create child tracks: Lead Vocal, Lead Vocal Double, Harmony High, Harmony Low, Backing Vocals, Ad-libs, Vocal Chops/Effects
2. Create folder track "DRUMS" (color: red). Create child tracks: Kick, Snare, Hi-Hat, Percussion/Shaker, Drum Loop/Programmed
3. Create folder track "BASS" (color: blue). Create child tracks: Bass (DI or synth), Sub Bass
4. Create folder track "KEYS/SYNTHS" (color: orange). Create child tracks: Piano, Synth Pad, Synth Lead, Arpeggiated Synth
5. Create folder track "GUITARS" (color: green). Create child tracks: Acoustic, Electric (if present in stems)
6. Create folder track "FX RETURNS" (color: purple). Create child tracks: Plate Verb, Room Verb, Hall Verb, Slapback Delay, Dotted-Eighth Delay, Vocal Throw Delay, Parallel Vocal Comp
7. Create "MIX BUS" track at the end
8. Import stem WAV files to matching tracks by name
9. Set project sample rate to match stems
10. Set up a dedicated vocal bus compression chain -- lead vocal gets its own parallel compression send
11. Insert **ReaEQ** on each folder track

**TwelveTake shortcut:** No single compound tool -- use track creation and FX operations sequentially. `create_bus` helps with FX returns.

**Expected time:** ~2-3 seconds (20-40 Reaper MCP calls at ~50ms each)

**Measurement verification after:** Run `batch_diagnostic` on imported stems to confirm correct loading. Verify vocal tracks are routed through the vocal bus.

**See also:** [session-templates.md](session-templates.md) for full Pop track hierarchy, [reaper-setup.md](reaper-setup.md) for Reaper routing details.

---

## setup_hiphop_session

**Trigger:** User requests hip-hop/trap session. `batch_diagnostic` results available for all stems.

**Goal:** Create a Hip-Hop/Trap template session from [session-templates.md](session-templates.md). The 808/kick relationship is everything. Vocal clarity is paramount.

**Undo Safety:** Create a Reaper undo point before starting. If any step fails, undo returns to empty session.

**Steps:**
1. Create folder track "DRUMS" (color: red). Create child tracks: Kick/808 Kick, 808 Sub Bass, Snare/Clap, Hi-Hat, Percussion/Shaker, Open Hat
2. Create folder track "BASS" (color: blue). Create child tracks: 808 (if separate from drums), Bass Synth
3. Create folder track "MELODICS" (color: orange). Create child tracks: Melody Loop, Counter Melody, Pad/Atmosphere, Piano/Keys, Guitar (if present)
4. Create folder track "VOCALS" (color: yellow). Create child tracks: Lead Vocal, Lead Vocal Double, Ad-libs, Backing Vocals, Vocal Effects/Chops
5. Create folder track "FX RETURNS" (color: purple). Create child tracks: Plate Verb (subtle), Room Verb (very short), Quarter Note Delay, Vocal Throw, Distortion Bus (parallel)
6. Create "MIX BUS" track at the end
7. Import stem WAV files to matching tracks by name
8. Set project sample rate to match stems
9. Keep 808 and kick on separate tracks even if they came from the same beat -- independent processing is essential
10. Add heavy sidechain send from kick to 808 sub bass (channels 3-4) -- duck 808 when kick hits
11. Insert **ReaEQ** on vocal track with high-pass at 80 Hz, cut competing instruments at 2-4 kHz to make room for vocals

**TwelveTake shortcut:** `setup_sidechain_compression` handles the kick-to-808 sidechain routing. `create_bus` helps with FX returns.

**Expected time:** ~2-3 seconds (20-40 Reaper MCP calls at ~50ms each)

**Measurement verification after:** Run `batch_diagnostic` on imported stems. Run `multi_stem_masking` between kick and 808 to verify sidechain is needed (confirms the routing decision).

**See also:** [session-templates.md](session-templates.md) for full Hip-Hop/Trap track hierarchy, [reaper-setup.md](reaper-setup.md) for sidechain routing via channels 3-4.

---

## setup_electronic_session

**Trigger:** User requests electronic/EDM session. `batch_diagnostic` results available for all stems.

**Goal:** Create an Electronic/EDM template session from [session-templates.md](session-templates.md). Synth-heavy with sidechain as a groove tool. Multiple effect layers.

**Undo Safety:** Create a Reaper undo point before starting. If any step fails, undo returns to empty session.

**Steps:**
1. Create folder track "DRUMS" (color: red). Create child tracks: Kick, Snare/Clap, Hi-Hat (closed, open), Percussion, Drum Loop/Break
2. Create folder track "BASS" (color: blue). Create child tracks: Sub Bass, Mid Bass/Reese, Bass FX/Growl
3. Create folder track "SYNTHS" (color: orange). Create child tracks: Lead Synth, Pad, Pluck/Arp, Atmosphere/Texture, FX/Risers/Impacts
4. Create folder track "VOCALS" (color: yellow, if present). Create child tracks: Lead Vocal, Vocal Chops, Vocal FX
5. Create folder track "FX RETURNS" (color: purple). Create child tracks: Hall Reverb (big), Room Reverb (tight), Ping-Pong Delay, Synced Delay, Filter Sweep Bus, Parallel Distortion
6. Create "MIX BUS" track at the end
7. Import stem WAV files to matching tracks by name
8. Set project sample rate to match stems
9. Add sidechain sends from kick to bass, pads, and synths (channels 3-4) -- sidechain everything to the kick is the EDM groove
10. Configure multiple sidechain depths: bass ducks hard (-6 dB), pads duck medium (-3 dB), leads duck subtle (-1 dB)
11. Insert **ReaEQ** on bass folder -- mono everything below 100-150 Hz (club systems are mono in the sub)

**TwelveTake shortcut:** `setup_sidechain_compression` handles each sidechain routing. `create_bus` helps with FX returns.

**Expected time:** ~2-3 seconds (25-45 Reaper MCP calls at ~50ms each)

**Measurement verification after:** Run `batch_diagnostic` on imported stems. Run `analyze_stereo` on bass tracks to verify low-end is mono-correlated below 150 Hz.

**See also:** [session-templates.md](session-templates.md) for full Electronic/EDM track hierarchy, [reaper-setup.md](reaper-setup.md) for sidechain routing and plugin reference.

---

## setup_from_diagnostic

**Trigger:** `batch_diagnostic` completed and mix brief available from `/phantom:audio-diagnostician`. No genre specified -- adapt based on stem types found.

**Goal:** Create a session adapted to the actual stems present. Auto-detect the closest genre/template from stem names and analysis results, then build the session accordingly.

**Undo Safety:** Create a Reaper undo point before starting. If any step fails, undo returns to empty session.

**Steps:**
1. Read the mix brief stem list from `batch_diagnostic` results. Note stem names, sample rates, and any flagged problems.
2. Choose the closest genre template based on stem types found:
   - Electric guitars + live drums + bass DI/amp = Rock/Metal
   - Heavy vocal tracks + synths + programmed drums = Pop
   - 808/sub bass + vocal tracks + melody loops = Hip-Hop/Trap
   - Synth layers + electronic drums + risers/impacts = Electronic/EDM
   - Acoustic instruments + minimal processing = Acoustic/Folk
3. Create folder structure matching available stems using the chosen template. Skip template tracks that have no matching stem.
4. Color code folders per the standard scheme (Drums: red, Bass: blue, Guitars: green, Vocals: yellow, Keys/Synths: orange, FX Returns: purple)
5. Import all stems to their matching tracks
6. Set project sample rate to match stems (flag if stems have mismatched sample rates)
7. Add sidechain routing if kick and bass stems are present
8. Insert **ReaEQ** on each folder track as a starting point

**Note:** When no genre is specified, use Rock/Metal template as the most comprehensive starting point (as noted in [session-templates.md](session-templates.md)) and strip out tracks that don't have matching stems.

**TwelveTake shortcut:** No single compound tool -- use track creation and FX operations sequentially.

**Expected time:** ~2-4 seconds (30-50 Reaper MCP calls at ~50ms each)

**Measurement verification after:** Run `batch_diagnostic` on imported stems to confirm they loaded correctly. Verify stem count matches track count. Check for sample rate mismatches flagged during import.

**See also:** [session-templates.md](session-templates.md) for all genre templates, [reaper-setup.md](reaper-setup.md) for Reaper-specific setup details, `/phantom:audio-diagnostician` for mix brief generation.

---

## Reaper MCP Known Issues

Issues discovered during real sessions. Items marked **Fixed** were resolved in the Phantom-patched Lua bridge and no longer require workarounds.

### insert_audio_file track targeting
**Status:** Fixed.
The upstream `InsertMedia` raw API call ignores the `track_index` parameter and always inserts on the first track. Phantom's `setup_reaper` command patches the Lua bridge to add an `InsertAudioFile` DSL function that correctly targets specific tracks using `AddMediaItemToTrack` + `PCM_Source_CreateFromFile` + `SetMediaItemTake_Source` in a single Lua call.

### insert_track name parameter
**Status:** Fixed (arg-order bug corrected).
The `name` parameter on `insert_track` previously set the name on the wrong track due to an extra argument in the MCP server call. This is fixed, but Reaper may still overwrite track names on audio import. **Best practice:** call `set_track_name` separately after `insert_track` when importing audio onto the same track.

### MIDI note insertion
**Status:** Fixed.
The Lua bridge now resolves track index → media item → active take within Lua itself, avoiding the pointer serialization problem. `add_midi_note` and `add_midi_notes_batch` work correctly through the file bridge.

### Item manipulation (split, move, set position/length)
**Status:** Fixed.
`split_item`, `set_item_position`, `set_item_length`, `set_item_volume`, `set_item_mute`, `set_item_fade_in`, `set_item_fade_out` all resolve track → item within the Lua bridge. No pointer serialization issue.

### Envelope automation
**Status:** Fixed.
`add_envelope_point`, `get_envelope_points`, `delete_envelope_point`, `clear_envelope`, and `arm_track_envelope` all resolve track → envelope by name within the Lua bridge. Volume, pan, and mute automation can be written programmatically.

### Peak metering
**Status:** Fixed.
`get_track_peak` resolves the track pointer within the Lua bridge. Returns both linear and dB values. Note: peak values are instantaneous snapshots — for reliable level measurement, render to WAV and analyze with Phantom MCP tools.

### Rendering
**Status:** Fixed.
`render_project` configures render settings (output path, bounds, tail) and triggers Reaper's auto-close render action. The audio format uses the project's current render format settings — verify format in Reaper's render dialog (Cmd+Alt+R) if needed. `render_region` renders a specific region by looking up its time bounds and rendering that range.

### FX parameter verification
**Issue:** Some plugins (notably iZotope Ozone 11 Maximizer) have internal parameter linking that overrides MCP-set values. Setting the Maximizer ceiling via param 119/122 gets reset by the linked input gain. **Workaround:** Set link param to 0 first, or instruct the user to set these values in the plugin GUI.

### Project tempo and audio files
**Issue:** Changing project tempo with `set_tempo` may timestretch audio items if Reaper's timestretch mode is enabled. **Always verify:** check if audio items have timestretch enabled before changing tempo. If BPM detection shows a different tempo than the project default (120), set delay/effect timing manually using absolute time values rather than changing the project tempo.
