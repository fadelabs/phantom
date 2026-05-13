---
phase: 18-bug-fixes-ux
plan: "03"
subsystem: analysis-engine
tags: [edge-cases, guards, hum-detection, masking, essentia]
dependency_graph:
  requires: []
  provides:
    - "explicit hum detection 2-second guard"
    - "explicit band energy sub-frame guard"
  affects:
    - src/phantom/problems.py
    - src/phantom/masking.py
tech_stack:
  added: []
  patterns:
    - "duration guard before Essentia HumDetector"
    - "length guard before Essentia FrameGenerator"
key_files:
  created: []
  modified:
    - src/phantom/problems.py
    - src/phantom/masking.py
    - tests/test_problems.py
    - tests/test_masking.py
decisions:
  - "Guard at 2.0s not 1.0s for hum detection — 1.9s audio triggers false hum positives from Essentia"
  - "Sub-frame guard returns zeros explicitly rather than relying on FrameGenerator zero-padding"
metrics:
  duration: "237s"
  completed: "2026-05-13T02:57:49Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 18 Plan 03: Analysis Edge Case Guards Summary

Explicit guards for hum detection (< 2s) and band energy computation (< 4096 samples) with TDD test coverage

## Completed Tasks

| Task | Name | Commit(s) | Key Changes |
|------|------|-----------|-------------|
| 1 | Raise hum detection guard to 2 seconds | `6aec7c3` (RED), `05e9e5d` (GREEN) | Guard in `_detect_hum` changed from 1.0s to 2.0s; 6 edge case tests added |
| 2 | Add explicit length guard to _compute_band_energies | `532fff1` (RED), `7c4eb65` (GREEN) | Early return for sub-frame audio; 4 edge case tests added |

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

- Task 1 RED: `6aec7c3` (test commit) -- 1.9s test fails as expected (HumDetector returns false positive at 1.9s)
- Task 1 GREEN: `05e9e5d` (feat commit) -- guard raised to 2.0s, all 52 problem tests pass
- Task 2 RED: `532fff1` (test commit) -- 100-sample test fails as expected (FrameGenerator zero-pads short audio)
- Task 2 GREEN: `7c4eb65` (feat commit) -- explicit guard added, all 34 masking tests pass

## What Changed

### Task 1: Hum Detection Guard

In `src/phantom/problems.py`, the `_detect_hum()` function's duration guard was raised from `1.0` to `2.0` seconds. The comment was updated to explain that audio shorter than 2 seconds has insufficient data for reliable PSD measurement by Essentia's HumDetector. Testing revealed that at 1.9 seconds, the HumDetector produces false positive hum detections (reporting 59.3 Hz with 0.997 salience on a synthetic signal), confirming the guard is necessary.

Six new edge case tests were added in a `TestHumEdgeCases` class covering 0.5s, 1.0s, 1.5s, 1.9s (all return empty), 2.0s (returns non-empty), and an integration test.

### Task 2: Band Energy Sub-Frame Guard

In `src/phantom/masking.py`, an explicit early return was added to `_compute_band_energies()` for audio shorter than `frame_size` (4096 samples). Previously, Essentia's FrameGenerator would zero-pad the short audio and produce non-zero (but meaningless) band energies. The new guard returns `np.zeros(10)` with a three-line comment explaining why zero energy is the acoustically correct answer.

Four new edge case tests were added in a `TestBandEnergiesEdgeCases` class covering 100-sample, 4095-sample (both return zeros), 4096-sample (returns non-zero), and 0-sample (returns zeros).

## Verification

- `uv run pytest tests/test_problems.py tests/test_masking.py -x -q` -- 86 passed
- `uv tool run ruff check src/phantom/problems.py src/phantom/masking.py` -- all checks passed
- `uv tool run ruff format --check src/phantom/problems.py src/phantom/masking.py` -- already formatted

## Known Stubs

None.

## Self-Check: PASSED

All 4 modified files verified present. All 4 commit hashes verified in git log.
