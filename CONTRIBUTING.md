# Contributing to Phantom

Thank you for your interest in contributing to Phantom! This guide will help you get started.

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md) in all interactions.

Contributions are welcome under the [AGPL-3.0](LICENSE) license (inbound = outbound).

## Development Setup

1. Fork and clone the repository:

   ```bash
   git clone https://github.com/YOUR_USERNAME/phantom.git
   cd phantom
   ```

2. Install dependencies (requires Python 3.10+ and [uv](https://docs.astral.sh/uv/)):

   ```bash
   uv sync --dev
   ```

   Or with pip:

   ```bash
   pip install -e ".[dev]"
   ```

3. Install git hooks:

   ```bash
   # Pre-commit hooks (secret scanning, PII detection, policy checks)
   uv run pre-commit install

   # Pre-push hook (linting, formatting, full test suite)
   ln -sf ../../scripts/pre-push .git/hooks/pre-push
   ```

   The pre-commit hook blocks commits containing secrets, PII, absolute paths, planning docs, or large audio files. The pre-push hook runs ruff linting, formatting checks, and the full pytest suite before each push.

4. Run the test suite:

   ```bash
   uv run pytest tests/ -x -q
   ```

## Code Style

- **Linting:** `uv tool run ruff check src/ tests/`
- **Formatting:** `uv tool run ruff format src/ tests/`
- The pre-push hook runs both automatically before each push
- No manual type checking required (essentia lacks type stubs)

## Architecture Overview

- `src/phantom/` — Core analysis modules, MCP server, CLI entry points
- `plugin/` — Claude Code plugin with 5 domain expert skills
- `tests/` — All tests use synthetic audio fixtures (no real audio files in repo)
- `docs/workflows/` — DAW integration workflow documentation
- `src/phantom/profiles/` — Genre reference profiles (JSON)

See [CLAUDE.md](CLAUDE.md) for deeper architectural guidance.

## How to Contribute

**Bug reports:** Use the [bug report template](https://github.com/fadelabs/phantom/issues/new?template=bug_report.md)

**Feature requests:** Use the [feature request template](https://github.com/fadelabs/phantom/issues/new?template=feature_request.md)

**Pull requests:**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Implement your changes
4. Ensure all checks pass
5. Open a pull request

All PRs require:

- Tests passing (`uv run pytest tests/ -x -q`)
- Ruff linting clean (`uv tool run ruff check src/ tests/`)
- Ruff formatting clean (`uv tool run ruff format --check src/ tests/`)
- Security scan passing (automated via GitHub Actions -- checks for secrets, PII, and policy violations)


New analysis features should follow existing module patterns: input guard, analyze, return Pydantic model. See any module in `src/phantom/` for examples.

Optional dependencies must use lazy imports with `DependencyMissingError`.

## Testing

- All tests use synthetic audio fixtures generated in `tests/conftest.py`
- Never commit real audio files to the repository
- Run a single test file: `uv run pytest tests/test_spectral.py -x -v`
- Run the full suite: `uv run pytest tests/ -v`
- Test marker: `@pytest.mark.live` for tests requiring real audio (gitignored fixtures)

## Optional Dependencies

Phantom uses a tiered dependency system:

| Tier | Packages | Install |
|------|----------|---------|
| **Core** | essentia, scipy, numpy, soundfile, pydantic, FastMCP | `uv sync` |
| **Dev** | pytest, ruff, pyloudnorm | `uv sync --dev` |
| **Separation** | demucs, torch | `uv sync --extra separation` |
| **Matching** | matchering (GPLv3) | `uv sync --extra matching` |
| **Processing** | pedalboard | `uv sync --extra processing` |
| **Analysis** | librosa | `uv sync --extra analysis` |

## License

By submitting a contribution, you agree that your work is licensed under [AGPL-3.0](LICENSE), the same license as the project.
