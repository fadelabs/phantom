# Measurement-to-Action Translation Tables

Complete lookup tables for interpreting Phantom MCP tool results and translating measurements into specific processing recommendations. Reference this when you need precise thresholds and actions for a specific measurement type.

## Dynamics to Compression

| Measurement | Condition | Interpretation | Recommended Action |
|-------------|-----------|----------------|-------------------|
| RMS level | > -12 dBFS | Hot signal, limited headroom | Reduce gain before processing, check for clipping |
| RMS level | -20 to -14 dBFS | Good level for mixing | Standard processing, no gain adjustment needed |
| RMS level | < -24 dBFS | Low level, possible noise issues | Boost gain, but check noise floor first |
| Crest factor | > 18 dB | Very dynamic, likely unprocessed | Gentle compression (2:1-3:1), preserve transients with slow attack |
| Crest factor | 12-18 dB | Normal dynamic range | Standard compression appropriate |
| Crest factor | 8-12 dB | Moderately compressed, well-recorded | Light compression only if needed, focus on tonal shaping |
| Crest factor | 6-8 dB | Already compressed | Minimal additional compression, consider parallel only |
| Crest factor | < 6 dB | Over-compressed, sausage waveform | Do not compress further. Use saturation or transient shaping if punch is needed |

Crest factor is source-dependent. Drums and transient-heavy material naturally sit at 15-20 dB without processing. A legato string section or pad may naturally sit at 6-8 dB even without compression. Interpret in context of the instrument type.

| Dynamic range | > 20 LU | Very wide dynamics | May need both compression and volume automation |
|-------------|-----------|----------------|-------------------|
| Dynamic range | 8-14 LU | Typical for mixed music | Normal processing |
| Dynamic range | < 6 LU | Heavily limited | Limited options for dynamics processing |
| Dynamic complexity | > 0.3 | High dynamic variation over time | Consider multiband compression for frequency-specific control |
| Dynamic complexity | 0.1-0.3 | Moderate variation | Standard dynamics processing |
| Dynamic complexity | < 0.1 | Consistent dynamics | Compression may not be needed |

## Frequency Spectrum to EQ

| Frequency Range | Excess Energy Means | Deficit Means | Action |
|----------------|--------------------|--------------| ------|
| Sub-bass (< 40 Hz) | Rumble, subsonic content | Clean recording | HPF at 30-40 Hz on most sources, higher on non-bass instruments |
| Low bass (40-80 Hz) | Boomy, tubby, excessive bottom | Thin, no weight | Cut problematic stems here, keep only kick and bass fundamental |
| Upper bass (80-200 Hz) | Muddy, thick | Thin, no body | Check for proximity effect on vocals (steep rise below 200 Hz) |
| Low mids (200-500 Hz) | Mud, boominess, boxiness | Hollow, scooped | "3 dB buildup at 250-400 Hz across stems = cut 2-3 dB with moderate Q on offending stems" |
| Mids (500 Hz-1 kHz) | Boxy, nasal, honky | Scooped, distant | Narrow cut at problem frequency if resonance, gentle boost if lacking body |
| Upper mids (1-2 kHz) | Nasal, telephone-like | Recessed, lacks clarity | Be surgical -- this range is where clarity and nasality compete |
| Presence (2-4 kHz) | Harsh, aggressive, fatiguing | Dull, buried | Most common problem range. Cut for harshness, boost for vocal clarity |
| Brilliance (4-8 kHz) | Sibilant, edgy, sharp | Dark, muffled | De-esser territory on vocals. Careful boosting -- ear fatigue zone |
| Air (8-16 kHz) | Hissy, brittle | Dull, lifeless | Gentle shelf boost for air, but check noise floor first |
| Ultra-high (> 16 kHz) | Noise, artifacts | Normal (most content rolls off here) | LPF at 16-18 kHz on most sources, especially for vinyl delivery |

### Common multi-stem EQ conflicts
| Pair | Conflict Zone | Solution |
|------|--------------|---------|
| Kick vs bass | 60-100 Hz | Complementary EQ: boost one where you cut the other |
| Bass vs guitars | 100-250 Hz | HPF guitars at 80-120 Hz, cut bass mud at 200-400 Hz |
| Guitars vs vocals | 2-4 kHz | Cut guitars at vocal presence frequency, boost guitars elsewhere |
| Keys vs guitars | 300 Hz-1 kHz | Pan separation + complementary EQ in the midrange |
| Multiple vocals | 1-5 kHz | Slight frequency offset per voice, different reverb sends |

### Spectral centroid reference ranges

Typical spectral centroid values by instrument type. Use these to sanity-check whether a stem's content matches its filename.

| Instrument | Typical Centroid Range | Notes |
|------------|----------------------|-------|
| Bass guitar / synth bass | 200-800 Hz | Higher if using a pick or distortion |
| Kick drum | 500 Hz-2 kHz | Depends on beater type and tuning |
| Floor tom / toms | 800 Hz-2 kHz | Lower for floor, higher for rack |
| Snare | 2-5 kHz | Higher with snare wires engaged |
| Overheads / cymbals | 3-8 kHz | Heavily cymbal-dependent |
| Acoustic guitar | 1-3 kHz | Fingerpicked lower, strummed higher |
| Electric guitar (clean) | 1-3 kHz | Similar to acoustic |
| Electric guitar (distorted) | 2-4 kHz | Distortion shifts centroid up |
| Vocals | 1-3 kHz | Breathy vocals higher, baritone lower |
| Piano / keys | 1-3 kHz | Depends on register |
| Synth pad | 500 Hz-4 kHz | Highly variable |
| Full mix | 2-4 kHz | Genre-dependent |

A stem with a centroid far outside its expected range may be mislabeled, heavily filtered, or unusual.

## Phase and Spatial

| Measurement | Condition | Interpretation | Action |
|-------------|-----------|----------------|--------|
| Overall correlation | > +0.8 | Excellent mono compatibility | No issues |
| Overall correlation | +0.5 to +0.8 | Good, normal stereo content | Monitor, acceptable |
| Overall correlation | +0.3 to +0.5 | Wide stereo, approaching risky | Check on mono playback systems |
| Overall correlation | < +0.3 | Mono compatibility compromised | Reduce stereo widening, check individual stems |
| Overall correlation | Sustained negative | Possible polarity inversion or excessive M/S processing | Check polarity; sustained near -1 = definite inversion; occasional dips normal with wide stereo |
| Per-band correlation (low) | < +0.5 below 200 Hz | Low-end phase issues | Make bass mono below 100-150 Hz |
| Per-band correlation (high) | < +0.3 above 8 kHz | Normal for wide stereo content | Usually acceptable, common with stereo reverbs |
| Time delay between L/R | > 1 ms | Haas effect or misalignment | Intentional = Haas widening (use with caution). Unintentional = fix alignment |
| Polarity inverted | true | One channel is flipped | Flip polarity on the inverted channel |

## Noise Assessment

| Measurement | Threshold | Rating | Action |
|-------------|-----------|--------|--------|
| SNR | > 70 dB | Professional | No treatment needed |
| SNR | 60-70 dB | Good | Acceptable, gate during silence if needed |
| SNR | 50-60 dB | Acceptable | Noise reduction recommended, gate aggressively |
| SNR | 40-50 dB | Poor | Dedicated noise reduction required before mixing |
| SNR | < 40 dB | Unacceptable | Re-record if possible, heavy NR will introduce artifacts |
| Noise floor | Below -70 dBFS | Clean | No treatment |
| Noise floor | -60 to -50 dBFS | Audible in quiet passages | Gate or noise reduction in quiet sections |
| Noise floor | Above -50 dBFS | Significant noise present | Noise reduction required before mixing |
| Hum detected | 50 Hz fundamental | Mains hum (EU/Australia/most of Asia) | Notch filter at 50, 100, 150, 200 Hz (fundamental + harmonics) |
| Hum detected | 60 Hz fundamental | Mains hum (US/Canada/most of S. America) | Notch filter at 60, 120, 180, 240 Hz (fundamental + harmonics) |

Note on mains hum: the dominant hum frequency is often the *double* of the mains frequency (100 Hz or 120 Hz) because magnetic force is proportional to the square of the current. Listen to identify which harmonic is loudest before applying notch filters -- sometimes the 2nd harmonic needs the deepest cut.

### DC Offset

| Measurement | Condition | Action |
|-------------|-----------|--------|
| DC offset detected | Mean > 5e-4 | Remove with dedicated DC offset removal tool (available in most DAWs as "Remove DC Offset" and in iZotope RX). If unavailable, use an HPF set very low (5-20 Hz). Dedicated removal (mean subtraction) is more precise -- HPF can attenuate wanted low-frequency content or introduce phase shift depending on cutoff and filter type. |

## Loudness

| Measurement | Condition | Context | Action |
|-------------|-----------|---------|--------|
| Integrated LUFS | > -8 | Any | Heavily limited, limited mastering headroom |
| Integrated LUFS | -14 to -10 | Mastered track | Normal range for mastered music |
| Integrated LUFS | -20 to -14 | Mix (pre-mastering) | Good level for a mix, leaves mastering headroom |
| Integrated LUFS | < -24 | Any | Very quiet -- check if this is intentional (ambient/classical) |
| True peak | > 0 dBTP | Any | Hard clipping -- dealbreaker. Samples are baked at the ceiling. |
| True peak | -1 to 0 dBTP | Any | Exceeds EBU R128 and streaming platform limits (-1 dBTP). Significant -- limits mastering options and may distort during lossy encoding. |
| True peak | -3 to -1 dBTP | Mix | Workable headroom, but tight for mastering |
| True peak | < -3 dBTP | Mix | Good headroom for mastering |
| Loudness range (LRA) | > 15 LU | Any | Very dynamic -- classical, ambient, some jazz |
| Loudness range (LRA) | 7-12 LU | Pop/Rock | Normal range |
| Loudness range (LRA) | < 5 LU | EDM/Hip-hop | Expected for heavily compressed genres |

## Severity Decision Matrix

Use this to assign the correct severity tier to any detected problem:

| Condition | Severity | Rationale |
|-----------|----------|-----------|
| Cannot be fixed in mixing (baked-in clipping, format mismatch) | Dealbreaker | Must be resolved at source before mixing begins |
| Exceeds distribution standards (true peak > -1 dBTP, lossy artifacts) | Significant | Limits mastering options and platform delivery |
| Degrades the entire mix if not addressed (noise, DC offset, hum) | Significant | Fix early -- these affect every processing step downstream |
| Affects specific mix decisions (sibilance, resonances, mud) | Moderate | Address as part of the mixing process |
| Audible only on close inspection or in solo | Minor | Fix if time allows, won't make or break the mix |
