---
phase: 20-security-hardening
plan: 02
subsystem: cli/setup-reaper
tags: [security, supply-chain, version-pinning, lua-whitelist, tdd]
dependency_graph:
  requires: []
  provides: [version-pinned-clone, lua-file-whitelist]
  affects: [phantom-cli, reaper-integration]
tech_stack:
  added: []
  patterns: [version-tag-pinning, file-whitelist-guard, fallback-with-warning]
key_files:
  created: []
  modified:
    - src/phantom/cli/setup_reaper.py
    - tests/test_cli_setup_reaper.py
decisions:
  - "EXPECTED_LUA_FILES as module-level constant for easy auditing and extension"
  - "Fallback to HEAD clone on missing tag (not blocking) to avoid breaking dev workflow"
  - "Yellow warning for both fallback and unexpected files -- visible but non-fatal"
metrics:
  duration: 5m 57s
  completed: 2026-05-13
  tasks: 1
  files_modified: 2
---

# Phase 20 Plan 02: Reaper Bridge Version Pin + Lua Whitelist Summary

Version-pinned Reaper MCP bridge clone using --branch v{version} tag with HEAD fallback, and EXPECTED_LUA_FILES whitelist blocking untrusted file injection into Reaper Scripts directory.

## Task Completion

| Task | Name | Type | Commit(s) | Files |
|------|------|------|-----------|-------|
| 1 (RED) | Failing tests for version pin + Lua whitelist | test | `671a842` | tests/test_cli_setup_reaper.py |
| 1 (GREEN) | Implement version pin, fetch/checkout update, Lua whitelist | feat | `fcd374a` | src/phantom/cli/setup_reaper.py, tests/test_cli_setup_reaper.py |

## Changes Made

### src/phantom/cli/setup_reaper.py

- Added `from phantom import __version__` import for version tag construction
- Added `EXPECTED_LUA_FILES = ["reaper_mcp_bridge.lua"]` module-level constant
- **Fresh clone (D-01):** `git clone --depth 1 --branch v{__version__}` with fallback to HEAD if tag missing (D-03)
- **Update path (D-01):** Replaced `git pull --ff-only` with `git fetch --tags` + `git checkout v{__version__}` with fallback warning (D-03)
- **Lua copy (D-06/D-07):** Added `if lua_file.name not in EXPECTED_LUA_FILES` guard that skips and warns about unexpected files

### tests/test_cli_setup_reaper.py

- `TestVersionPinning` class (3 tests):
  - `test_version_pin_fresh_clone` -- clone includes --branch v{version}
  - `test_version_pin_update_uses_fetch_checkout` -- update uses fetch+checkout, not pull --ff-only
  - `test_version_pin_fallback_on_missing_tag` -- fallback to HEAD with "unverified" warning
- `TestLuaWhitelist` class (3 tests):
  - `test_whitelist_copies_expected_file` -- reaper_mcp_bridge.lua IS copied
  - `test_whitelist_blocks_unexpected_file` -- evil_payload.lua is NOT copied
  - `test_unexpected_lua_warning` -- output contains "Skipping unexpected" for non-whitelisted files

## Threat Mitigations

| Threat ID | Status | Implementation |
|-----------|--------|----------------|
| T-20-02 | Mitigated | Clone uses --branch v{__version__} tag |
| T-20-02a | Mitigated | Update uses fetch --tags + checkout v{version} |
| T-20-03 | Mitigated | EXPECTED_LUA_FILES whitelist with warn-and-skip |
| T-20-02b | Accepted | Missing tags fall back to HEAD with yellow warning |

## Deviations from Plan

None -- plan executed exactly as written.

## TDD Gate Compliance

- RED gate: `671a842` (test commit) -- 5 of 6 tests correctly failing, 1 passing (expected file copy already worked)
- GREEN gate: `fcd374a` (feat commit) -- all 6 tests passing
- REFACTOR gate: skipped (no meaningful cleanup needed after ruff formatting)

## Verification

```
22 passed in 0.45s (setup_reaper tests)
766 passed, 28 skipped in 9.18s (full suite)
ruff check: All checks passed
ruff format: All files formatted
```

## Known Stubs

None.
