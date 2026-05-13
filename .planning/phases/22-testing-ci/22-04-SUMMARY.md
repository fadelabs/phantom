---
phase: 22-testing-ci
plan: 04
subsystem: testing
tags: [pytest, long-audio, optional-deps, integration-tests]

# Dependency graph
requires: [22-01]
provides:
  - Long audio duration tests (60s stereo) for detect_problems and full_diagnostic
  - Optional dependency integration tests for Matchering, Demucs, and Pedalboard
affects: [22-05]

# Tech tracking
tech-stack:
  added: []
  patterns: [session-scoped long audio fixture reuse, MCP client fixture for tool testing, skipif guards for optional deps]

key-files:
  created:
    - tests/test_long_audio.py
    - tests/test_optional_deps.py
  modified: []

key-decisions:
  - "Duplicated absence tests from test_server.py into test_optional_deps.py for CI simplicity (per D-22)"
  - "Presence tests verify import + callable attribute only, no actual processing (per D-10)"

patterns-established:
  - "Long audio tests use session-scoped fixture with @pytest.mark.slow + @pytest.mark.timeout(120)"
  - "Optional dep tests use _has_module helper with mirrored skipif guards for presence/absence"

requirements-completed: [D-10, D-11, D-12, D-14, D-22]

# Metrics
duration: 4min
completed: 2026-05-13
---

# Phase 22 Plan 04: Long Audio and Optional Dependency Tests Summary

**Duration tests for 60s audio and conditional integration tests for Matchering, Demucs, and Pedalboard**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-13T17:07:26Z
- **Completed:** 2026-05-13T17:11:24Z
- **Tasks:** 2/2
- **Files created:** 2

## Accomplishments

- Created `tests/test_long_audio.py` with 2 tests verifying detect_problems and full_diagnostic complete on 60s stereo audio without timeout or crash
- Created `tests/test_optional_deps.py` with 6 tests: 3 presence tests (import + callable check) and 3 absence tests (DependencyMissingError with install hint)
- Both long audio tests marked with `@pytest.mark.slow` and `@pytest.mark.timeout(120)`
- Optional dep tests use correct skipif guards for both installed and absent scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Create long audio duration tests** - `c92557d` (test)
2. **Task 2: Create optional dependency integration tests** - `95bf7db` (test)

## Files Created/Modified

- `tests/test_long_audio.py` - 2 tests: detect_problems and full_diagnostic on 60s stereo audio
- `tests/test_optional_deps.py` - 6 tests: 3 presence (matchering, demucs, pedalboard import) + 3 absence (DependencyMissingError via MCP client)

## Decisions Made

- Duplicated absence tests from test_server.py per D-22 (test organization at Claude's discretion) for CI job simplicity
- Presence tests only verify import and callable attribute, not actual processing (avoids slow model downloads and real audio requirements)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-existing test failure in `tests/test_processing.py::TestRecipes::test_recipe_mud_returns_two_plugins` due to missing optional `pedalboard` dependency. Not caused by this plan's changes (out of scope, same as reported in 22-01-SUMMARY).

## Self-Check: PASSED

- All files verified present on disk
- All commit hashes verified in git log

---
*Phase: 22-testing-ci*
*Completed: 2026-05-13*
