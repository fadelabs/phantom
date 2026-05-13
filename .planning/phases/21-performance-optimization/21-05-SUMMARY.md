---
phase: 21-performance-optimization
plan: 05
subsystem: core-analysis
tags: [cache-integration, resampling, comparison, phase, masking, performance]
dependency_graph:
  requires:
    - phantom._cache.analysis_cache
    - phantom._resample.resample_to_match
  provides:
    - "Cached analysis calls in compare_to_reference and compare_to_profile"
    - "Auto-resampling in compare_phase, analyze_masking, analyze_masking_matrix"
  affects:
    - src/phantom/comparison.py
    - src/phantom/phase.py
    - src/phantom/masking.py
tech_stack:
  added: []
  patterns:
    - "Cache-through helper pattern: check cache -> compute -> store"
    - "Auto-resample to max rate on sample rate mismatch"
key_files:
  created: []
  modified:
    - src/phantom/comparison.py
    - src/phantom/phase.py
    - src/phantom/masking.py
    - tests/test_comparison.py
    - tests/test_phase.py
    - tests/test_masking.py
decisions:
  - "Used _cached_analysis helper function rather than inline cache calls for consistency"
  - "Clear cache in tests that mock analysis functions to prevent stale cache interference"
  - "Updated existing sample-rate-mismatch tests from expect-raise to expect-success"
metrics:
  duration: 8min
  completed: "2026-05-13"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
  test_count: 130
  test_pass: 130
---

# Phase 21 Plan 05: Cache and Resample Integration Summary

Wired AnalysisCache into comparison.py for cached analysis calls (10 cache lookups across compare_to_reference and compare_to_profile) and resample_to_match into phase.py and masking.py to auto-resample on sample rate mismatch instead of raising AnalysisError.

## Task Summary

| Task | Name | Commits | Status |
|------|------|---------|--------|
| 1 | Wire AnalysisCache into comparison.py | `2557466` (RED), `6793e0a` (GREEN) | Complete |
| 2 | Wire resample_to_match into phase.py, masking.py | `46c5838` (RED), `15ce26f` (GREEN) | Complete |

## TDD Gate Compliance

Both tasks followed RED/GREEN TDD gates:
- Task 1: `test(21-05)` commit `2557466` (RED) -> `feat(21-05)` commit `6793e0a` (GREEN)
- Task 2: `test(21-05)` commit `46c5838` (RED) -> `feat(21-05)` commit `15ce26f` (GREEN)

## Changes Made

### Task 1: AnalysisCache integration in comparison.py

- Added `from phantom._cache import analysis_cache` import
- Created `_cached_analysis(audio, func_name, func)` helper that checks cache before calling analysis functions, stores results on miss
- `compare_to_reference`: 8 analysis calls (4 functions x 2 audio inputs) wrapped with `_cached_analysis` -- second call with same audio hits cache
- `compare_to_profile`: 4 analysis calls (spectrum, loudness, dynamics, stereo) wrapped with `_cached_analysis`
- Fixed `TestReferenceComparisonUnionBands` to clear cache before running mocked analysis (existing test was getting stale cached results)
- 4 new tests in `TestAnalysisCaching`: cache population, cache hits on repeat, profile caching, helper existence

### Task 2: Auto-resampling in phase.py and masking.py

- `compare_phase`: Replaced `raise AnalysisError("Sample rate mismatch...")` with auto-resample -- lower-rate audio upsampled to higher rate via `resample_to_match`
- `analyze_masking`: Same pattern -- auto-resample lower-rate audio to higher rate
- `analyze_masking_matrix`: Replaced multi-rate AnalysisError with list comprehension resampling all stems to max rate
- Updated docstrings to document auto-resample behavior
- Updated 3 existing tests from expect-raise to expect-success (TestSampleRateMismatch in phase, test_sample_rate_mismatch and test_sample_rate_mismatch_in_matrix in masking)
- 6 new tests across TestComparePhaseResample (3) and TestMaskingResample (3)

## Verification Results

```
uv run pytest tests/test_comparison.py tests/test_phase.py tests/test_masking.py -x -q --tb=short
130 passed in 1.40s

uv run pytest tests/ -x -q --tb=short --ignore=tests/test_processing.py
877 passed, 28 skipped in 9.04s

uv tool run ruff check src/phantom/comparison.py src/phantom/phase.py src/phantom/masking.py
All checks passed!

uv tool run ruff format --check src/phantom/comparison.py src/phantom/phase.py src/phantom/masking.py
3 files already formatted
```

Note: Pre-existing pedalboard test failures (tests/test_processing.py) are unrelated to this plan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cache interference with mocked analysis tests**
- **Found during:** Task 1 GREEN phase
- **Issue:** `TestReferenceComparisonUnionBands` patches `phantom.comparison.analyze_spectrum` but the cache retained results from prior tests, preventing the mock from being called
- **Fix:** Added `autouse` fixture to clear analysis cache before/after mock-based test class
- **Files modified:** tests/test_comparison.py
- **Commit:** 6793e0a

**2. [Rule 1 - Bug] Existing sample-rate-mismatch tests expected AnalysisError**
- **Found during:** Task 2 GREEN phase
- **Issue:** 3 existing tests expected `pytest.raises(AnalysisError, match="Sample rate mismatch")` but the behavior now auto-resamples
- **Fix:** Updated tests to verify successful auto-resample instead of expected exception
- **Files modified:** tests/test_phase.py, tests/test_masking.py
- **Commit:** 15ce26f

## Known Stubs

None.

## Threat Flags

None -- no new network endpoints, auth paths, file access patterns, or schema changes introduced. All changes are internal wiring of existing utilities.

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 2557466 | test | Add failing tests for AnalysisCache integration in comparison.py (RED) |
| 6793e0a | feat | Wire AnalysisCache into comparison.py with _cached_analysis helper (GREEN) |
| 46c5838 | test | Add failing tests for auto-resample in phase.py and masking.py (RED) |
| 15ce26f | feat | Wire resample_to_match into phase.py and masking.py (GREEN) |

## Self-Check: PASSED

All 6 files exist, all 4 commits verified in git log.
