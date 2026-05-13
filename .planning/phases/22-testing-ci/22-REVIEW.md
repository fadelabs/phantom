---
phase: 22-testing-ci
reviewed: 2026-05-13T20:15:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - .github/dependabot.yml
  - .github/workflows/ci.yml
  - tests/conftest.py
  - tests/test_error_schema.py
  - tests/test_long_audio.py
  - tests/test_optional_deps.py
findings:
  critical: 1
  warning: 2
  info: 1
  total: 4
status: issues_found
---

# Phase 22: Code Review Report

**Reviewed:** 2026-05-13T20:15:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed CI workflow, dependabot config, shared test fixtures, and three new test files. The test design is generally solid: dynamic tool discovery, session-scoped fixtures for expensive audio generation, and dual presence/absence testing for optional dependencies. One critical issue will cause CI to fail on first run: unused imports in `test_long_audio.py` that violate the project's ruff linting rules (which run as a CI gate). Two warnings address silent CI failure masking and a fragile error-schema test fallback.

## Critical Issues

### CR-01: Unused imports in test_long_audio.py will fail the CI lint gate

**File:** `tests/test_long_audio.py:9,13`
**Issue:** `json` (line 9) and `ToolError` (line 13) are imported but never used. The CI workflow runs `uv run ruff check src/ tests/` as a gating step before tests. Ruff reports two F401 violations on this file, which will cause the CI pipeline to fail before any tests execute. Verified by running `uv run ruff check tests/test_long_audio.py` locally -- exits with code 1.
**Fix:**
```python
# Remove lines 9 and 13. The resulting imports should be:
from __future__ import annotations

import pytest
from fastmcp import Client

from phantom.audio import load_audio
from phantom.problems import detect_problems
from phantom.server import mcp
```

## Warnings

### WR-01: optional-deps CI job silently swallows failures via continue-on-error

**File:** `.github/workflows/ci.yml:45`
**Issue:** The `optional-deps` job sets `continue-on-error: true` at the job level. This means any test failure in `tests/test_optional_deps.py` (or even installation failures for optional extras) will show as a green check on PRs. Real regressions in optional dependency integration (matchering, demucs, pedalboard) will be invisible. The intent may have been to avoid blocking merges when optional deps have upstream breakage, but the current setting provides zero signal.
**Fix:** Remove `continue-on-error: true` from the job level and, if needed, apply it only to the install step where upstream breakage is expected:
```yaml
  optional-deps:
    name: Optional dependencies
    runs-on: ubuntu-latest
    # Removed: continue-on-error: true

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v8
        with:
          enable-cache: true

      - name: Install Python 3.12
        run: uv python install 3.12

      - name: Install with optional extras
        continue-on-error: true  # tolerate upstream dep issues
        run: uv sync --locked --python 3.12 --extra matching --extra separation --extra processing

      - name: Test optional dependencies
        run: uv run pytest tests/test_optional_deps.py -x -q --tb=short
```

### WR-02: Error-schema test has a silent catch-all fallback for unknown tools

**File:** `tests/test_error_schema.py:99-100`
**Issue:** The `_get_bad_args` function has a fallback at line 99 that returns `{"file_path": "/nonexistent/test.wav"}` for any tool not explicitly listed in the mapping or the `single_file_tools` set. If a new tool is added that does not accept a `file_path` parameter, this fallback will cause an unexpected error (possibly not a `ToolError` at all, or a `ToolError` with a different schema), leading to a confusing test failure that obscures the real issue: the test's coverage map is stale. A safer approach would fail explicitly when encountering an unrecognized tool.
**Fix:**
```python
    # Replace lines 99-100 with an explicit failure:
    raise ValueError(
        f"No bad_args mapping for tool '{tool_name}'. "
        f"Add it to _get_bad_args() or _SKIP_TOOLS."
    )
```

## Info

### IN-01: CI matrix does not cover all declared Python versions

**File:** `.github/workflows/ci.yml:18`
**Issue:** The CI matrix tests Python 3.10 and 3.12, but `pyproject.toml` declares support for 3.10, 3.11, 3.12, and 3.13 (via classifiers and `requires-python = ">=3.10,<3.14"`). Python 3.11 and 3.13 are untested. This is not blocking but risks undiscovered compatibility issues on those versions.
**Fix:** Add 3.11 and 3.13 to the matrix, or at minimum add 3.13 as the latest supported version:
```yaml
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12", "3.13"]
```

---

_Reviewed: 2026-05-13T20:15:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
