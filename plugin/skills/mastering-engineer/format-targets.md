# Platform-Specific Delivery Requirements

## Table of Contents
- Streaming Platform Targets
- Genre-Specific Loudness Ranges
- CD (Red Book)
- Vinyl
- Delivery Metadata
- MCP Verification Checklist

---

## Streaming Platform Targets

Run `analyze_loudness` after mastering to verify compliance.

| Platform | Target LUFS | True Peak Ceiling | Bit Depth | Sample Rate | Notes |
|----------|------------|-------------------|-----------|-------------|-------|
| **Spotify** | -14 LUFS | -1 dBTP | 24-bit | 44.1 kHz | Normalizes to -14. Louder masters get turned DOWN — no advantage to mastering louder. |
| **Apple Music** | -16 LUFS | -1 dBTP | 24-bit | 44.1 kHz+ | Apple Digital Masters program. Submit highest sample rate available. |
| **YouTube** | -14 LUFS | -1 dBTP | 24-bit | 48 kHz preferred | YouTube audio is 48 kHz. 44.1 works but gets resampled. |
| **Tidal** | -14 LUFS | -1 dBTP | 24-bit | 44.1 kHz+ | MQA support for high-res. Submit highest quality. |
| **Amazon Music** | -14 LUFS | -1 dBTP | 24-bit | 44.1 kHz+ | Same targets as Spotify/YouTube. |
| **Broadcast TV (US)** | -24 LUFS | -2 dBTP | 24-bit | 48 kHz | ATSC A/85 standard. |
| **Podcast (Apple)** | -16 LUFS | -1 dBTP | — | — | Matches Apple Music level. |
| **General streaming** | -14 LUFS | -1 dBTP | 24-bit | 44.1 kHz | Safe default for all platforms. |

**Normalization reality:** Every major platform normalizes loudness. A -6 LUFS master gets turned down to -14 on Spotify — and sounds worse than one optimized for -14, because limiting artifacts are baked in but the loudness advantage is removed.

**Exception:** Club/DJ play has no normalization. EDM for club use may target -6 to -8 LUFS. Consider delivering two masters: streaming (-14) and club (-6 to -8).

---

## Genre-Specific Loudness Ranges

Don't master to each platform individually — they normalize regardless. Master to a level that sounds great for the genre.

| Genre | Working LUFS Range | Dynamic Range Priority | Notes |
|-------|-------------------|----------------------|-------|
| Acoustic / Jazz / Classical | -12 to -16 LUFS | Maximum — dynamic range IS the music | Minimal processing. A classical piece squashed to -9 has lost its musical meaning. |
| Country / Singer-Songwriter | -10 to -14 LUFS | High — vocal authenticity valued | More dynamic than pop despite modern production trends. |
| Rock / Alternative | -9 to -12 LUFS | Moderate — punch matters more than loudness | Drum transient preservation is critical. Over-limiting kills impact. |
| Pop / R&B | -8 to -10 LUFS | Moderate — competitive loudness expected | Vocal clarity through limiting is the key challenge. |
| Hip-Hop | -7 to -10 LUFS | Moderate — sub-bass headroom matters | Low-end weight needs harmonic content for small-speaker translation. |
| Electronic / EDM | -6 to -9 LUFS | Low — source is already compressed | Kick transient vs loudness is the central tension. Limiter attack is critical. |
| Metal | -7 to -10 LUFS | Moderate — loud sections need quiet contrast | Dense, layered genres still need micro-dynamics for punch. |

These are descriptive ranges based on what successful releases measure at — not prescriptive targets. The right loudness serves the music.

---

## CD (Red Book)

| Property | Requirement |
|----------|-------------|
| Bit depth | 16-bit |
| Sample rate | 44.1 kHz |
| Loudness | -9 to -6 LUFS (genre-dependent) |
| Dither | **Mandatory** when going from 24→16 bit |

**Dither is not optional.** Reducing from 24-bit to 16-bit without dither introduces quantization distortion — subtle but audible graininess, especially on reverb tails and quiet passages. TPDF is transparent. Noise-shaped dither (MBIT+) pushes dither noise above 15 kHz where hearing is least sensitive.

Dither is always the absolute last stage. Nothing goes after dither.

---

## Vinyl

Vinyl is the most constrained format. Master separately — do not reuse the digital master.

| Constraint | Requirement | Why |
|-----------|-------------|-----|
| **Mono bass** | Below 80-100 Hz | Out-of-phase bass causes the needle to jump out of the groove |
| **De-essing** | More aggressive than digital | Sibilance causes distortion (stylus can't track rapid HF movements) |
| **HF rolloff** | LPF at 16-18 kHz | Extreme highs cause tracking problems and add noise |
| **Short-term LUFS** | Max -9 LUFS | Louder = narrower grooves = more distortion |
| **Track sequencing** | Complex/bass-heavy tracks at outer grooves | Outer grooves have more velocity and wider spacing — handle dense content better |
| **Side length** | 22 minutes max per side | Longer sides = narrower grooves = less dynamic range |

**Vinyl mastering checklist:**
1. Mono everything below 100 Hz (verify with `analyze_stereo`)
2. Aggressive de-essing (more than digital master)
3. LPF at 16-18 kHz
4. Check short-term LUFS stays below -9 (verify with `analyze_loudness`)
5. Sequence: heaviest content on outside of each side
6. Deliver as 24-bit WAV to cutting engineer (they handle final format)

---

## Delivery Metadata

| Item | Format | Notes |
|------|--------|-------|
| **ISRC codes** | CC-XXX-YY-NNNNN | Unique per track. Country (2) + Registrant (3) + Year (2) + Designation (5). |
| **UPC/EAN** | 12 or 13 digits | Barcode for the release (album/EP level, not per-track). |
| **Track metadata** | Embedded in WAV/FLAC | Artist, title, album, track number, ISRC. |
| **Stem deliverables** | Separate WAV files | If stem mastering was requested, deliver individual stem masters alongside the stereo master. |

---

## MCP Verification Checklist

After mastering, verify with Phantom tools:

1. `analyze_loudness` — integrated LUFS matches platform target, true peak below -1 dBTP
2. `analyze_dynamics` — crest factor and LRA appropriate for genre
3. `analyze_stereo` — correlation above +0.3, bass mono below target frequency
4. `analyze_spectrum` — spectral balance appropriate for genre (compare with `compare_to_profile`)
5. `detect_problems` — no clipping, no ISPs above ceiling, no introduced artifacts
6. `compare_to_profile` — deviations from genre norms are intentional, not accidental
7. `compare_to_reference` — if reference available, per-dimension check confirms direction
