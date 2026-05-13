---
phase: 19-tech-debt-cleanup
plan: 02
subsystem: core-engine
tags: [refactor, constants, thread-safety, tech-debt]
dependency_graph:
  requires: []
  provides:
    - RECOMMENDED_PYTHON constant in exceptions.py
    - Thread-safe profile cache in _profiles.py
    - Named threshold constants in problems.py
  affects:
    - src/phantom/exceptions.py
    - src/phantom/cli/_formatting.py
    - src/phantom/cli/doctor.py
    - src/phantom/cli/setup.py
    - src/phantom/_profiles.py
    - src/phantom/problems.py
tech_stack:
  added: []
  patterns:
    - module-level constant extraction (RECOMMENDED_PYTHON)
    - threading.Lock for shared mutable state
    - _UNDERSCORE_PREFIX naming for module-internal constants
key_files:
  created: []
  modified:
    - src/phantom/exceptions.py
    - src/phantom/cli/_formatting.py
    - src/phantom/cli/doctor.py
    - src/phantom/cli/setup.py
    - src/phantom/_profiles.py
    - src/phantom/problems.py
decisions:
  - "Placed RECOMMENDED_PYTHON before class definitions in exceptions.py for visibility"
  - "Lock scope limited to dict access only; file I/O outside lock to avoid holding during slow ops"
  - "Used _UNDERSCORE_PREFIX convention matching comparison/_common.py for problems.py constants"
metrics:
  duration: 5m 55s
  completed: 2026-05-13T04:37:14Z
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
  tests_passed: 732
  tests_skipped: 37
---

# Phase 19 Plan 02: Constants & Thread Safety Summary

Single-source RECOMMENDED_PYTHON constant eliminating four-site version drift, threading.Lock on profile cache for safe concurrent MCP access, and 14 named threshold constants in problems.py.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 81af81a | Extract RECOMMENDED_PYTHON constant to single source of truth |
| 2 | 69e7016 | Add thread lock to profile cache and extract magic number constants |

## Task Details

### Task 1: Extract RECOMMENDED_PYTHON constant and update 4 call sites

Added `RECOMMENDED_PYTHON = "3.13"` as a module-level constant in `exceptions.py`. Updated all four call sites (`DependencyMissingError.__init__`, `_formatting.py`, `doctor.py`, `setup.py`) to import and reference this constant instead of hardcoded `"3.13"` strings. Future Python version bumps require changing only one line.

### Task 2: Add thread lock to profile cache and extract magic number constants

**Thread safety:** Added `threading.Lock` to protect `_profile_cache` dictionary reads and writes in `_profiles.py`. Lock scope is intentionally minimal -- only dict access is synchronized. File I/O and profile validation remain outside the lock to avoid holding it during slow operations.

**Magic numbers:** Extracted 14 inline threshold values from `problems.py` into named constants with descriptive names and PROB-XX comments. Constants follow the `_UNDERSCORE_PREFIX` convention established in `comparison/_common.py`. All threshold values are unchanged.

Constants extracted:
- `_CLIPPING_THRESHOLD`, `_DC_OFFSET_THRESHOLD`
- `_ISP_OVERSHOOT_THRESHOLD_DB`, `_ISP_SEVERE_DBTP`
- `_DYNAMIC_SPREAD_MIN_DB`, `_NOISE_FLOOR_MODERATE_DB`, `_NOISE_FLOOR_MINOR_DB`
- `_SNR_PROFESSIONAL_DB`, `_SNR_POOR_DB`
- `_SPECTRAL_FLATNESS_MIN`, `_BAND_EXCESS_THRESHOLD_DB`
- `_RESONANCE_MEDIAN_FLOOR_DB`, `_RESONANCE_PROMINENCE_DB`
- `_LOSSY_SHELF_DROP_DB`

## Verification Results

- 732 tests passed, 37 skipped (all skips are pre-existing optional-dep guards)
- 1 pre-existing test error (`test_loudness.py` -- missing `pyloudnorm` module, unrelated)
- All 6 modified files pass `ruff check` cleanly
- No hardcoded `"3.13"` strings remain outside the constant definition
- Profile cache lock verified as `threading.Lock` instance
- All 14 constants importable from `phantom.problems`
- 33 total constant references in problems.py (14 definitions + 19 usages)

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None.
