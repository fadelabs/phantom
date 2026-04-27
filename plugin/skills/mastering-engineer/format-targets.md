# Platform-Specific Delivery Requirements

Loudness targets, format requirements, and delivery specs. Run `analyze_loudness` after mastering to verify compliance. These are targets, not rigid rules -- some genres push louder.

## Streaming Platforms

| Platform | Target LUFS | True Peak Ceiling | Bit Depth | Sample Rate | Notes |
|----------|------------|-------------------|-----------|-------------|-------|
| **Spotify** | -14 LUFS | -1 dBTP | 24-bit | 44.1 kHz | Normalizes to -14 LUFS. Louder masters get turned DOWN -- there's no advantage to mastering louder than -14. |
| **Apple Music** | -16 LUFS | -1 dBTP | 24-bit | 44.1 kHz+ | Apple Digital Masters program. Submit at the highest sample rate you have. |
| **YouTube** | -14 LUFS | -1 dBTP | 24-bit | 48 kHz preferred | YouTube's audio is 48 kHz. 44.1 kHz works but gets resampled. |
| **Tidal** | -14 LUFS | -1 dBTP | 24-bit | 44.1 kHz+ | MQA support for high-res. Submit highest quality available. |
| **Amazon Music** | -14 LUFS | -1 dBTP | 24-bit | 44.1 kHz+ | Same targets as Spotify/YouTube. |
| **General streaming** | -14 LUFS | -1 dBTP | 24-bit | 44.1 kHz | Safe default for all platforms. |

**Normalization reality:** Every major streaming platform normalizes loudness. A master at -6 LUFS gets turned down to -14 LUFS on Spotify -- and it sounds worse than a master that was optimized for -14 LUFS, because the limiting artifacts are baked in but the loudness advantage is removed. Master to the platform target, not louder.

**Exception:** Club/DJ play has no normalization. EDM masters for club use may target -6 to -8 LUFS. Consider delivering two masters: one for streaming (-14 LUFS) and one for club play (-6 to -8 LUFS).

## CD (Red Book)

| Property | Requirement |
|----------|-------------|
| Bit depth | 16-bit |
| Sample rate | 44.1 kHz |
| Loudness | -9 to -6 LUFS (genre-dependent) |
| Dither | **Mandatory** when going from 24-bit to 16-bit |

**Dither is not optional.** Reducing from 24-bit to 16-bit without dither introduces quantization distortion -- a subtle but audible graininess, especially on reverb tails and quiet passages. TPDF dither is transparent. MBIT+ noise shaping pushes dither noise into frequencies where hearing is least sensitive (above 15 kHz).

Dither is always the absolute last stage. Nothing goes after dither.

## Vinyl

Vinyl is the most constrained format. Master separately for vinyl -- do not use the digital master.

| Constraint | Requirement | Why |
|-----------|-------------|-----|
| **Mono bass** | Below 80-100 Hz | Out-of-phase bass causes the needle to physically jump out of the groove |
| **De-essing** | Aggressive, more than digital | Sibilance causes distortion on vinyl (the stylus can't track rapid HF movements) |
| **HF rolloff** | 16-18 kHz | Extreme highs cause tracking problems and add noise |
| **Short-term LUFS** | Max -9 LUFS | Louder = narrower grooves = more distortion |
| **Track sequencing** | Complex/bass-heavy tracks at outer grooves | Outer grooves have more linear velocity and wider groove spacing -- they handle dense content better |
| **Side length** | 22 minutes maximum per side | Longer sides = narrower grooves = less dynamic range and more distortion |

**Vinyl mastering checklist:**
1. Mono everything below 100 Hz (verify with `analyze_stereo`)
2. Aggressive de-essing (more than you'd use for digital)
3. LPF at 16-18 kHz
4. Check short-term LUFS stays below -9 (verify with `analyze_loudness`)
5. Sequence tracks: heaviest content on the outside of each side
6. Deliver as 24-bit WAV to the cutting engineer (they handle the final format)

## Delivery Metadata

| Item | Format | Notes |
|------|--------|-------|
| **ISRC codes** | CC-XXX-YY-NNNNN | Unique per track. Country (2) + Registrant (3) + Year (2) + Designation (5). |
| **UPC/EAN** | 12 or 13 digits | Barcode for the release (album/EP level, not per-track). |
| **Track metadata** | Embedded in WAV/FLAC | Artist, title, album, track number, ISRC. |
| **Stem deliverables** | Separate WAV files | If stem mastering was requested, deliver individual stem masters alongside the stereo master. |

## MCP Verification Checklist

After mastering, verify with Phantom tools:

1. `analyze_loudness` -- integrated LUFS matches platform target, true peak below -1 dBTP
2. `analyze_dynamics` -- crest factor and LRA appropriate for genre
3. `analyze_stereo` -- correlation above +0.3, bass mono below target frequency
4. `analyze_spectrum` -- spectral balance appropriate for genre (compare with `compare_to_profile`)
5. `detect_problems` -- no clipping, no ISPs above ceiling, no introduced artifacts
6. `compare_to_profile` -- deviations from genre norms are intentional, not accidental
7. `compare_to_reference` -- if reference track available, per-dimension check confirms direction
