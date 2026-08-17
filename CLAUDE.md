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
- Env var configuration: 40 `PHANTOM_*` runtime variables covering paths/limits, analysis thresholds, FFT/frame sizes, and behavior flags. The canonical registry is `src/phantom/_config.py` (it also drives `phantom doctor`'s environment table); per-knob defaults resolve in `src/phantom/_settings.py`. Installer-only vars live in `install.sh` / `install.ps1`: `PHANTOM_NO_TELEMETRY` (opt out) and `PHANTOM_BIN` (script-internal)

### Testing

- All tests use synthetic audio fixtures (no real audio committed)
- pytest 8.x with pytest-asyncio
- Run: `uv run pytest tests/ -x -q`

### Pre-push Checks

- Linting: `uv run ruff check src/ tests/ packages/`
- Formatting: `uv run ruff format --check src/ tests/ packages/`
- Tests: `uv run pytest tests/ -x -q --tb=short`
- Hook: `scripts/pre-push` (auto-runs on git push)

Use `uv run`, not `uv tool run` -- the latter resolves to the newest ruff, and a
new minor can widen the default rule set, so it fails on rules CI never
enforces. The hook blocks a push whose ref is not the one checked out, since its
checks run against the working tree; `--no-verify` overrides.

## Privacy

Artist personal information must never appear in commits or public-facing documentation. Reference artists by first name only in internal docs, never in committed code.

## Key Decisions

- **AGPL-3.0** -- open source, copyleft (commercial licensing available separately)
- **Reaper over Cubase** for DAW integration (900+ API functions vs sandboxed JS)
- **Monorepo** -- MCP server usable by any MCP client, skills are Claude Code specific
- **Essentia as primary engine** -- 10-25x faster than librosa for feature extraction. Cost: **essentia publishes no Windows wheel, so phantom-audio cannot be installed on Windows at all.** macOS and Linux only. Replacing it with a Windows-capable backend is tracked in issue #52 -- read that issue before touching `loudness.py`, `spectral.py`, `dynamics.py`, `problems.py`, `_bands.py`, or `_truepeak.py`
- **Dynamic reference system** -- accepts artist name, genre, song title, or WAV file as mixing/mastering target

## Entry Points

| Command | Source | Description |
|---------|--------|-------------|
| `phantom` | `src/phantom/cli/__init__.py` | CLI entry point (click group) |
| `phantom-mcp` | `src/phantom/server.py` | MCP server entry point |

### MCP Tools (20)

`analyze_spectrum`, `analyze_loudness`, `analyze_dynamics`, `analyze_stereo`, `analyze_phase`, `compare_phase`, `detect_problems`, `analyze_masking`, `multi_stem_masking`, `compare_to_profile`, `compare_to_reference`, `list_profiles`, `load_profile`, `match_to_reference`, `separate_stems`, `fix_audio`, `apply_processing`, `full_diagnostic`, `batch_diagnostic`, `read_live_metrics`

### CLI Commands

`phantom analyze`, `phantom compare`, `phantom separate`, `phantom render`, `phantom setup-reaper`, `phantom serve`

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

<!-- For detailed internal technical research (dependency analysis, alternatives considered, -->
<!-- version pinning rationale), see .claude.local.md (not committed). -->
