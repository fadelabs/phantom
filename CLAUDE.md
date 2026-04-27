# CLAUDE.md

This file provides guidance to Claude Code when working with the Phantom codebase.

## Project

Phantom is an AI audio engineering system. It combines an MCP server for audio analysis with Claude Code skills encoding professional mixing/mastering expertise, integrated with Reaper via MCP for DAW control.

**Core Value:** Claude can analyze any audio file or set of stems and produce actionable, measurement-backed mixing and mastering guidance calibrated to a reference target.

## Architecture

- **MCP Server** (`src/phantom/`) -- Python, audio analysis via Essentia + scipy/numpy, served through FastMCP
- **Claude Code Plugin** (`plugin/`) -- 5 domain expert skills: mix-engineer, effects-engineer, mastering-engineer, audio-diagnostician, session-architect
- **CLI** (`src/phantom/cli/`) -- Rich terminal interface for analysis, comparison, separation, rendering
- **Reference Profiles** (`src/phantom/profiles/`) -- 9 genre spectral and dynamics targets as JSON
- **DAW Control** -- via external Reaper MCP server (TwelveTake recommended)

## Tech Stack

| Library | Purpose |
|---------|---------|
| Python 3.10+ | Runtime |
| essentia | Primary analysis engine (spectral, loudness, problem detection) |
| scipy / numpy | Signal processing, array operations |
| soundfile | WAV I/O |
| pydantic | Typed response models |
| FastMCP 2.x | MCP server framework |
| click + rich | CLI interface |

Optional: demucs (stem separation), matchering (reference matching, GPLv3), pedalboard (audio processing)

## Conventions

### Code Patterns

- All analysis modules follow: input guard -> analyze -> return Pydantic model
- Optional dependencies use lazy imports with `DependencyMissingError`
- `PhantomError` hierarchy with musician-friendly error messages
- Env var configuration: `PHANTOM_AUDIO_DIR`, `PHANTOM_OUTPUT_DIR`, `PHANTOM_MAX_DURATION`, `PHANTOM_MAX_FILE_SIZE`

### Testing

- All tests use synthetic audio fixtures (no real audio committed)
- pytest 8.x with pytest-asyncio
- Run: `uv run pytest tests/ -x -q`

### Pre-push Checks

- Linting: `uv tool run ruff check src/ tests/`
- Formatting: `uv tool run ruff format --check src/ tests/`
- Tests: `uv run pytest tests/ -x -q --tb=short`
- Hook: `scripts/pre-push` (auto-runs on git push)

## Privacy

Artist personal information must never appear in commits or public-facing documentation. Reference artists by first name only in internal docs, never in committed code.

## Key Decisions

- **AGPL-3.0** -- open source, copyleft (commercial licensing available separately)
- **Reaper over Cubase** for DAW integration (900+ API functions vs sandboxed JS)
- **Monorepo** -- MCP server usable by any MCP client, skills are Claude Code specific
- **Essentia as primary engine** -- 10-25x faster than librosa for feature extraction
- **Dynamic reference system** -- accepts artist name, genre, song title, or WAV file as mixing/mastering target

## Entry Points

| Command | Source | Description |
|---------|--------|-------------|
| `phantom` | `src/phantom/cli/__init__.py` | CLI entry point (click group) |
| `phantom-mcp` | `src/phantom/server.py` | MCP server entry point |

### MCP Tools (17)

`analyze_spectrum`, `analyze_loudness`, `analyze_dynamics`, `analyze_stereo`, `analyze_phase`, `compare_phase`, `detect_problems`, `analyze_masking`, `analyze_masking_matrix`, `multi_stem_masking`, `compare_to_profile`, `compare_to_reference`, `match_to_reference`, `separate_stems`, `full_diagnostic`, `batch_diagnostic`, `setup_reaper`

### CLI Commands

`phantom analyze`, `phantom compare`, `phantom separate`, `phantom render`, `phantom setup-reaper`, `phantom serve`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

<!-- For detailed internal technical research (dependency analysis, alternatives considered, -->
<!-- version pinning rationale), see .claude.local.md (not committed). -->
