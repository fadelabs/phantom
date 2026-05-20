---
name: session-architect
description: >
  Session setup methodology for Reaper DAW. Guides track hierarchy,
  bus routing, send/receive configuration, sidechain setup, and
  genre-specific session templates. Use this skill whenever the user
  wants to set up a new mixing session, organize tracks into folders
  and buses, create routing for sends and returns, build a session
  from a genre template, configure sidechain compression routing,
  set up color coding and naming conventions, or prepare render
  settings. Also use when the user has a mix brief from
  /phantom:audio-diagnostician and needs to translate diagnostic
  findings into session architecture decisions, or when they ask
  about Reaper-specific track setup, folder structures, or plugin
  routing -- even if they don't say "session setup" explicitly.
---

# Session Architect

> **Workflow position:** diagnostician → **session-architect** → mix-engineer → effects-engineer → mastering-engineer

A well-organized session is half the mix. Engineers waste hours hunting for tracks and debugging routing when they skip the 15-minute setup. A clean session means you make mixing decisions instead of solving signal path problems.

**Non-negotiable rules (repeated at end as final checklist):**
1. Fix it before you mix it — clean tracks, resolve edits, comp vocals BEFORE building the session
2. Read the mix brief first — diagnostic findings dictate routing decisions
3. Color and name every track — "Audio 1" helps nobody, including future you
4. Start sends at -inf — bring up to taste during mixing, never default to 0 dB

## Step 1: Session Preparation (Before Any Routing)

### Fix It Before You Mix It

Production decisions should not compete with mix decisions. Complete these before building the session:

**When time is tight** (client in the room, studio clock running): tier your prep. Do dealbreakers immediately — comps, polarity checks, sample rate matching. Defer nice-to-haves (fades, trimming silence, consolidating) to a cleanup pass after the rough balance. Tell the client what you're doing and why: "I need 10 minutes to lock the vocal comp and check phase on the drums — if I skip this, we'll lose an hour debugging it later." This reframes prep as time-saving, not time-wasting.

| Task | What to Do | Why |
|------|-----------|-----|
| **Comp vocals** | Select best takes, build final vocal | Choosing takes mid-mix degrades both tasks |
| **Tune if needed** | Pitch correction on comped vocal | Must happen before processing — correcting pitch on compressed/distorted audio creates artifacts |
| **Trim heads/tails** | Remove dead air before and after every performance | Accumulated silence = accumulated noise floor |
| **Fade every edit** | 5-10 ms crossfade at every cut point | Inaudible now, but compression during mixing will reveal clicks |
| **Eliminate noise** | Count-offs, chair squeaks, headphone bleed, amp buzz between phrases | Fix it now or debug it later when it's harder to find |
| **Consolidate** | Single continuous clip per track after editing is locked | Visually clean, can't accidentally shift edit fragments |
| **Delete unused** | Hide/deactivate tracks that won't be in the final mix | Screen space and mental bandwidth are limited resources |

### Read the Mix Brief

If audio-diagnostician produced a brief, extract:
- **Stem count and names** — determines track layout
- **Sample rate and bit depth** — set project to match (don't let Reaper resample on import)
- **Dealbreaker problems** — stems with phase issues need routing that facilitates polarity flips and time alignment
- **Masking conflicts** — knowing that kick and bass fight at 60-100 Hz means prewiring sidechain routing, not discovering you need it mid-mix. When the brief lists multiple masking pairs, map ALL of them to routing simultaneously (see "Wiring multiple findings" below)
- **Mixed sample rates** — if stems arrive at different sample rates, set the project to the highest rate present. Import lower-rate stems and let Reaper resample up (Project Settings → Media → resample mode: use "sinc 512 point" for transparent quality). Never resample down to match the lowest rate
- **Monitoring setup** — set up a monitoring section on the mix bus: mono check (utility plugin or Reaper's channel routing to sum L+R), dim button (-20 dB), and a reference track routed directly to hardware output (bypasses mix bus processing)
- **Headphone feeds for tracking** — when the session doubles as a tracking session (overdubs during mixing), route headphone mixes on separate hardware outputs (e.g., outputs 3-4). Create a dedicated "HP Mix" bus with independent sends from each track. This bus must NOT feed the mix bus — route it directly to the headphone amp output. The performer's headphone mix is independent of your monitor mix.

If no brief exists, run `batch_diagnostic` on all stems before building the session.

## Step 2: Choose and Adapt a Template

Pick the genre template closest to the project from [session-templates.md](session-templates.md).

### When to Deviate from Templates

| Situation | Adaptation |
|-----------|-----------|
| No drums (electronic, ambient) | Remove drum folder, keep bus structure for synths/samples |
| Orchestral instruments | Start from rock template (most comprehensive), rename guitar → strings, add woodwind/brass folders |
| 10 stems or fewer | Flatten hierarchy — skip sub-folders, single instrument bus is enough |
| 40+ stems | Add sub-buses within groups (drum overheads bus, background vocals bus) |
| 80+ stems | Full sub-bus hierarchy with VCA groups for section control |
| Pre-printed effects (reverb/delay baked in) | Do NOT send these stems to shared reverb/delay returns — doubling printed effects sounds washy. Route pre-printed stems to a dedicated "Wet Stems" sub-bus. Process separately (EQ, compression only). Keep an unprocessed copy on a muted reference track for A/B. If more spatial effect needed, use only short ambiance (< 0.8s) blended sparingly. |
| Live session with bleed | Bleed is the glue — do NOT gate it out. Route all mics from a single source (e.g., drum kit) to a sub-bus. Insert a polarity/time-alignment chain: use track delay per mic to align transients to the close mic, then check polarity. Process the sub-bus as a unit. Skip individual compression on room/ambient mics since bleed makes it pump unpredictably. |
| CPU/performance (50+ tracks) | Freeze tracks you're not actively tweaking. At 80+, consider splitting into stem-group sub-sessions. Set buffer to 512+ samples during mixing. |
| Mid-mix expansion (artist adds tracks) | Insert new tracks into the existing folder hierarchy — don't append at the bottom. Gain-stage new tracks to -18 dBFS via clip gain. Verify existing sidechain sends still trigger correctly (new track insertion can shift track indices in Reaper, breaking send routing). Re-query `get_project_summary` after any structural change. |
| Multi-format delivery (stereo + stems + surround) | Architect from the start: keep instrument group buses clean (no master bus processing baked in) so each bus can render as an independent stem. For surround, add a 5.1 bus parallel to the stereo mix bus, fed by the same group buses. For sync licensing stems, ensure each group bus can solo-render cleanly. Set up render presets (File → Render → Presets) for each delivery format. |

### Stem Count Scaling

| Stem Count | Architecture Complexity | Key Adjustments |
|-----------|------------------------|-----------------|
| 5-10 | Flat — minimal folders | One bus per group, 2 FX returns (verb + delay) |
| 10-25 | Standard — folder per group | Standard template, 3-4 FX returns |
| 25-50 | Dense — sub-buses within groups | Add drum sub-bus (shells vs cymbals), vocal sub-bus (lead vs BG). 4-6 FX returns. |
| 50-80 | Complex — full hierarchy | Sub-buses everywhere, VCA groups for section-level control, 6+ FX returns |
| 80+ | Production-scale | Consider splitting into stem-group sessions for performance |

**Complexity override:** stem count is a starting heuristic, not a rule. A 15-stem session with 8 individual drum mics needs drum-complex architecture (sub-buses for shells vs cymbals, phase alignment chain) even though overall count says "flat." Scale complexity to the most demanding instrument group, not the total.

### Track Templates vs Session Templates

Save a "session start" snapshot (File → Save As with version suffix, e.g., `Song_v01_session-start.rpp`) before any processing. During mixing, save versioned snapshots at each major milestone: rough balance, EQ pass, compression pass, automation. For client revisions, always branch from the last approved version — never overwrite it. Keep a `_notes.txt` logging what changed per version.

**Track templates** save a per-instrument channel strip (EQ → comp → sends chain) as a reusable preset. **Session templates** save the full hierarchy and routing. Use both: session template builds the skeleton, then apply track templates to speed up individual channel setup. In Reaper: right-click a configured track → "Save track as track template." When inserting, the template includes FX chain and send configuration but adapts to the current session's bus structure.

## Step 3: Build the Track Hierarchy

Reaper's folder tracks serve double duty: visual grouping AND audio bus. A track set as a folder automatically sums its children — put a compressor on the folder and it's a bus compressor. This is Reaper's superpower.

**Standard layout** (adapt per genre — see [session-templates.md](session-templates.md) for specifics):

```
DRUMS (red)       — Kick, Snare, Toms, OH, Room
BASS (blue)       — DI, Amp
GUITARS (green)   — Rhythm L/R, Lead, Clean/Acoustic
VOCALS (yellow)   — Lead, Harmonies, BGs, Ad-libs
KEYS/SYNTHS (orange) — Piano, Organ, Pads, Leads
FX RETURNS (purple) — Verbs, Delays, Parallel buses
MIX BUS (master parent)
```

**Track order:** The specific order matters less than consistency. Pick an order and use it on every session so your eyes always know where to look.

> **Requires a Reaper MCP server** for automated track creation.
> See the [setup guide](../../docs/workflows/setup-guide.md) for installation.

## Step 4: Set Up Auxiliary Channels

### Effects Returns

Pre-build before mixing so creative flow isn't interrupted. **Verify each return:** after setup, send a test signal (solo a track, raise its send to -6 dB) and confirm the return's meter shows signal. If the return meter is silent, the send routing is wrong.

| Return | Type | Purpose | Starting State |
|--------|------|---------|---------------|
| Room verb | Short (0.5-1.5s), natural | Drums, keeping things grounded | Send at -inf, bring up to taste |
| Plate verb | Medium (1.5-2.5s), vocal-friendly | Vocals, snare, melodic instruments | Send at -inf |
| Long delay | Quarter or dotted-eighth, 3-5 repeats | Vocal phrases, guitar leads | Send at -inf |
| Slapback delay | 50-120 ms, single repeat | Vocal thickening, guitar character | Send at -inf |
| Parallel comp | Heavy compression (10:1+) | Drums, vocals (blend underneath dry) | Fader at -inf, bring up to taste |

**All send levels start at -inf.** Never at 0 dB — that's the maximum, not the default. All effect plugins on returns must be **100% wet** — dry signal mixed in on return = comb filtering.

### Conditional Routing from Diagnostics

Translate diagnostic findings into routing decisions. **When the artist/producer vetoes a diagnostic recommendation** (e.g., "no sidechain ducking on my bass"), respect creative direction — it's their record. Find an alternative: dynamic EQ on the bass at the conflicting frequency, complementary static EQ cuts, or arrangement-level changes. Document the override in your session notes: what was recommended, what was vetoed, what alternative was used, and why.

| Diagnostic Finding | Routing Decision |
|-------------------|-----------------|
| *(Artist vetoes recommended routing)* | Respect creative direction. Use alternative processing (dynamic EQ, static EQ, arrangement). Document the override. |
| Kick/bass masking (60-100 Hz) | Prewire sidechain: kick → bass on channels 3-4 |
| Phase issues on multi-mic source | Route close and room mics to a sub-bus for time-alignment processing |
| Guitar/vocal masking (2-4 kHz) | Route guitars through a bus with sidechain from vocal (subtle ducking) |
| Over-compressed stems (crest < 6 dB) | Skip compression insert, mark track as "no comp needed" |
| Severe noise on specific stems | Insert gate as first plugin on those tracks |
| Stereo correlation < +0.3 on a stem | Route to a sub-bus with M/S processing for correction |

#### Wiring Multiple Findings Simultaneously

A real mix brief rarely has just one finding. When wiring multiple diagnostic findings:

1. **Map all findings first, build second.** Read every finding and note the routing it requires before creating tracks. Findings interact: kick/bass sidechain AND drum phase issues both affect the drum bus structure.
2. **Build order:** Create sub-buses for phase/alignment issues first (these affect signal path), then add sidechain routing (sends layered on top), then insert processing chains last.
3. **Example — three simultaneous findings:** Kick/bass masking + guitar/vocal masking + drum phase issues. Build the drum sub-bus first for phase alignment. Then add kick → bass sidechain on channels 3-4. Then add vocal → guitar bus sidechain on channels 3-4 (separate send). Three findings, three routing actions, no conflicts because each operates on different signal paths.

## Step 5: Configure Sidechain Routing

In Reaper, sidechain signals travel on channels 3-4 (conventional — plugins expect this).

**Plugin-specific sidechain channels:** Channels 3-4 is the Reaper/ReaComp convention, but third-party plugins vary. FabFilter Pro-C 2 reads sidechain on channels 1-2 by default. Waves C1 uses 3-4. Always check the plugin's sidechain input assignment. **Verify with a test signal:** solo the source, confirm the destination's compressor gain reduction meter moves in time with the source transients. If it doesn't respond, the sidechain channel assignment is wrong.

**Standard sidechain setup:**
1. Source track (e.g., kick): add send to destination track (e.g., bass)
2. Set send to channels 3-4 (not 1-2)
3. On destination's compressor (ReaComp): set detector input to auxiliary channels 3-4
4. For frequency-dependent sidechaining: HPF the sidechain input at 80-100 Hz so only sub frequencies duck
5. **Latency check:** sidechain sends through plugins with high latency can misalign the trigger with the audio. After setup, zoom into the waveform and verify the ducking aligns with the kick transient. If it's late, enable Reaper's plugin delay compensation (Options → Preferences → Audio → Buffering → "Allow anticipative FX processing") or reduce the plugin's lookahead/oversampling.

**Common sidechain patterns:**

| Source → Target | Amount | Purpose |
|----------------|--------|---------|
| Kick → Bass | 3-6 dB, fast attack/release | Low-end clarity (THE critical sidechain setup) |
| Vocal → Guitar bus | 1-2 dB, slow attack | Guitars subtly yield to vocal |
| Vocal → Reverb return | 3-6 dB, medium attack | Ducked reverb — clarity during singing, bloom in gaps |
| Kick → Synth pads | 1-3 dB, fast attack | Rhythmic pumping (EDM groove) |

### Multi-Target Sidechain (One Source → Multiple Destinations)

A single source can sidechain multiple targets simultaneously. In Reaper, each send is independent.

**Setup for kick → bass AND kick → synth pad:**
1. On kick track, create Send #1 → bass track, channels 3-4
2. On kick track, create Send #2 → synth pad bus, channels 3-4
3. Each destination gets its own compressor with independent settings: bass gets 3-6 dB fast duck; synth pad gets 1-3 dB for rhythmic pump
4. No limit to sidechain sends from one source. When a vocal needs to duck guitars, reverb, AND delay simultaneously, add three sends from the vocal, all on channels 3-4, each destination tuned independently.

## Step 6: Section Markers and Navigation

Mark every section of the song. Place markers 1-2 bars before each section change for pre-roll:

| Marker | Position |
|--------|----------|
| Intro | Bar 1 (or wherever it starts) |
| Verse 1 | Before first verse |
| Pre-chorus | Before pre-chorus |
| Chorus 1 | Before first chorus |
| Bridge | Before bridge |
| Outro | Before outro |
| Key moments | Drum fills, breakdowns, key changes, solos |

These become your navigation system during mixing and drastically speed up revision passes.

## Step 7: Gain Staging

Before any processing: set all faders to unity (0 dB). Use item/clip gain to target -18 dBFS average per channel (0 VU = -18 dBFS — where most analog-modeled plugins are calibrated). **Verification:** after staging, play the loudest section of the song. Group bus meters should peak around -10 to -6 dBFS with faders at unity. If buses are hitting 0, individual tracks are too hot — pull clip gain down.

**Never use faders for gain staging** — reserve them for mix balance. If a stem is significantly hot or quiet, adjust at the source (clip gain), not the fader.

**Non-mixing elements** (reference tracks, click tracks, talkback mics) do NOT follow gain staging rules. Reference tracks should stay at their original level for meaningful A/B comparison — route them directly to hardware output, bypassing the mix bus entirely. Mark them with a distinct color (white or gray) and name prefix ("REF:") so they're never confused with mix elements.

## Color Coding and Naming

Consistency matters more than the specific scheme. Use the same colors across every session:

| Group | Color | Track Naming |
|-------|-------|-------------|
| Drums | Red | "Kick In", "Snare Top", "OH L" |
| Bass | Blue | "Bass DI", "Bass Amp" |
| Guitars | Green | "Rhythm L", "Lead", "Acoustic" |
| Vocals | Yellow | "Lead Vox", "Harm Hi", "BG Vox" |
| Keys/Synths | Orange | "Piano", "Pad", "Synth Lead" |
| FX Returns | Purple | "Plate Verb", "Slap DLY", "Par Comp" |

Names should tell anyone what the track is without soloing it.

## Reaper MCP Notes

- Always set track names with `set_track_name` after `insert_track` — the name parameter on insert is unreliable
- Verify audio landed on the correct track after `insert_audio_file` — check with `get_track_items`
- Re-query `get_project_summary` after structural changes (track deletion shifts indices)
- iZotope plugins need modules added through their GUI before MCP params take effect
- Verify param values after setting — some plugins have internal linking that overrides MCP values

## Reference Materials

- [session-templates.md](session-templates.md) — genre-specific track layouts, routing conventions, color schemes
- [reaper-setup.md](reaper-setup.md) — Reaper folder tracks, 64-channel routing, built-in plugin reference, SWS/ReaPack
- [reaper-recipes.md](reaper-recipes.md) — compound session setup operations (requires Reaper MCP server)

## Final Checklist (restated for attention)

1. Fix it before you mix it — comps, tuning, trimming, fades, noise cleanup done (or deferred items logged)
2. Mix brief read — diagnostic findings translated into routing decisions (overrides documented)
3. Every track colored and named descriptively — no "Audio 1" tracks remain
4. Mixed sample rates resolved — project set to highest rate, sinc resample mode
5. All sends start at -inf — bring up to taste during mixing
6. Sidechain routing prewired for ALL known conflicts — **verify each:** solo source, confirm GR meter moves on destination
7. FX returns verified — test signal confirms each return receives and outputs signal
8. Section markers placed with pre-roll
9. Gain staging done via clip gain, faders at unity — **verify:** loudest section peaks group buses at -10 to -6 dBFS
10. Non-mixing elements (reference, click, talkback) routed to hardware output, bypassing mix bus
11. Delivery format routing confirmed — stem buses solo-render cleanly if multi-format delivery required
12. Session saved as versioned snapshot before any processing begins
