---
phase: 24-overengineering-audit-simplification
plan: 03
subsystem: analysis-modules
tags: [refactor, decorator, exception-handling, dead-code-removal, simplification]
dependency_graph:
  requires: [wrap_errors-decorator]
  provides: [simplified-exception-handling]
  affects: [spectral, loudness, dynamics, stereo, phase, masking, problems, processing, separation, profiles]
tech_stack:
  added: []
  patterns: [decorator-based-error-handling]
key_files:
  created: []
  modified:
    - src/phantom/spectral.py
    - src/phantom/loudness.py
    - src/phantom/dynamics.py
    - src/phantom/stereo.py
    - src/phantom/phase.py
    - src/phantom/masking.py
    - src/phantom/problems.py
    - src/phantom/processing.py
    - src/phantom/separation.py
    - src/phantom/_profiles.py
    - tests/test_processing.py
decisions:
  - Used exact existing error message prefix from each function for wrap_errors decorator
  - Both analyze_masking and analyze_masking_matrix use same prefix "Masking analysis failed" (matching existing code)
  - separation.py FileNotFoundError from internal calls now wrapped by decorator (acceptable - gives clearer error context)
  - ALLOWED_OPERATIONS module-level name removed (breaking change documented per D-03)
metrics:
  duration: 721s
  completed: 2026-05-13T10:43:22Z
  tasks_completed: 2
  tasks_total: 2
---

# Phase 24 Plan 03: Apply wrap_errors Across Analysis Modules Summary

Replaced inline try/except AnalysisError patterns with the @wrap_errors decorator across all 12 analysis functions in 10 modules. Removed dead _has_builtin_profile function and over-engineered _AllowedOpsProxy class, saving 101 lines total.

## What Was Done

### Task 1: Apply wrap_errors to 9 analysis modules + remove dead code

Applied the @wrap_errors decorator to 10 analysis functions across 9 modules, removing identical try/except AnalysisError boilerplate from each. Also removed the dead `_has_builtin_profile` function from `_profiles.py` (0 callers confirmed).

### Task 2: Remove _AllowedOpsProxy and apply wrap_errors to processing.py

Removed the _AllowedOpsProxy class (~20 lines), renamed `_get_allowed_operations` to public `get_allowed_operations`, applied @wrap_errors to `apply_processing` and `fix_audio`, and updated tests to use the new public function name.

## Line Count Changes

| File | Before | After | Delta | Simplification |
|------|--------|-------|-------|----------------|
| src/phantom/spectral.py | 198 | 193 | -5 | @wrap_errors replaces try/except |
| src/phantom/loudness.py | 180 | 175 | -5 | @wrap_errors replaces try/except |
| src/phantom/dynamics.py | 133 | 128 | -5 | @wrap_errors replaces try/except |
| src/phantom/stereo.py | 221 | 216 | -5 | @wrap_errors replaces try/except |
| src/phantom/phase.py | 304 | 294 | -10 | @wrap_errors on 2 functions |
| src/phantom/masking.py | 344 | 334 | -10 | @wrap_errors on 2 functions |
| src/phantom/problems.py | 727 | 722 | -5 | @wrap_errors replaces try/except |
| src/phantom/separation.py | 148 | 139 | -9 | @wrap_errors replaces try/except |
| src/phantom/_profiles.py | 341 | 334 | -7 | Dead _has_builtin_profile removed |
| src/phantom/processing.py | 619 | 579 | -40 | @wrap_errors on 2 functions, _AllowedOpsProxy removed |
| **Total** | **3215** | **3114** | **-101** | |

## Breaking Changes (per D-03)

The `ALLOWED_OPERATIONS` module-level name has been removed from `processing.py`. Callers that previously used `ALLOWED_OPERATIONS[key]` or `ALLOWED_OPERATIONS.keys()` must now use `get_allowed_operations()[key]` or `get_allowed_operations().keys()`. This is a public API change. No external consumers were found in the codebase.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| 854f0cb | refactor | Apply wrap_errors to 10 analysis functions, remove dead _has_builtin_profile |
| 76663bc | refactor | Remove _AllowedOpsProxy, apply wrap_errors to processing.py |

## Verification

```
grep -rn "except AnalysisError" [all 10 modules] -> 0 matches
grep -rn "@wrap_errors" src/phantom/ -> 12 decorators across 10 modules
uv run pytest tests/ -x -q -> 858 passed, 29 skipped
uv tool run ruff check src/ tests/ -> All checks passed
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] separation.py error prefix mismatch**
- **Found during:** Task 1
- **Issue:** Plan specified "Stem separation failed" as the error prefix for separate_stems, but the actual code uses "Source separation failed"
- **Fix:** Used the actual code prefix "Source separation failed" as the plan instructs to match existing error messages exactly
- **Files modified:** src/phantom/separation.py
- **Commit:** 854f0cb

**2. [Rule 1 - Bug] masking_matrix error prefix mismatch**
- **Found during:** Task 1
- **Issue:** Plan specified "Masking matrix analysis failed" but both analyze_masking and analyze_masking_matrix use "Masking analysis failed" in the existing code
- **Fix:** Used the actual code prefix "Masking analysis failed" for both functions
- **Files modified:** src/phantom/masking.py
- **Commit:** 854f0cb

## Known Stubs

None.

## Metrics

| Metric | Value |
|--------|-------|
| Lines removed (net) | 101 |
| Modules modified | 10 source + 1 test |
| Decorators added | 12 |
| Dead functions removed | 1 (_has_builtin_profile) |
| Dead classes removed | 1 (_AllowedOpsProxy) |
| Duration | ~12 minutes |
| Full suite regression | 0 failures |

## Self-Check: PASSED
