# Mix Brief Template

Structured mix brief template. After running diagnostics, fill in this template to create the handoff document for mixing. This format ensures all downstream skills (`/phantom:mix-engineer`, `/phantom:session-architect`) can parse the assessment consistently.

## Session Overview

| Property | Value |
|----------|-------|
| Stem count | {N} |
| Sample rate | {rate} Hz |
| Bit depth | {depth}-bit |
| Duration | {duration} |
| Genre / Reference | {genre or reference track} |

## Per-Stem Summary

| Stem | LUFS | Peak (dBTP) | Crest (dB) | Phase Corr. | Key Issues |
|------|------|-------------|------------|-------------|------------|
| {name} | {lufs} | {peak} | {crest} | {correlation} | {issues or "clean"} |

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

{Processing order rationale: dealbreakers first, then significant problems, then start building the mix addressing moderate issues as you go. Respect signal chain logic -- fix phase before EQ, remove noise before compression.}

---

## Usage Notes

- Fill values from `batch_diagnostic` and `multi_stem_masking` results
- List problems in descending severity order within each tier
- The per-stem summary table should include every stem, even clean ones (mark as "clean")
- Masking map only needs pairs with medium or high severity -- skip low-severity pairs
- The recommended processing order is a priority list, not a rigid sequence
- If comparing to a genre profile or reference, add a "Reference Comparison" section after the masking map with the key deviations
