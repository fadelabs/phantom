---
phase: 21-performance-optimization
plan: 04
subsystem: core-analysis
tags: [env-var, gcc-phat, masking, performance]
dependency_graph:
  requires: []
  provides:
    - "_get_env_int and _get_env_float helpers in _utils.py"
    - "PHANTOM_PHAT_WINDOW_S env var for GCC-PHAT truncation"
    - "PHANTOM_MASKING_TOP_N env var for masking pair limit"
    - "Adaptive top_n scaling in multi_stem_masking"
  affects:
    - "src/phantom/phase.py (GCC-PHAT window)"
    - "src/phantom/server.py (multi_stem_masking payload)"
tech_stack:
  added: []
  patterns:
    - "_get_env_int/_get_env_float for typed env var parsing with AnalysisError on invalid"
    - "Adaptive default scaling: min(pair_count, max(10, stem_count))"
key_files:
  created: []
  modified:
    - src/phantom/_utils.py
    - src/phantom/phase.py
    - src/phantom/server.py
    - tests/test_utils.py
    - tests/test_phase.py
    - tests/test_server.py
decisions:
  - "GCC-PHAT default window reduced from 30s to 10s (only 50ms lag searched)"
  - "Adaptive top_n formula: min(pair_count, max(10, stem_count)) balances small vs large sessions"
  - "Env var override uses _get_env_int for consistent validation"
metrics:
  duration: "7min"
  completed: "2026-05-13"
  tasks: 2
  files: 6
---

# Phase 21 Plan 04: Env Var Helpers and Performance Wiring Summary

Typed env var helpers (_get_env_int, _get_env_float) in _utils.py, GCC-PHAT window reduced from 30s to 10s via PHANTOM_PHAT_WINDOW_S, and adaptive top_n truncation in multi_stem_masking via PHANTOM_MASKING_TOP_N with formula min(pair_count, max(10, stem_count)).

## Task Summary

| Task | Name | Commit(s) | Status |
|------|------|-----------|--------|
| 1 | Add _get_env_int and _get_env_float to _utils.py | `50cca0c` (RED), `85b28b4` (GREEN) | Complete |
| 2 | Wire PHANTOM_PHAT_WINDOW_S and adaptive PHANTOM_MASKING_TOP_N | `8e57f33` (RED), `8e0e22e` (GREEN) | Complete |

## TDD Gate Compliance

Both tasks followed RED/GREEN TDD gates:
- Task 1: `test(21-04)` commit `50cca0c` (RED) -> `feat(21-04)` commit `85b28b4` (GREEN)
- Task 2: `test(21-04)` commit `8e57f33` (RED) -> `feat(21-04)` commit `8e0e22e` (GREEN)

## Changes Made

### Task 1: Env var helper functions
- Added `_get_env_int(name, default)` to `_utils.py` -- parses integer env vars, returns default on unset/empty, raises `AnalysisError` on invalid
- Added `_get_env_float(name, default)` to `_utils.py` -- same pattern for floats
- 10 tests in `TestGetEnvHelpers` class covering: default, parsed, invalid, empty, whitespace for both types

### Task 2: Performance wiring
- **phase.py**: Replaced `sample_rate * 30` with `_get_env_float("PHANTOM_PHAT_WINDOW_S", 10.0)` -- reduces FFT size by 3x for long files
- **server.py**: Added adaptive top_n truncation to `multi_stem_masking`:
  - Formula: `min(pair_count, max(10, stem_count))`
  - 3 stems (3 pairs) -> all shown; 6 stems (15 pairs) -> top 10; 20 stems (190 pairs) -> top 20
  - `PHANTOM_MASKING_TOP_N` env var overrides adaptive default when explicitly set
  - `pair_count` preserves original total for context
- 3 PHAT window tests + 3 adaptive top_n tests (few stems, many stems, env override)

## Verification

- `uv run pytest tests/test_utils.py tests/test_phase.py tests/test_server.py -x -q` -- 120 passed
- `uv run pytest tests/ -x -q` (excluding pre-existing dep issues) -- 801 passed, 37 skipped
- `ruff check` and `ruff format --check` -- all clean on all 3 source files

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

All 6 files exist. All 4 commits verified (50cca0c, 85b28b4, 8e57f33, 8e0e22e).
