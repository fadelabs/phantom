# Compressor Selection & Settings Guide

The right compressor type matters as much as the right settings -- each topology has a character. Reference this when choosing a compressor and dialing in starting values.

## Compressor Types

| Type | Harmonic Content | Character | Best For | Examples |
|------|-----------------|-----------|----------|----------|
| **FET** | Odd-order harmonics | Fast, punchy, aggressive | Drums, vocals needing control, parallel compression | 1176, Distressor |
| **Opto** | Minimal coloration | Smooth, musical, slow | Vocals, bass, gentle evening out | LA-2A, CL-1B |
| **VCA** | Transparent | Clean, precise, controlled | Buses, precision work, mix bus glue | SSL G-Bus, API 2500 |
| **Vari-Mu** | Even-order harmonics | Warm, gentle, glue | Mix bus, mastering, warmth | Fairchild, Manley Variable Mu |
| **Digital** | None | Transparent, flexible | Surgical precision, anything needing exact control | Stock DAW compressor |

## Starting Settings Per Instrument

| Instrument | Type | Ratio | Attack | Release | GR Target | Notes |
|-----------|------|-------|--------|---------|-----------|-------|
| Kick | FET or VCA | 4:1 | 10-30 ms | 50-100 ms | 3-6 dB | Fast attack softens transient (good for pillowy kick), slow attack preserves punch |
| Snare | FET | 4:1-6:1 | 5-15 ms | 50-100 ms | 3-6 dB | Slow attack (15ms+) preserves the crack. Fast attack flattens it -- only if you want smooth. |
| Drum Bus | VCA | 2:1-4:1 | 10-30 ms | Auto or 100-300 ms | 2-4 dB | Glue, not squash. The bus comp should make drums feel like one instrument. |
| Bass | Opto or FET | 3:1-4:1 | 20-40 ms | 100-200 ms | 3-6 dB | Opto for smooth leveling, FET for more punch. Bass needs even dynamics. |
| Vocals | Opto then FET | 3:1-4:1 | 10-30 ms | 50-150 ms | 3-6 dB | Serial compression: opto first (smooth out dynamics), FET second (catch remaining peaks) |
| Acoustic Guitar | Opto | 2:1-3:1 | 20-40 ms | 100-200 ms | 2-4 dB | Gentle evening. Don't kill the dynamics -- that's the instrument's expression. |
| Electric Guitar | VCA or FET | 3:1-4:1 | 10-20 ms | 50-100 ms | 2-4 dB | Already compressed by the amp. Light touch unless very dynamic clean parts. |
| Mix Bus | VCA or Vari-Mu | 1.5:1-2:1 | 10-30 ms | Auto or 300 ms | 1-3 dB | Glue not squash. If you're hitting more than 3 dB on the mix bus, you're doing too much. |

## Parallel Compression (NY Compression)

The dry signal preserves transients. The heavily compressed signal adds sustain and body. Blend the two for the best of both worlds.

**Setup:**
1. Send the source to a parallel bus (pre-fader send)
2. On the parallel bus: compress hard (10:1+, fast attack 1-5 ms, medium release 50-100 ms)
3. Blend the parallel bus at -10 to -6 dB below the dry signal
4. Adjust to taste -- you should feel the density increase without hearing obvious compression

**Best for:** Drums (adds punch and sustain), vocals (adds density and presence), bass (adds consistency)

**Caution:** The parallel bus will be noisy (heavy compression raises the noise floor). Gate or noise-reduce the source before the parallel send.

## Sidechain Compression

### Frequency-Dependent Sidechaining

Don't just duck the whole bass when the kick hits -- that kills the bass's midrange presence. Instead, HPF the sidechain input at 80-100 Hz so only the sub frequencies duck.

**Setup:**
1. Send kick to bass compressor's sidechain input (Reaper: channels 3-4)
2. On the compressor, set detector input to sidechain
3. Add an HPF at 80-100 Hz on the sidechain input (so the compressor only responds to the kick's sub energy)
4. Fast attack (1-5 ms), fast release (50-100 ms), 2:1-3:1 ratio

Run `analyze_masking` between kick and bass first. The masking analysis tells you exactly which frequency bands are fighting, so you can set the sidechain filter precisely.

### Beyond Kick/Bass

- **Vocal-to-guitar sidechain**: gentle ducking (1-2 dB, slow attack) so guitars subtly yield to vocals
- **Vocal-to-reverb sidechain**: reverb ducks during vocal phrases, blooms in gaps (ducked reverb)
- **Kick-to-synth pad sidechain**: rhythmic pumping (intentional in EDM, subtle elsewhere)

## Serial Compression

Two gentle compressors (2-3 dB gain reduction each) instead of one heavy one (6 dB). Each compressor does less work, producing fewer artifacts.

**Typical vocal serial chain:**
1. Opto (LA-2A style): slow, smooth, catches the broad dynamic envelope. 3:1, 2-3 dB GR.
2. FET (1176 style): faster, catches remaining peaks. 4:1, 2-3 dB GR.

The result: 4-6 dB total gain reduction with the musicality of two different characters working together, instead of one compressor straining to do all the work.
