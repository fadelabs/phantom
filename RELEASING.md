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
3. **Linting clean:** `uv tool run ruff check src/ tests/`
4. **Format clean:** `uv tool run ruff format --check src/ tests/`
5. **Version number updated** in both places (see below)

## Step 1: Bump the Version

Update the version in **two files**:

```bash
# 1. pyproject.toml (line 6)
version = "X.Y.Z"

# 2. plugin/.claude-plugin/plugin.json
"version": "X.Y.Z"
```

Commit:
```bash
git add pyproject.toml plugin/.claude-plugin/plugin.json
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
uv publish --token "$(security find-generic-password -a __token__ -s pypi -w)"
```

Verify it works:
```bash
uv tool install phantom-audio --python 3.13 --force
phantom --version
```

## Step 4: Update the Marketplace

If the plugin is on the official Anthropic marketplace, the marketplace entry has a `ref` and `sha` that pin to a specific version. Anthropic manages this on their end after you notify them of a new release. For your own marketplace:

```bash
# Update .claude-plugin/marketplace.json with new ref and sha
# ref = the tag name, sha = the commit hash
git rev-parse HEAD  # get the sha
```

Update the `ref` and `sha` fields, commit, and push.

## Quick Reference

| What | Where | Command |
|------|-------|---------|
| Version (package) | `pyproject.toml` line 6 | edit manually |
| Version (plugin) | `plugin/.claude-plugin/plugin.json` | edit manually |
| Tests | local | `uv run pytest tests/ -x -q` |
| Lint | local | `uv tool run ruff check src/ tests/` |
| Build | local | `uv build` |
| Publish to PyPI | pypi.org | `uv publish --token "$(security find-generic-password -a __token__ -s pypi -w)"` |
| Tag | GitHub | `git tag vX.Y.Z && git push origin vX.Y.Z` |
| Install test | local | `uv tool install phantom-audio --python 3.13 --force` |

## Example: Full Release

```bash
# 1. Make sure everything is clean
uv run pytest tests/ -x -q
uv tool run ruff check src/ tests/

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
uv publish --token "$(security find-generic-password -a __token__ -s pypi -w)"

# 5. Verify
uv tool install phantom-audio --python 3.13 --force
phantom --version  # should show 1.2.0

# 6. Update marketplace sha (if applicable)
# Edit .claude-plugin/marketplace.json with new ref/sha
# git add, commit, push
```
