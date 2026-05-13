---
phase: 24-overengineering-audit-simplification
plan: 05
subsystem: api
tags: [mcp, error-handling, decorator, refactor]

# Dependency graph
requires:
  - phase: 24-overengineering-audit-simplification
    provides: "_phantom_tool decorator pattern established on 17 tools"
provides:
  - "All 19 MCP tools using consistent @_phantom_tool error handling"
  - "Eliminated duplicated error conversion boilerplate from batch_diagnostic and multi_stem_masking"
affects: [server, mcp-tools]

# Tech tracking
tech-stack:
  added: []
  patterns: ["All MCP tools use @_phantom_tool for uniform error handling"]

key-files:
  created: []
  modified: ["src/phantom/server.py"]

key-decisions:
  - "Accepted empty context dict {} for list[str] args in _phantom_tool (consistent with decorator design, error messages already contain paths)"

patterns-established:
  - "@_phantom_tool decorator: all 19 MCP tools use it, no exceptions"

requirements-completed: [AUDIT-SERVER-STANDARDIZATION]

# Metrics
duration: 3min
completed: 2026-05-13
---

# Phase 24 Plan 05: Server Tool Error Handling Standardization Summary

**Standardized batch_diagnostic and multi_stem_masking to use @_phantom_tool decorator, eliminating duplicated error conversion boilerplate across all 19 MCP tools**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-13T10:13:56Z
- **Completed:** 2026-05-13T10:17:25Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- All 19 MCP tools now use @_phantom_tool decorator (was 17/19)
- Removed 10 lines of duplicated outer try/except boilerplate from batch_diagnostic and multi_stem_masking
- Preserved inner per-stem error handling in batch_diagnostic (graceful degradation for individual stem failures)
- Preserved ToolError validation guards in both functions (max batch, empty list, duplicates, min stems)
- server.py reduced from 555 to 545 lines

## Task Commits

Each task was committed atomically:

1. **Task 1: Add @_phantom_tool to batch_diagnostic and multi_stem_masking** - `5894400` (refactor)

## Files Created/Modified
- `src/phantom/server.py` - Added @_phantom_tool to batch_diagnostic and multi_stem_masking, removed outer try/except blocks, unindented function bodies

## Decisions Made
- Accepted that _phantom_tool context extraction yields {} for list[str] args (isinstance(v, str) skips lists). This is consistent with the decorator's design and all other tools. Error messages from PhantomError already contain relevant file paths. Documented as T-24-07 in threat model.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-existing test failures in test_loudness.py (missing pyloudnorm) and test_processing.py (missing pedalboard) -- these are optional dependencies not installed in the worktree venv. Not caused by this change. All 48 server tests and 763 other tests pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 19 MCP tools now have uniform error handling via @_phantom_tool
- No blockers or concerns

---
*Phase: 24-overengineering-audit-simplification*
*Completed: 2026-05-13*
