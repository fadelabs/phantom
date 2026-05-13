---
phase: 21-performance-optimization
plan: 02
subsystem: audio-analysis
tags: [resampling, scipy, audio-processing, utility]
dependency_graph:
  requires: []
  provides: [resample_to_match]
  affects: [compare_phase, analyze_masking, analyze_masking_matrix]
tech_stack:
  added: []
  patterns: [polyphase-fir-resampling, gcd-rational-ratio]
key_files:
  created:
    - src/phantom/_resample.py
    - tests/test_resample.py
  modified: []
decisions:
  - "Upsample-only policy: ValueError on downsample attempts to prevent frequency content loss"
  - "GCD-based rational resampling ratios for exact sample count computation"
  - "Per-channel resampling loop for mono/stereo compatibility"
metrics:
  duration: 4min
  completed: "2026-05-13T14:51:48Z"
  tasks_completed: 1
  tasks_total: 1
  files_created: 2
  files_modified: 0
  test_count: 19
  test_pass: 19
---

# Phase 21 Plan 02: Resample-to-Match Utility Summary

Polyphase FIR audio resampling via scipy.signal.resample_poly with upsample-only policy and GCD-based rational ratio computation.

## What Was Built

`resample_to_match(audio, target_sr)` in `src/phantom/_resample.py` -- a utility function that upsamples AudioData to a target sample rate using polyphase FIR filtering. Designed to replace AnalysisError on sample rate mismatch in cross-file operations (compare_phase, analyze_masking, analyze_masking_matrix).

### Key behaviors:
- **Identity fast-path:** Same-rate input returns the original AudioData object (no allocation)
- **Upsample only:** Raises ValueError if target_sr < source rate (prevents frequency content loss)
- **Rational resampling:** GCD-based up/down ratio for exact polyphase filter parameters
- **Channel independence:** Each channel resampled separately, works for mono and stereo
- **Metadata preservation:** file_path, num_channels, float32 dtype all carried through
- **Logging:** Warning emitted with source/target rates when resampling occurs

## TDD Gate Compliance

| Gate | Commit | Verified |
|------|--------|----------|
| RED (failing tests) | 1cb19af | 19 tests, all fail with ModuleNotFoundError |
| GREEN (implementation passes) | 783b4e6 | 19 tests pass, 0 regressions |
| REFACTOR | -- | No refactoring needed; code already clean |

## Test Coverage

19 tests across 6 test classes:

| Class | Tests | Coverage |
|-------|-------|----------|
| TestIdentity | 2 | Same-rate passthrough, no warning logged |
| TestDownsampleRejection | 2 | ValueError on downsample (48k->44.1k, 96k->48k) |
| TestUpsampleMono | 6 | Sample count, rate, 2x exact, duration, channels, dtype |
| TestUpsampleStereo | 3 | Channel count, sample count, array shape |
| TestMetadata | 4 | file_path preserved/None, num_samples matches array, duration formula |
| TestWarning | 2 | Warning logged, contains source/target rates |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 1cb19af | test | Failing tests for resample_to_match (RED gate) |
| 783b4e6 | feat | Implement resample_to_match polyphase FIR resampling (GREEN gate) |

## Deviations from Plan

None -- plan executed exactly as written.

## Verification Results

```
uv run pytest tests/test_resample.py -x -q --tb=short
19 passed in 0.42s

uv run pytest tests/ -x -q --tb=short -k "not live"
535 passed, 1 failed (pre-existing pedalboard dep), 29 deselected

uv tool run ruff check src/phantom/_resample.py tests/test_resample.py
All checks passed!

uv tool run ruff format --check src/phantom/_resample.py tests/test_resample.py
2 files already formatted
```

Note: The 1 pre-existing failure (`test_processing.py::TestRecipes::test_recipe_mud_returns_two_plugins`) requires optional `pedalboard` dependency and is unrelated to this plan.

## Self-Check: PASSED

- [x] src/phantom/_resample.py exists
- [x] tests/test_resample.py exists
- [x] 21-02-SUMMARY.md exists
- [x] Commit 1cb19af (RED) found
- [x] Commit 783b4e6 (GREEN) found
