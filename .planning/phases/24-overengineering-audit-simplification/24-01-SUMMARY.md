---
phase: 24-overengineering-audit-simplification
plan: 01
subsystem: utils
tags: [tdd, decorator, exception-handling, simplification]
dependency_graph:
  requires: []
  provides: [wrap_errors-decorator]
  affects: [analysis-modules]
tech_stack:
  added: []
  patterns: [decorator-factory, functools-wraps]
key_files:
  created: []
  modified:
    - src/phantom/_utils.py
    - tests/test_utils.py
decisions:
  - Decorator catches PhantomError (base class) rather than listing each subclass individually
  - Synchronous-only implementation (no async) per plan spec
metrics:
  duration: 271s
  completed: 2026-05-13T10:17:44Z
  tasks_completed: 3
  tasks_total: 3
---

# Phase 24 Plan 01: wrap_errors Decorator Summary

TDD-built decorator factory that replaces the repetitive try/except AnalysisError pattern found in 15 analysis functions, catching PhantomError subclasses to pass through and wrapping all other exceptions in AnalysisError with a descriptive prefix.

## TDD Gate Compliance

| Gate | Commit | Description |
|------|--------|-------------|
| RED | f9c7153 | 11 failing tests for all wrap_errors behaviors |
| GREEN | 8dab93d | wrap_errors implementation passes all 11 tests |
| REFACTOR | -- | No refactoring needed; implementation already minimal |

## What Was Built

The `wrap_errors` decorator in `src/phantom/_utils.py`:
- Decorator factory accepting a `message_prefix` string parameter
- PhantomError subclasses (AnalysisError, AudioLoadError, PathSecurityError, ProfileLoadError, DependencyMissingError) pass through unchanged
- All other exceptions are caught and re-raised as `AnalysisError(f"{prefix}: {exc}")` with `__cause__` chain preserved
- Uses `functools.wraps` to preserve `__name__` and `__doc__` on decorated functions
- 10 lines of logic, synchronous only

## Test Coverage

11 tests in `TestWrapErrors` class covering:
- Normal return value passthrough
- All 5 PhantomError subclasses pass through unchanged
- ValueError wrapped in AnalysisError with prefix message
- RuntimeError wrapped with `__cause__` chain preserved
- `__name__` preservation via functools.wraps
- `__doc__` preservation
- `*args`/`**kwargs` forwarding

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| f9c7153 | test | Add 11 failing tests for wrap_errors decorator (RED) |
| 8dab93d | feat | Implement wrap_errors decorator in _utils.py (GREEN) |

## Verification

```
uv run pytest tests/test_utils.py -x -q -k "WrapErrors" -> 11 passed
uv run pytest tests/ -x -q -> 845 passed, 31 skipped
uv tool run ruff check src/phantom/_utils.py tests/test_utils.py -> All checks passed
uv tool run ruff format --check -> 2 files already formatted
uv run python -c "from phantom._utils import wrap_errors" -> import OK
```

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None.

## Metrics

| Metric | Value |
|--------|-------|
| Lines added to _utils.py | 30 (imports + decorator + docstring) |
| Tests added | 11 |
| Duration | ~4.5 minutes |
| Full suite regression | 0 failures |
