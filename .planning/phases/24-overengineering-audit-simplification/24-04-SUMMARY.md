---
phase: 24-overengineering-audit-simplification
plan: 04
subsystem: comparison
tags: [consolidation, simplification, module-merge, wrap-errors]
dependency_graph:
  requires: [wrap_errors-decorator]
  provides: [consolidated-comparison-module]
  affects: [test-mock-paths]
tech_stack:
  added: []
  patterns: [wrap-errors-decorator, gpl-lazy-import-isolation]
key_files:
  created:
    - src/phantom/comparison.py
  modified:
    - tests/test_comparison.py
decisions:
  - Applied @wrap_errors to all 3 public functions, replacing inline try/except AnalysisError patterns
  - Preserved match_to_reference lock-file cleanup in finally block (wrap_errors handles exception wrapping around the outer scope)
  - Kept _silent_comparison_result as private function rather than inlining
metrics:
  duration: 289s
  completed: 2026-05-13T10:36:00Z
  tasks_completed: 2
  tasks_total: 2
---

# Phase 24 Plan 04: Comparison Subpackage Consolidation Summary

Merged 5-file comparison/ subpackage (750 lines) into single comparison.py module (665 lines), eliminating 85 lines of overhead and 4 files of indirection while applying @wrap_errors to all 3 public functions.

## What Was Built

Consolidated `src/phantom/comparison/` subpackage into `src/phantom/comparison.py`:

- **Files before:** 5 (`__init__.py`, `_common.py`, `profile.py`, `reference.py`, `match.py`)
- **Files after:** 1 (`comparison.py`)
- **Lines before:** 750
- **Lines after:** 665
- **Net reduction:** 85 lines, 4 files eliminated

Module structure (in order):
1. Consolidated imports (deduplicated across all 4 source files)
2. Constants (_THRESHOLD_ON_TARGET, _WIDTH_RANGES, _BASS_MONO_THRESHOLD)
3. 14 Pydantic models (DeviationResult through MatchResult)
4. 7 private helper functions (_classify_deviation through _unmeasurable_deviation)
5. compare_to_profile() with @wrap_errors("Comparison analysis failed")
6. compare_to_reference() with @wrap_errors("Comparison analysis failed")
7. match_to_reference() with @wrap_errors("Reference matching failed")

## Breaking Changes (per D-03, D-04)

Internal import paths changed. Any code importing from submodule paths must update:

| Old Path | New Path |
|----------|----------|
| `phantom.comparison.profile.compare_to_profile` | `phantom.comparison.compare_to_profile` |
| `phantom.comparison.reference.compare_to_reference` | `phantom.comparison.compare_to_reference` |
| `phantom.comparison.match.match_to_reference` | `phantom.comparison.match_to_reference` |
| `phantom.comparison._common.DeviationResult` | `phantom.comparison.DeviationResult` |

Public API unchanged: `from phantom import compare_to_profile` and `from phantom.comparison import compare_to_profile` both work.

## GPL Isolation Verification

Matchering `import matchering as mg` remains inside `match_to_reference()` function body at line 562 (verified via AST analysis). Not at module level.

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| f9df1fb | feat | Consolidate comparison/ subpackage into single comparison.py module |
| 697bd0c | fix | Update test mock paths from submodule to flat module paths |

## Verification

```
test ! -d src/phantom/comparison/ -> Directory deleted
test -f src/phantom/comparison.py -> Module exists (665 lines)
grep -c "@wrap_errors" -> 3 (one per public function)
grep -c "import matchering" -> 1 (inside function body only, verified by AST)
grep -v '^#' | grep -c "except AnalysisError" -> 0 (inline patterns removed)
uv run python -c "from phantom import compare_to_profile" -> Public API OK
uv run pytest tests/test_comparison.py -x -q -> 56 passed
uv run pytest tests/ -x -q -> 856 passed, 31 skipped
uv tool run ruff check src/ tests/ -> All checks passed
```

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

All files exist, all commits verified.
