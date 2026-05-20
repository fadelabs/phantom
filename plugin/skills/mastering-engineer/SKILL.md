---
name: mastering-engineer
description: >
  Professional mastering methodology for audio engineering. Covers the
  complete mastering chain (HPF through dither), corrective vs
  enhancement mastering, when to send a mix back, loudness targeting
  per platform, iZotope Ozone 11 workflow, and reference-based
  mastering. Use this skill whenever the user wants to master a mix,
  prepare audio for distribution, target a specific loudness standard,
  compare against a reference track, decide whether a mix needs more
  work or is ready for mastering, deliver for streaming (Spotify,
  Apple Music, YouTube), CD, or vinyl, or make any mastering decision.
  Also use when the user asks about LUFS, true peak, limiting,
  dithering, loudness normalization, or format-specific delivery
  requirements -- even if they don't say "mastering" explicitly.
---

# Mastering Engineer

> **Workflow position:** diagnostician → session-architect → mix-engineer → effects-engineer → **mastering-engineer**

Mastering is the last creative decision and the first technical one. The less you have to do, the better the mix was. Every move affects everything — you're working with a stereo file where instruments are already summed together.

**Non-negotiable rules (repeated at end as final checklist):**
1. Corrective before enhancement — never polish problems
2. Level-match before every A/B comparison — louder always sounds "better," remove that bias
3. True peak ceiling at -1.0 dBTP — never 0 (inter-sample peaks exceed sample-level meters)
4. Dither is always last — nothing after dither
5. If you need > 3 dB of any corrective move, the problem is upstream of you
6. If cumulative corrective EQ exceeds 6 dB total, the mix has systemic problems — send it back. Only corrective moves (stages 2-3) count toward this threshold; enhancement EQ (stage 6) and album-level tonal adaptation are separate categories

## Phase 1: Evaluation

### 1. Listen Holistically

Listen to the mix without touching anything. Don't listen to individual instruments — listen to the overall impression: bright or dark? Dense or open? Punchy or smooth? Where's the focal point? This holistic listening is the defining mastering skill — hearing the whole rather than the parts.

For albums/EPs: listen to 15-30 seconds of every track first. Identify which songs are louder, which have better balance, which feel like outliers.

### 2. Run Diagnostics

Run `detect_problems` and `analyze_loudness` on the mix. Also run `analyze_dynamics` to check crest factor and LRA — these tell you how much dynamic work is needed and whether parallel compression is appropriate (LRA < 4 LU = already over-compressed, skip parallel). Measurement drives the send-back decision.

### 3. Send Back or Work With It

| Condition | Decision | Why |
|-----------|----------|-----|
| > 3 dB corrective EQ needed at any single point | Send back | Mix-level frequency imbalance — mastering EQ affects everything, not just the problem |
| Cumulative corrective EQ > 6 dB total (corrective stages only) | Send back | Sum only corrective moves (stages 2-3) — enhancement shaping (stage 6) and album tonal adaptation don't count. E.g. 2.5 dB cut + 2 dB boost + 1.5 dB shelf = 6 dB signals systemic problems even when each move seems reasonable |
| Vocal buried or overwhelmingly loud | Send back | Balance problem requiring track-level fader moves |
| Phase correlation < +0.3 on mix bus | Send back | Severe phase cancellation — lead elements will disappear in mono |
| Baked-in clipping/distortion on mix bus | Send back | Irreversible — can't un-clip a summed stereo file |
| Noise floor issues (hiss, hum, buzz) | Send back if severe | Individual track noise is cheaper to fix at the stem level |
| Lossy source detected (MP3/AAC artifacts, spectral shelf above 16 kHz) | Send back | You cannot add back frequency content that a lossy codec discarded — run `analyze_spectrum` and look for a hard spectral cutoff at 16-18 kHz. Mastering a lossy source guarantees inferior results |
| Single element peaks far above everything | Send back | Limiter can't work properly — it squashes everything to catch one peak |
| Gentle tonal imbalance (< 2-3 dB EQ) | Work with it | Normal corrective mastering territory |
| Needs dynamic reshaping/glue | Work with it | Standard broadband compression |
| Needs stereo optimization | Work with it | Mono bass, subtle widening |
| Format-specific optimization needed | Work with it | Loudness targeting, dither — this is your job |

**Communicate feedback specifically:** Name the problem, the frequency or element, the section (verse/chorus), the magnitude, and the expected outcome of the fix. Example: "The vocal needs approximately 2 dB up in the choruses relative to the verses — this should bring it forward without needing mastering EQ at 2-4 kHz. There's a low-mid buildup centered around 300 Hz clouding the vocal — a 2-3 dB cut on the guitar bus at 300 Hz would clear space without thinning the kick and bass the way stereo mastering EQ would. The snare has a 4 kHz ring that a narrow cut on the snare channel would fix cleanly; on the stereo bus it would dull vocal presence. Expected result: a cleaner mix that needs < 3 dB total corrective mastering EQ."

## Phase 2: The Mastering Chain

Ten stages in strict order. Each feeds the next — skipping or reordering changes the result.

**Cumulative phase shift:** Every EQ, compressor, and stereo processor adds phase rotation. After completing the chain, run `analyze_stereo` and compare phase correlation to the unprocessed file. If correlation dropped > 0.15, bypass stages one at a time to find the culprit — typically a linear-phase EQ with steep slope or aggressive M/S processing. Prefer minimum-phase processing when cumulative shift is a concern.

**Section-aware processing (mastering automation):** If the track has dramatically different sections (quiet acoustic intro → loud full-band chorus), automate your chain. Bypass or reduce compression/limiting during quiet sections where the compressor would over-react. Automate EQ if the tonal balance shifts dramatically between sections. The goal: each section sounds mastered for what it is, not forced through settings optimized for a different part of the song.

### 1. High-Pass Filter (Sub-Bass Cleanup)

Remove energy below 20-30 Hz. Inaudible content that wastes headroom and makes the limiter react to energy nobody can hear. Gentle slope (6-12 dB/octave) to avoid phase shift in audible bass.

**Genre check:** Hip-hop, EDM, and dub use deliberate sub-bass at 30-50 Hz. Don't filter it out.

### 2. Corrective / Subtractive EQ

Run `analyze_spectrum`. Fix problems with surgical precision. **EQ type resolution:** Use **minimum-phase EQ** as the default — it has zero pre-ringing, natural transient response, and works on all material. Switch to **linear-phase EQ** only for surgical sub-300 Hz cuts where phase shift would degrade stereo imaging, and only after confirming the source is not transient-heavy (percussive/acoustic). Linear-phase pre-ringing smears transients — on a drum-forward mix, a linear-phase low cut can add an audible "thwip" before each kick. When in doubt, use minimum-phase. **Q range:** Corrective cuts Q 4-8 (surgical). Enhancement boosts Q 0.5-1.5 (broad musical). Anything above Q 10 on a stereo master is almost certainly too narrow — you're trying to fix a mix-level problem with a mastering tool.

- **Resonances/mud:** Narrow Q cut (Q 4-8) at problem frequency → expect 2-3 dB cut to clean the area without audible thinning elsewhere. If you need > 3 dB, it's a mix problem.
- **Broad tonal imbalance:** Shelf or tilt EQ → expect overall tonal shift without the comb-filter artifacts that multiple narrow cuts create.
- **The 500 Hz-1 kHz danger zone:** Vocal body lives here. Cut cautiously — a 2 dB cut at 800 Hz will noticeably thin vocals.
- **The 2.5-4 kHz danger zone:** Presence and intelligibility. A 1.5 dB boost at 3 kHz is the line between clarity and harshness on most material.

### 3. De-Noising (If Needed)

Mastering rooms are quieter than mix rooms — problems masked by studio noise become audible.

**Order of noise operations:** Tonal artifacts first (notch filters for hum/buzz) → declicking → decrackling → broadband denoising. This sequence prevents later stages from misinterpreting earlier artifacts.

**The risk:** Every noise removal process can introduce artifacts. Reverb tails that decay into noise may get stripped. Some noise is part of the recording's character. Use the lightest touch possible — moderate combined approaches beat aggressive single-tool processing.

### 4. Broadband Compression

Glue, not squash. Pulling dynamics together so the mix feels cohesive and punchy. **Critical interaction with the limiter:** Your compressor's attack time determines what the limiter sees. A fast attack (< 10 ms) pre-squashes transients before they reach the limiter — the limiter has nothing sharp to grab, resulting in a flat, lifeless master. A slow attack (15-30 ms) passes transients through to the limiter, letting it handle peak control while the compressor shapes sustain and body. The ideal pairing: compressor with slow attack (passes transients) feeding a limiter with faster attack (catches those transients cleanly).

| Parameter | Range | Notes |
|-----------|-------|-------|
| Ratio | 1.5:1-3:1 | Mastering compression is gentle |
| Attack | 10-30 ms | Slow enough to pass transients |
| Release | Auto or 100-300 ms | Auto adapts to program material |
| Gain reduction | 1-3 dB max | More than 3 dB = the mix needs more compression in mixing |

**Type selection:** VCA for transparency. Opto for smooth program-dependent response. Vari-Mu for warmth and harmonic richness alongside control.

**Parallel compression — when to use and when to skip:** Blend a heavily compressed copy at low level to add density to quiet passages without clamping peaks. **Skip parallel compression when the mix is already heavily compressed** (crest factor < 6 dB, LRA < 4 LU) — there are no quiet passages to lift, and you'll just add distortion artifacts. On over-compressed material, consider upward expansion instead: gently restore dynamics by expanding the quieter passages downward, recovering some of the range that was squashed in mixing.

### 5. Dynamic EQ / Multiband Compression

For frequency-specific problems broadband compression can't solve — a bass note that booms on certain chords, harshness at 3 kHz only in the chorus, embedded sibilance.

**Dynamic EQ vs multiband:** Dynamic EQ is preferable for intermittent problems — only engages when the threshold is exceeded, leaves the signal untouched otherwise. Multiband applies gain reduction to the entire band whenever triggered, which can shift tonal balance even when the "problem" isn't occurring.

**Crossover placement matters:** Low crossover ~80-120 Hz (sub from midrange), mid ~2-3 kHz (lower mid from presence), high ~8-10 kHz (presence from air). Place crossovers between instruments' frequency ranges, not through them.

### 6. Tonal / Additive EQ (Enhancement)

Shape the final character. Wide Q, gentle boosts — this is creative, not corrective. These moves do NOT count toward the 6 dB corrective threshold.

| Enhancement | Frequency | Amount | Caution |
|-------------|-----------|--------|---------|
| Air/sparkle | Shelf above 10-12 kHz | 1-2 dB | What sounds open on monitors becomes harsh on earbuds |
| Weight/fullness | 60-100 Hz | 1-2 dB | What sounds like thump on monitors becomes mud on small speakers |
| Presence/energy | 2-4 kHz | 0.5-1.5 dB | Very easy to overdo — harsh mastering almost always originates here |
| Warmth/body | 100-250 Hz | 1-2 dB | The mud danger zone if overdone |

**Level-match before and after.** Small EQ boosts sound "better" because they're louder. Remove the bias.

### 7. Stereo Imaging

**Mono the bass.** Collapse everything below 80-150 Hz to mono. Low-frequency stereo content causes problems on every system (vinyl skips, club subs cancel, headphones lose focus, mono playback loses energy). Exact frequency depends on genre and format — digital: 100-150 Hz for most genres, 60-80 Hz for electronic with deliberately wide bass. Vinyl: always 100 Hz or higher (groove geometry demands it).

**Verify mono-bass with measurement:** After applying mono-bass, run `analyze_stereo` — expect correlation near +1.0 below your crossover frequency. If you still see spread below target, the processing isn't fully engaged or the crossover slope is too gentle.

**Mid-Side processing** — verify every M/S change with `analyze_stereo` before and after. M/S introduces subtle level and phase shifts that accumulate across stages. Action: boost Mid 1-2 dB at 2-4 kHz → expect vocal presence increase without side guitar/reverb change. Action: compress Sides 2-3 dB GR → expect tighter image, correlation increase of 0.05-0.1, no center vocal change.

**Widening:** After any widening, check `analyze_stereo` — correlation must stay above +0.3. Below that, mono compatibility is compromised.

### 8. Saturation / Exciter (Optional)

Light touch before the limiter. Saturation adds harmonics that make the signal perceptually louder without increasing peak level — essentially free loudness.

- **Tape:** Even harmonics (warm, musical), gently rounds transient peaks
- **Tube:** Mix of even and odd harmonics (richer, more complex)
- **Harmonic exciter:** Generates harmonics for perceived brightness without EQ boost — useful when a mix sounds dull but doesn't respond to HF EQ

### 9. Limiting / Maximizer

**Ceiling:** -1.0 dBTP for digital delivery. Vinyl masters use -3.0 dBTP — the cutting lathe needs extra headroom for the electromechanical translation process.

**Total-chain GR budget:** Think of gain reduction as a shared budget across compressor + multiband + limiter. Target 6-8 dB total GR across all stages combined. If your compressor does 2 dB, multiband does 1-2 dB, the limiter should do 2-4 dB. If the limiter is doing 6+ dB, either redistribute GR upstream (more compression, less limiting) or the mix is too dynamic for your target loudness. Track the budget: run `analyze_dynamics` after each dynamics stage to see cumulative effect.

**Loudness:** As you lower the threshold, peaks are caught and held, raising average level relative to peaks. Target 2-4 dB of gain reduction on the limiter specifically. Above 6 dB of limiter GR, you're almost certainly crushing it.

**Attack and release per material:** Fast attack (0.1-1 ms) for dense, sustained material (electronic, heavily compressed rock). Slower attack (1-5 ms) for transient-rich material (acoustic, jazz, orchestral) — lets the initial transient punch through. Release: auto-release works for most material; manual short release (20-50 ms) for fast-tempo electronic, manual long release (100-200 ms) for ballads and classical.

**When limiting goes too far:** Flat-lined waveforms have no punch, no transient detail, no life. Streaming platforms normalize everything to the same perceived level — hypercompression offers no competitive advantage and actively degrades quality.

**Limiter artifacts on specific transients:** If you hear distortion or pumping on specific hits (snare crack, vocal consonant, pick attack) but the rest sounds fine, the limiter's attack is too fast for that transient. Try: (1) increase limiter attack slightly to let the transient pass, (2) use multiband limiter to isolate the problem band, (3) use dynamic EQ before the limiter to tame the specific frequency peak triggering excessive GR. If one element consistently triggers limiter distortion, that's a send-back candidate — the element is too loud in the mix.

Run `analyze_loudness` after limiting — expect integrated LUFS within 1 LU of your target, true peak at or below ceiling. If true peak exceeds ceiling, reduce limiter input gain by the overshoot amount and re-check.

For platform-specific targets and genre loudness ranges: load [format-targets.md](format-targets.md).

### 10. Dither (When Reducing Bit Depth)

Only when reducing bit depth (24→16 for CD). Always the absolute last process. TPDF for transparency, noise-shaped dither pushes noise into frequencies where hearing is least sensitive (above 15 kHz).

**32-bit float → 24-bit:** Dither at the 24-bit noise floor (~-144 dBFS) is inaudible under any listening condition — below the thermal noise floor of any real-world DA converter. In practice, skip dither for 32→24 conversion. It adds nothing perceptible. Dither matters for 24→16 (CD) because the 16-bit noise floor (~-96 dBFS) is within audible range on quiet passages.

Never dither twice. Never dither at same bit depth. Never dither when going up in bit depth. **Sample rate conversion** is separate from dithering — if delivering at a different sample rate (e.g., 96→44.1 kHz), perform SRC before dithering, and verify with `analyze_spectrum` to confirm no aliasing. Use high-quality SRC (SoX, iZotope, r8brain) rather than a DAW's default resampler.

## A/B Reference Methodology

Use `compare_to_reference` for per-dimension deviations. Use `match_to_reference` (if Matchering installed) at 50-70% strength as a starting point.

**How to A/B effectively:**
1. Choose references in the same genre and era
2. **Level-match** — match integrated LUFS before comparing. Non-negotiable.
3. Compare quickly — short 2-4 second switches reveal differences better than extended listening
4. Compare specific dimensions: low-end weight, vocal presence, stereo width, transient clarity, brightness
5. Use 2-3 references — no single reference is perfect in every dimension

**When the reference is a loudness-war casualty:** If the client's reference is mastered at -5 to -7 LUFS with visible flat-lining, educate: "That reference measures -6 LUFS with 4 LU loudness range — it was mastered for a pre-normalization era. On Spotify at -14, it gets turned down 8 dB and sounds worse than a -10 LUFS master with intact dynamics. I'll match the tonal character and punch, but target a loudness that actually sounds better on modern platforms." Show them a before/after with `analyze_dynamics` — crest factor and LRA numbers make the argument concrete.

**Match direction, not destination.** If the reference has more sparkle, add sparkle — but don't make your track sound identical.

**Structured before/after comparison:** At session end, run `compare_to_reference` on both the original mix and the master against the same reference. Present a dimension-by-dimension comparison table: original mix deviation vs mastered deviation for each dimension (spectral balance, dynamics, stereo width, loudness). This shows the client exactly what mastering accomplished — and what it intentionally left alone.

## Album / EP Workflow

When mastering a collection (not just a single):

1. **Listen to everything first** — 15-30 seconds per track, identify the center of the collection's sound
2. **Process the "average" tracks first** — get the core group cohesive, then bring outliers into line. Tonal adjustments to create album coherence (matching brightness, low-end weight across tracks) are **adaptation, not corrective EQ** — they don't count toward the 6 dB corrective threshold because you're shaping for context, not fixing problems
3. **Match perceived levels** (not mathematical) — a loud electronic track and a quiet ballad shouldn't read the same LUFS, but should feel like they belong at the same listening volume
4. **Sequence and spacing** — 2-4 seconds between tracks (adjusted per transition). Zero gap for some; 4-5 seconds to reset the listener's ears after intense tracks
5. **Check fades and heads/tails** — verify no reverb tails cut short, no count-offs included, no silence too long/short

## Stem Mastering

When working with grouped stereo submixes instead of a single stereo file:

**When it makes sense:** Mix has a specific problem solvable only with separated stems (vocal too quiet, bass too boomy). Or the project is for film/sync where dialogue-stage remixing is needed. Or the mastering engineer wants different processing per element group.

**When it doesn't:** Mix is well-balanced and the stereo file is the mixer's intended product. Adding complexity without clear benefit.

**Verification step (mandatory):** All stems summed with no processing must exactly match the provided stereo mix bounce. If they don't, bus compression or master effects aren't captured in the stems — proceeding means you're working with material that doesn't represent what the mixer approved.

## Quality Control (Final Pass)

Before delivery — each step is pass/fail with explicit thresholds. If any fails, fix and re-run from that step forward:

1. **Headphone QC pass** — headphones reveal clicks, dropouts, and stereo anomalies that monitors mask. Pass: no artifacts heard. Fail: any click, dropout, or stereo anomaly → identify source stage, bypass to confirm, fix.
2. Run `analyze_loudness` — Pass: integrated LUFS within 1 LU of platform target AND true peak at or below ceiling (-1.0 dBTP digital, -3.0 dBTP vinyl). Fail: adjust limiter threshold/ceiling.
3. Run `analyze_dynamics` — Pass: crest factor and LRA within genre norms (see format-targets.md). Fail: over-limited (reduce limiter GR) or under-processed (add compression).
4. Run `analyze_stereo` — Pass: correlation above +0.3, bass mono below target frequency, AND correlation dropped < 0.15 from unprocessed file. Fail on correlation drop: bypass stages one at a time to find the phase-shift culprit.
5. Run `detect_problems` — Pass: no clipping, no ISPs above ceiling, no introduced artifacts. Fail: identify and fix the offending stage.
6. Run `compare_to_profile` — Pass: deviations from genre norms are intentional and documented. Fail: unintentional deviation → adjust.
7. **Mono check** — Pass: no element drops > 3 dB in mono. Fail: identify the out-of-phase element, fix in stereo imaging stage.
8. **Multiple playback check** — if possible, check on at least two systems
9. **Format verification** — confirm delivered file matches required format: correct sample rate, bit depth, file type. If SRC was performed, verify no aliasing. If dither was applied, confirm applied once at the final bit depth reduction.

## Reference Materials

- [format-targets.md](format-targets.md) — platform loudness targets, CD/vinyl specs, delivery metadata, genre loudness ranges
- [ozone-guide.md](ozone-guide.md) — iZotope Ozone 11 module-by-module guidance, Neutron stem mastering
- [reaper-recipes.md](reaper-recipes.md) — compound Reaper mastering operations (requires Reaper MCP server)

## Final Checklist (restated for attention)

1. Corrective before enhancement — always fix problems before polishing
2. Level-match every A/B comparison — remove the loudness bias
3. Ceiling at -1.0 dBTP digital, -3.0 dBTP vinyl
4. Dither last — nothing after dither, only when reducing bit depth
5. If > 3 dB corrective needed — send it back, the problem is in the mix
6. Total-chain GR budget — 6-8 dB across comp + multiband + limiter combined
7. Mono the bass — 100-150 Hz digital, 100+ Hz vinyl
8. QC on headphones — catches what monitors mask
