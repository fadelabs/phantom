# Quick Reference: Parallel Drum Compression

> User says: "The drums need more energy, they sound too thin"

## Prerequisites

Drums on a folder/bus track. Phantom and a Reaper MCP server must both be connected. See [setup-guide.md](setup-guide.md).

## Pipeline

| Stage | Who | Action | Tool/Skill |
|-------|-----|--------|------------|
| 1. Measure | Phantom MCP | `analyze_dynamics` on drum bus | audio-diagnostician |
| 2. Confirm | Skill | Verify high crest factor (> 12 dB) | mix-engineer |
| 3. Execute | Skill + Reaper MCP | Set up parallel compression bus | mix-engineer |
| 4. Verify | Phantom MCP | `analyze_dynamics` confirms crest factor decreased | audio-diagnostician |

## Signal Flow

```mermaid
flowchart LR
    Drums["Drum Bus"] --> Analyze["analyze_dynamics"]
    Analyze --> Confirm["Crest factor > 12 dB<br/>Punch but no body"]
    Confirm --> Recipe["parallel_drum_compression"]
    Recipe --> Reaper["Reaper MCP<br/>Send + Bus + ReaComp"]
    Reaper --> Verify["analyze_dynamics<br/>Crest factor decreased"]
```

## What Happens at Each Stage

1. **Measure** -- Run `analyze_dynamics` on the drum bus. Check the crest factor. Above 12 dB means the drums have transient punch but lack sustain and body.

2. **Confirm** -- High crest factor confirms parallel compression will help. If crest factor is already below 8 dB, the drums are over-compressed -- do not add more compression.

3. **Execute** -- Follow the [parallel_drum_compression](../../plugin/skills/mix-engineer/reaper-recipes.md) recipe: create a "Drum Parallel" track, add a pre-fader send from the drum bus, insert **ReaComp** with heavy settings (10:1, fast attack, 10-15 dB gain reduction), start fader at -inf, blend up slowly.

4. **Verify** -- Run `analyze_dynamics` again. Crest factor should decrease by 2-4 dB. RMS should increase slightly. The drums should sound fuller without losing transient punch.

## Cross-References

- [Parallel compression recipe](../../plugin/skills/mix-engineer/reaper-recipes.md) (parallel_drum_compression)
- [Setup guide](setup-guide.md)

## Expected Time

Analysis: ~1-2 seconds. Parallel compression setup: ~1 second (~3-5 MCP calls, or 1 call with TwelveTake's `add_parallel_compression`).
