---
phase: 21-performance-optimization
plan: 03
subsystem: analysis-engine
tags: [performance, fft, spectrum-sharing, tdd]
dependency_graph:
  requires: []
  provides:
    - "FFT-sharing optimization in detect_problems"
    - "Optional spectral_flatness kwarg on _detect_band_excess"
    - "Optional power_spectrum kwarg on _detect_resonances and _detect_lossy_codec"
  affects:
    - src/phantom/problems.py
    - tests/test_problems.py
tech_stack:
  added: []
  patterns:
    - "Pre-computed FFT values passed via optional keyword arguments"
    - "Detectors remain standalone-callable with None defaults"
key_files:
  created: []
  modified:
    - src/phantom/problems.py
    - tests/test_problems.py
decisions:
  - "keyword-only arguments (after *) for optional FFT kwargs to avoid positional ambiguity"
  - "power_spectrum passed as full tuple including None-check for consistency with existing return type"
metrics:
  duration: 5min
  completed: "2026-05-13T14:53:41Z"
  tasks: 1
  files: 2
---

# Phase 21 Plan 03: FFT Spectrum Sharing in detect_problems Summary

TDD-refactored detect_problems to pre-compute spectral_flatness (4096) and average_power_spectrum (8192) once, eliminating 4 redundant FFT passes across frequency-domain detectors.

## Changes Made

### src/phantom/problems.py

- Added `spectral_flatness: float | None = None` keyword-only parameter to `_detect_band_excess` -- when None, computes own; when provided, uses value directly
- Added `power_spectrum: tuple[np.ndarray, np.ndarray] | None = None` keyword-only parameter to `_detect_resonances` -- same standalone/shared pattern
- Added same `power_spectrum` keyword-only parameter to `_detect_lossy_codec`
- Updated `detect_problems` to pre-compute `flatness = _spectral_flatness(mono)` and `spectrum_8k = _average_power_spectrum(mono, 8192, sample_rate)` after the near-silence guard
- Passes `spectral_flatness=flatness` to all 3 `_detect_band_excess` calls
- Passes `power_spectrum=spectrum_8k` to `_detect_resonances` and `_detect_lossy_codec`

### tests/test_problems.py

- Added `TestFFTSpectrumSharing` class with 10 tests covering:
  - Standalone mode for all 3 detector types (spectral_flatness=None, power_spectrum=None)
  - Shared mode with mock verification (confirms internal FFT functions not called when pre-computed values provided)
  - Low flatness threshold bypass with provided value
  - Regression test for result equivalence
  - Integration tests verifying detect_problems calls _spectral_flatness exactly once (not 3 times) and _average_power_spectrum exactly once (not 2 times)

## Deviations from Plan

None -- plan executed exactly as written.

## TDD Gate Compliance

- RED: `c264ab2` -- `test(21-03): add failing tests for FFT spectrum sharing` (9 of 10 tests failed as expected)
- GREEN: `33e0eca` -- `feat(21-03): implement FFT spectrum sharing in detect_problems` (all 73 tests pass)
- REFACTOR: not needed -- implementation was minimal and clean

## Verification Results

```
tests/test_problems.py: 73 passed
Full suite (excl optional deps): 795 passed, 37 skipped
ruff check: All checks passed
ruff format: 2 files already formatted
```

## Self-Check: PASSED

- FOUND: src/phantom/problems.py
- FOUND: tests/test_problems.py
- FOUND: .planning/phases/21-performance-optimization/21-03-SUMMARY.md
- FOUND: c264ab2 (RED commit)
- FOUND: 33e0eca (GREEN commit)
