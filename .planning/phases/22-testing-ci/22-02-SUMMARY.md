---
phase: 22-testing-ci
plan: 02
subsystem: testing
tags: [mcp, error-schema, wrap-errors, tdd, fastmcp, pytest]

# Dependency graph
requires: []
provides:
  - "Error schema consistency tests for all 19 MCP tools"
  - "wrap_errors decorator coverage verification across 10 analysis modules"
  - "Dynamic tool count assertion (D-20)"
affects: [testing-ci, server, analysis-modules]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dynamic tool discovery via client.list_tools() for schema tests"
    - "_assert_error_schema helper for reusable error JSON validation"
    - "_get_bad_args mapping for per-tool error trigger arguments"

key-files:
  created:
    - tests/test_error_schema.py
  modified: []

key-decisions:
  - "Skip list_profiles in error schema test (no error path with bad args)"
  - "Use empty file_paths list for batch_diagnostic error trigger (batch_diagnostic catches per-file errors internally)"
  - "Assert tool count >= 19 (not ==) so test survives additions"

patterns-established:
  - "Dynamic tool discovery: use client.list_tools() not hardcoded tool names"
  - "Error schema helper: _assert_error_schema validates {error_type, message, context}"

requirements-completed: [D-20]

# Metrics
duration: 6min
completed: 2026-05-13
---

# Phase 22 Plan 02: Error Schema Consistency Summary

**TDD error schema tests verifying all 18 error-producing MCP tools return consistent {error_type, message, context} JSON and all 14 analysis functions use @wrap_errors**

## Performance

- **Duration:** 6 min
- **Started:** 2026-05-13T16:51:13Z
- **Completed:** 2026-05-13T16:57:23Z
- **Tasks:** 1 (TDD RED/GREEN/REFACTOR cycle)
- **Files modified:** 1

## Accomplishments

- Created comprehensive error schema tests covering 18 of 19 MCP tools (list_profiles skipped -- no error path)
- Dynamic tool discovery via client.list_tools() ensures tests never go stale when tools are added (D-20)
- Verified @wrap_errors decorator coverage across all 10 analysis modules (14 decorated functions)
- All 4 tests pass (881 total test suite pass, 28 skipped, 0 related failures)

## TDD Gate Compliance

1. `test(22-02): add error schema consistency tests` -- RED gate (b9d304a)
2. GREEN gate -- tests pass against existing production code (test-only plan, no feat commit needed)
3. `refactor(22-02): extract error schema assertion helper` -- REFACTOR gate (fb81b32)

RED and REFACTOR gate commits present. GREEN gate is implicit (test-only plan validates existing code).

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Error schema tests** - `b9d304a` (test)
2. **Task 1 REFACTOR: Helper extraction + formatting** - `fb81b32` (refactor)

## Files Created/Modified

- `tests/test_error_schema.py` - 4 test functions: error schema consistency for all tools, tool count minimum, wrap_errors coverage, module count meta-test

## Decisions Made

- **batch_diagnostic skip strategy:** batch_diagnostic catches per-file errors internally (returns them as result entries, not ToolErrors). Used empty file_paths list to trigger validation-level ToolError instead.
- **list_profiles excluded:** This tool takes no arguments and has no failure path reachable with bad input. Added to _SKIP_TOOLS set.
- **>= 19 tool count assertion:** Using >= rather than == prevents test breakage when new tools are added while still catching accidental tool removal.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] batch_diagnostic does not raise ToolError on nonexistent files**
- **Found during:** Task 1 (RED phase)
- **Issue:** Plan suggested `file_paths: ["/nonexistent/a.wav"]` for batch_diagnostic, but batch_diagnostic catches file errors per-stem and returns them embedded in results, not as ToolError
- **Fix:** Changed to `file_paths: []` which triggers the validation-level ToolError (empty list check)
- **Files modified:** tests/test_error_schema.py
- **Verification:** test_all_tools_return_consistent_error_schema passes for batch_diagnostic
- **Committed in:** b9d304a (RED commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary correction for batch_diagnostic error trigger strategy. No scope creep.

## Issues Encountered

- Pre-existing test failure in tests/test_processing.py::TestRecipes::test_recipe_mud_returns_two_plugins (missing optional pedalboard dependency). Not related to this plan's changes.
- Worktree .venv required `uv sync --extra dev` to install pytest (dev dependency not initially present).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Error schema regression tests are in place, future tool additions will be automatically covered via dynamic discovery
- wrap_errors coverage test will catch any new analysis module that forgets the decorator

---
*Phase: 22-testing-ci*
*Completed: 2026-05-13*
