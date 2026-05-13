---
phase: 22-testing-ci
plan: 01
subsystem: testing
tags: [pytest, pytest-timeout, fixtures, markers]

# Dependency graph
requires: []
provides:
  - pytest-timeout dev dependency for test timeouts
  - slow marker registration (pyproject.toml + conftest.py hook)
  - long_stereo_60s session-scoped fixture (60s stereo, 2.6M samples)
affects: [22-02, 22-03, 22-04, 22-05]

# Tech tracking
tech-stack:
  added: [pytest-timeout>=2.4]
  patterns: [session-scoped fixtures for expensive audio generation]

key-files:
  created: []
  modified:
    - pyproject.toml
    - tests/conftest.py
    - uv.lock

key-decisions:
  - "Belt-and-suspenders marker registration: slow marker in both pyproject.toml and conftest.py pytest_configure hook"

patterns-established:
  - "Session-scoped fixtures for long audio: generate once, reuse across all tests"
  - "Phase 22 fixture section header convention in conftest.py"

requirements-completed: [D-13, D-15, D-16, D-17, D-21]

# Metrics
duration: 4min
completed: 2026-05-13
---

# Phase 22 Plan 01: Test Infrastructure Foundation Summary

**pytest-timeout dependency, slow marker registration, and 60s stereo session-scoped fixture for long audio tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-05-13T16:50:06Z
- **Completed:** 2026-05-13T16:54:26Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Added pytest-timeout>=2.4 as dev dependency enabling `@pytest.mark.timeout()` on long tests
- Registered `slow` marker in pyproject.toml and conftest.py for filtering long-running tests
- Created `long_stereo_60s` session-scoped fixture: 440Hz sine + noise, stereo, 2,646,000 samples

## Task Commits

Each task was committed atomically:

1. **Task 1: Add pytest-timeout dev dependency and register slow marker** - `1d98aa2` (chore)
2. **Task 2: Add 60s stereo session-scoped fixture to conftest.py** - `289c058` (feat)

## Files Created/Modified
- `pyproject.toml` - Added pytest-timeout>=2.4 to dev deps, slow marker to pytest markers
- `tests/conftest.py` - Added long_stereo_60s session-scoped fixture, slow marker in pytest_configure
- `uv.lock` - Updated with pytest-timeout dependency

## Decisions Made
- Registered slow marker in both pyproject.toml and conftest.py pytest_configure hook (belt-and-suspenders per plan spec)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failure in `tests/test_processing.py::TestRecipes::test_recipe_mud_returns_two_plugins` due to missing optional `pedalboard` dependency. Not caused by this plan's changes (out of scope). All 877 other tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- pytest-timeout available for timeout decorators in Plans 02-05
- slow marker ready for `-m "not slow"` filtering in CI pipeline (Plan 05)
- long_stereo_60s fixture available for duration-handling tests (Plans 02-04)

## Self-Check: PASSED

- All files verified present on disk
- All commit hashes verified in git log

---
*Phase: 22-testing-ci*
*Completed: 2026-05-13*
