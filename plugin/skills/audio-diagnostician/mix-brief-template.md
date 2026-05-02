# Mix Brief Template

Structured mix brief template. After running diagnostics, fill in this template to create the handoff document for mixing. This format ensures all downstream skills (`/phantom:mix-engineer`, `/phantom:session-architect`, `/phantom:effects-engineer`) can parse the assessment consistently.

## Session Overview

| Property | Value |
|----------|-------|
| Stem count | {N} |
| Sample rate | {rate} Hz |
| Bit depth | {depth}-bit (note if stems differ: e.g., "24-bit, except bass_di at 16-bit") |
| Duration | {duration} (note if stems differ significantly) |
| Genre / Reference | {genre or reference track} |
| BPM | {tempo if known, or "not provided -- ask user"} |
| Aggregate headroom | {estimate: e.g., "stems average -6 dBTP peak, expect hot summing -- gain staging needed"} |

## Per-Stem Summary

| Stem | LUFS | Peak (dBTP) | Crest (dB) | Phase Corr. | Width | Duration | Key Issues |
|------|------|-------------|------------|-------------|-------|----------|------------|
| {name} | {lufs} | {peak} | {crest} | {correlation} | {width} | {duration} | {issues or "clean"} |

## Problems by Severity

### Dealbreakers (fix before mixing)
- {problem}: {stem} -- {recommendation}

### Significant (address early)
- {problem}: {stem} -- {recommendation}

### Moderate (address during mixing)
- {problem}: {stem} -- {recommendation}

### Minor (optional cleanup)
- {problem}: {stem} -- {recommendation}

## Masking Map

| Pair | Worst Band | Severity | Recommendation |
|------|-----------|----------|----------------|
| {stem_a} vs {stem_b} | {frequency band} | {low/medium/high} | {action} |

## Overall Assessment

{One paragraph: honest, opinionated summary of the session quality, the main challenges, and the suggested overall approach. Be specific -- "the drums are well-recorded but the bass has significant noise" is useful. "The recordings are of mixed quality" is not. NEVER speculate about how the stems were created (AI-separated, pre-mastered, etc.) -- report what the measurements say and let the user provide context about provenance.}

## Recommended Processing Order

Address items in this order:

1. {stem}: {action} (dealbreaker/significant)
2. {stem}: {action}
3. ...

{Processing order rationale: dealbreakers first, then significant problems, then start building the mix addressing moderate issues as you go. Respect signal chain logic -- fix phase before EQ, remove noise before compression, remove DC offset before anything else.}

---

## Usage Notes

- Fill values from `batch_diagnostic` and `multi_stem_masking` results
- List problems in descending severity order within each tier
- The per-stem summary table should include every stem, even clean ones (mark as "clean")
- Width values come from `analyze_stereo` (0.0 = mono, higher = wider)
- Masking map only needs pairs with medium or high severity -- skip low-severity pairs
- The recommended processing order is a priority list, not a rigid sequence
- If comparing to a genre profile or reference, add a "Reference Comparison" section after the masking map with the key deviations
- If stems have mismatched bit depths, note each stem's bit depth in the Key Issues column
- If stems have significantly different durations, note outliers in the Key Issues column
- Aggregate headroom is an estimate based on individual stem peaks -- it's not a precise measurement, but it gives the session-architect and mix-engineer a heads-up on gain staging
