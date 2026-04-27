# Quick Reference: Session Setup from Stems

> User says: "Set up a session for these stems, reference: metal"

## Prerequisites

Phantom and a Reaper MCP server must both be connected. See [setup-guide.md](setup-guide.md).

## Pipeline

| Stage | Who | Action | Tool/Skill |
|-------|-----|--------|------------|
| 1. Gather | User | Provide stem file paths | -- |
| 2. Analyze | Phantom MCP | `batch_diagnostic` on all stems | audio-diagnostician |
| 3. Assess | Phantom MCP | `multi_stem_masking` across all stem pairs | audio-diagnostician |
| 4. Reference | Phantom MCP | `compare_to_profile` against genre target | audio-diagnostician |
| 5. Plan | Skill | Read mix brief, choose genre template | session-architect |
| 6. Execute | Reaper MCP | Create tracks, folders, routing, import stems | session-architect |
| 7. Verify | Both | Phantom re-analyzes, user checks Reaper | -- |

## Signal Flow

```mermaid
flowchart LR
    Stems["WAV Stems"] --> Phantom["Phantom MCP<br/>batch_diagnostic"]
    Phantom --> Masking["multi_stem_masking"]
    Masking --> Ref["compare_to_profile"]
    Ref --> Brief["Mix Brief"]
    Brief --> Skill["Session Architect"]
    Skill --> Recipe["setup_metal_session"]
    Recipe --> Reaper["Reaper MCP<br/>Tracks/FX/Routing"]
    Reaper --> Session["Configured Session"]
```

## What Happens at Each Stage

1. **Gather** -- User provides paths to WAV stem files. Every stem must be mono or stereo WAV.

2. **Analyze** -- Phantom runs `batch_diagnostic` on all stems. Returns spectrum, loudness, dynamics, and problems for each stem. Flags sample rate mismatches as a dealbreaker.

3. **Assess** -- Phantom runs `multi_stem_masking` across all stem pairs. Identifies frequency conflicts for sidechain and EQ planning.

4. **Reference** -- Phantom compares against the genre target via `compare_to_profile`. Shows where loudness, frequency balance, dynamics, and stereo width deviate.

5. **Plan** -- Session-architect skill reads the diagnostic results and chooses the appropriate genre template from [session-templates.md](../../plugin/skills/session-architect/session-templates.md).

6. **Execute** -- Claude follows the session setup recipe (e.g., [setup_metal_session](../../plugin/skills/session-architect/reaper-recipes.md)) to create tracks, folders, colors, routing, and import stems in Reaper.

7. **Verify** -- Run `batch_diagnostic` again to confirm stems imported correctly. User visually checks Reaper session layout.

## Cross-References

- [Session setup recipes](../../plugin/skills/session-architect/reaper-recipes.md) (setup_metal_session, setup_pop_session, setup_hiphop_session, setup_electronic_session, setup_from_diagnostic)
- [Session templates](../../plugin/skills/session-architect/session-templates.md)
- [Setup guide](setup-guide.md)

## Expected Time

Analysis: ~5-10 seconds (Python processing). Reaper setup: ~2-4 seconds (~30-50 MCP calls at ~50ms each).
