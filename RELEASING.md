# Releasing Phantom

Complete workflow for publishing a new version to GitHub, PyPI, and the Claude Code marketplace.

## When to Bump Versions

Use [semantic versioning](https://semver.org/) — `MAJOR.MINOR.PATCH`:

| Change type | Bump | Example |
|-------------|------|---------|
| Bug fix, typo, small tweak | PATCH | 1.1.1 → 1.1.2 |
| New feature, new skill, new CLI command | MINOR | 1.1.2 → 1.2.0 |
| Breaking change (renamed tools, changed API, removed features) | MAJOR | 1.2.0 → 2.0.0 |

**Rules of thumb:**
- If a user's existing workflow still works after updating → PATCH or MINOR
- If a user has to change anything on their end → MAJOR
- Skill content improvements (better prompts, better thresholds) → PATCH
- New MCP tools or CLI commands → MINOR
- Renamed or removed MCP tools → MAJOR

## Pre-Release Checklist

1. **All changes committed and pushed to main**
2. **Tests pass:** `uv run pytest tests/ -x -q`
3. **Linting clean:** `uv run ruff check src/ tests/ packages/`
4. **Format clean:** `uv run ruff format --check src/ tests/ packages/`
5. **Version number updated** in both places (see below)

Use `uv run ruff` (not `uv tool run ruff`) so checks run the ruff version
pinned in the dev dependencies — the same one CI and the pre-push hook use.

## Step 1: Bump the Version

Update the version in **three files**:

```bash
# 1. pyproject.toml (line 6)
version = "X.Y.Z"

# 2. plugin/.claude-plugin/plugin.json
"version": "X.Y.Z"

# 3. .claude-plugin/marketplace.json -- plugins[0].source.ref, with a "v" prefix
"ref": "vX.Y.Z"
```

The third is easy to miss and the test suite enforces it:
`tests/test_cli_setup.py::TestMarketplaceVersionPin` fails when the marketplace
`ref` does not equal `v` + the plugin version, so the pre-release checks above
will not pass until all three agree.

`uv.lock` also records the project version. Any `uv run` after the bump rewrites
it, so it shows up as an unstaged change — commit it with the rest rather than
leaving the lock disagreeing with `pyproject.toml`.

Commit:
```bash
git add pyproject.toml plugin/.claude-plugin/plugin.json \
  .claude-plugin/marketplace.json uv.lock
git commit -m "chore: bump version to X.Y.Z"
```

## Step 2: Tag and Push

```bash
git tag vX.Y.Z
git push && git push origin vX.Y.Z
```

## Step 3: Publish to PyPI

```bash
uv build
uv publish --token "$(security find-generic-password -a pypi -s pypi -w)"
```

Without file arguments, `uv publish` uploads **every** file in `dist/` —
including artifacts left over from earlier releases. Clear `dist/` before
building, or pass explicit paths: `uv publish --token ... dist/phantom_audio-X.Y.Z*`.

**Sibling package:** the stem-separation plugin lives in
`packages/phantom-audio-separation` (its own version in
`packages/phantom-audio-separation/pyproject.toml`). When it has changes to
release, build and publish it too:

```bash
uv build --package phantom-audio-separation
uv publish --token "$(security find-generic-password -a pypi -s pypi -w)" dist/phantom_audio_separation-*
```

Verify it works:
```bash
uv tool install phantom-audio --python 3.13 --force
phantom --version
```

## Step 4: Confirm the Anthropic catalog pin advanced

**There is no "notify Anthropic" step. That was wrong.** Anthropic's community
catalog pins each plugin to a **commit SHA on your default branch** and a nightly
CI sweep (07:23 UTC) opens a `bump/<name>` PR when your `main` moves ahead. A
human on their side merges it, and the public directory syncs nightly after that.
Normal turnaround is one to three days.

Two consequences worth internalizing:

- **They track `main`, not our tag.** Their entry carries `"ref": "main"` plus a
  pinned `sha`. Our own `.claude-plugin/marketplace.json` says `"ref": "v1.5.0"`,
  and the D-01 test asserts that matches the tag and `plugin.json`. That
  invariant governs *our* marketplace only — the Anthropic catalog never reads it.
- **The version users see comes from `plugin/.claude-plugin/plugin.json` at the
  pinned SHA.** So bumping that file and pushing to `main` is normally all it
  takes.

Check the pin after every release:

```bash
curl -sSL https://raw.githubusercontent.com/anthropics/claude-plugins-community/main/.claude-plugin/marketplace.json \
  | python3 -c "import json,sys; p=[x for x in json.load(sys.stdin)['plugins'] if x['name']=='phantom'][0]; print(p['source'])"
git rev-list --count <that-sha>..main   # 0 means the pin is current
```

If the pin is stale, first run the same validation their sweep runs — a failure
there produces no PR and no notification, the pin just silently holds:

```bash
claude plugin validate ./plugin --strict
```

If validation passes and the pin still has not moved after a few days, re-submit
through <https://clau.de/plugin-directory-submission> and say in the notes which
SHA it is stuck on. **Do not open a PR against `anthropics/claude-plugins-community`
— external PRs are auto-closed.**

Directory description, homepage and category come from the submission record, not
the repo. Editing the repo will not change them. Never change the plugin's `name`;
it breaks existing installs.

### Our own marketplace

Separately, update `.claude-plugin/marketplace.json` so users who add
`fadelabs/phantom` directly get the new version:

```bash
# ref = the tag name
git rev-parse HEAD  # if you also want to record a sha
```

Update the `ref`, commit, and push.

## Quick Reference

| What | Where | Command |
|------|-------|---------|
| Version (package) | `pyproject.toml` line 6 | edit manually |
| Version (plugin) | `plugin/.claude-plugin/plugin.json` | edit manually |
| Version (marketplace ref) | `.claude-plugin/marketplace.json` | edit manually, `vX.Y.Z` |
| Tests | local | `uv run pytest tests/ -x -q` |
| Lint | local | `uv run ruff check src/ tests/ packages/` |
| Build | local | `uv build` |
| Publish to PyPI | pypi.org | `uv publish --token "$(security find-generic-password -a pypi -s pypi -w)"` |
| Tag | GitHub | `git tag vX.Y.Z && git push origin vX.Y.Z` |
| Install test | local | `uv tool install phantom-audio --python 3.13 --force` |

## Example: Full Release

```bash
# 1. Make sure everything is clean
uv run pytest tests/ -x -q
uv run ruff check src/ tests/ packages/

# 2. Bump version (edit both files)
# pyproject.toml: version = "1.2.0"
# plugin/.claude-plugin/plugin.json: "version": "1.2.0"

# 3. Commit, tag, push
git add pyproject.toml plugin/.claude-plugin/plugin.json
git commit -m "chore: bump version to 1.2.0"
git tag v1.2.0
git push && git push origin v1.2.0

# 4. Build and publish to PyPI
uv build
uv publish --token "$(security find-generic-password -a pypi -s pypi -w)"

# 5. Verify
uv tool install phantom-audio --python 3.13 --force
phantom --version  # should show 1.2.0

# 6. Update marketplace sha (if applicable)
# Edit .claude-plugin/marketplace.json with new ref/sha
# git add, commit, push
```
