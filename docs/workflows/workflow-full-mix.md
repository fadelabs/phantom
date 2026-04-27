# Quick Reference: Full Mix Workflow

> User says: "Mix this track, reference: rock"

## Prerequisites

Session already set up (see [workflow-session-setup.md](workflow-session-setup.md)). Phantom and a Reaper MCP server must both be connected. See [setup-guide.md](setup-guide.md).

## Pipeline

| Stage | Who | Action | Tool/Skill |
|-------|-----|--------|------------|
| 1. Diagnose | Phantom MCP | `batch_diagnostic` on all stems | audio-diagnostician |
| 2. Masking | Phantom MCP | `multi_stem_masking` across stem pairs | audio-diagnostician |
| 3. Reference | Phantom MCP | `compare_to_profile` against genre target | audio-diagnostician |
| 4. Fix | Skill + Reaper MCP | Address dealbreakers and problems | mix-engineer |
| 5. EQ | Skill + Reaper MCP | Complementary EQ for masking conflicts | mix-engineer |
| 6. Compress | Skill + Reaper MCP | Compression decisions per stem | mix-engineer |
| 7. Spatial | Skill + Reaper MCP | Reverb, delay, panning | mix-engineer + effects-engineer |
| 8. Verify | Phantom MCP | Re-analyze and compare to reference | audio-diagnostician |

## Signal Flow

```mermaid
flowchart LR
    Stems["All Stems"] --> Diag["batch_diagnostic"]
    Diag --> Mask["multi_stem_masking"]
    Mask --> Ref["compare_to_profile"]
    Ref --> Mix["Mix Engineer<br/>EQ + Comp + Spatial"]
    Mix --> Reaper["Reaper MCP<br/>ReaEQ/ReaComp/Sends"]
    Reaper --> Verify["Re-analyze<br/>compare_to_profile"]
```

## What Happens at Each Stage

1. **Diagnose** -- Run `batch_diagnostic` on all stems. Fix dealbreakers first (clipping, DC offset, phase issues).

2. **Masking** -- Run `multi_stem_masking` to find frequency conflicts. High masking at 200-500 Hz across multiple pairs means the mix will sound muddy without complementary EQ.

3. **Reference** -- Run `compare_to_profile` to see how the current balance compares to genre norms. This sets your EQ and loudness targets.

4. **Fix** -- Address problems by severity. Phase issues first, then noise, then frequency problems. Use specific recipes as needed.

5. **EQ** -- Apply [complementary_eq_pair](../../plugin/skills/mix-engineer/reaper-recipes.md) between competing stems. Cut the yielding instrument, gentle boost on the owning instrument.

6. **Compress** -- Set compression per stem based on crest factor. Use [parallel_drum_compression](../../plugin/skills/mix-engineer/reaper-recipes.md) for drum energy. Use [sidechain_bass_to_kick](../../plugin/skills/mix-engineer/reaper-recipes.md) for low-end clarity.

7. **Spatial** -- Add reverb sends, delay throws, panning. Use [ducked_reverb_setup](../../plugin/skills/effects-engineer/reaper-recipes.md) for vocal clarity.

8. **Verify** -- Run `compare_to_profile` again. Deviations from the genre target should have decreased. Check `analyze_stereo` for mono compatibility.

## Cross-References

- [Mixing recipes](../../plugin/skills/mix-engineer/reaper-recipes.md) (complementary_eq_pair, sidechain_bass_to_kick, parallel_drum_compression)
- [Effects recipes](../../plugin/skills/effects-engineer/reaper-recipes.md) (ducked_reverb_setup)
- [Setup guide](setup-guide.md)

## Expected Time

Analysis: ~5-10 seconds. Mixing operations: ~3-5 seconds (~50+ MCP calls at ~50ms each).
