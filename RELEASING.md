# Releasing Phantom

Release from a reviewed branch after local checks and remote CI pass. This is a
public repository: inspect the staged diff, outgoing commits, PR description,
and release notes for secrets, personal information, private plans, local paths,
and AI session links. Keep all repository hooks enabled.

## Prepare the version

Use a patch version for compatible fixes, a minor version for new commands or
features, and a major version for incompatible public API changes.

Update all three public version fields together:

- `pyproject.toml`: project version.
- `plugin/.claude-plugin/plugin.json`: plugin version.
- `.claude-plugin/marketplace.json`: plugin source ref, `vX.Y.Z`.

Run `uv lock` and include `uv.lock` in the same change. The marketplace pin test
checks that the plugin version and tag agree. The separation sibling has an
independent version; release it separately when it has changes to distribute.

DAW bridges also have independent versions. `REAPER_MCP_VERSION` in
`src/phantom/cli/setup_reaper.py` must name an existing, tested bridge release tag.
It must not be derived from the Phantom version. `ABLETON_PACKAGE` in
`src/phantom/cli/setup_ableton.py` pins the external Ableton package. Verify both
installation paths before publishing a release that changes either pin.

## Validate and merge

```bash
uv sync --locked --extra dev --extra processing --extra matching
uv run ruff check src/ tests/ packages/
uv run ruff format --check src/ tests/ packages/
uv run pytest tests/ -x -q
uv run pre-commit run --all-files
```

Use the project’s pinned Ruff through `uv run`. Check optional separation tests
in an environment with that sibling installed. Record skipped manual DAW tests
honestly; configuration tests do not prove a connected session works.

Stage only reviewed public files, commit with the normal hooks, and push the
checked-out branch. Inspect all remote CI results before merging. Verify main’s
checks after the merge, then tag the tested merge commit. Do not force-push,
skip hooks, or tag an unreviewed commit to work around a failure.

## Build and publish

Build into a fresh release directory so old artifacts cannot be uploaded:

```bash
uv build --out-dir dist/X.Y.Z
```

Inspect wheel and source archive contents and metadata, and install the wheel in
an isolated environment to check the CLI version and startup. Publish only those
exact artifact paths using `uv publish` with credentials from the configured
secret store. Never print a token or put it in a committed command or log.

Create `vX.Y.Z` at the tested main commit, push that specific tag, and publish the
matching GitHub release. Release notes should explain user-visible changes,
installation requirements, and material limitations. Verify the package version
on PyPI and the release artifacts on GitHub before describing it as released.

If the separation sibling also needs a release, build its package explicitly
with `uv build --package phantom-audio-separation` into a separate fresh directory,
inspect it, and publish only its exact files.

## Marketplace and documentation

Our marketplace uses the release tag committed above. Validate the plugin with
`claude plugin validate ./plugin --strict` when that CLI is available.

The external Anthropic catalog has its own review and update process. Inspect
its actual Phantom entry after publication; do not promise an automatic update
or a turnaround time. A successful GitHub or PyPI release does not establish that
an external directory has refreshed. Never rename the plugin as an update fix.

Deploy fadelab.net documentation describing the new release after the package is
available. Check the public installation instructions and changed documentation
pages after deployment. Keep unreleased Studio capabilities clearly identified.
