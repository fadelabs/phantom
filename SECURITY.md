# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.1.x   | Yes       |
| < 1.1   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in Phantom, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, email: **phantom-audio@proton.me**

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to Expect

- **Acknowledgment:** Within 48 hours
- **Assessment:** Within 7 days
- **Fix timeline:** Critical vulnerabilities within 30 days; others in the next release

### Scope

The following are in scope:

- `src/phantom/` — all Python source code
- `plugin/` — Claude Code plugin skills (if they contain executable logic)
- Path traversal or file access bypasses
- Dependency vulnerabilities in core dependencies

The following are out of scope:

- Vulnerabilities in optional dependencies (demucs, matchering, pedalboard) — report to their maintainers
- Issues requiring local file system access beyond configured directories (Phantom is designed to run locally)

## Security Design

Phantom runs as a local MCP server over stdio. It does not expose network endpoints by default. File **writes** are always confined to an output directory — `PHANTOM_OUTPUT_DIR` when set, otherwise a `~/.phantom/output` sandbox created on demand. File **reads** may target any path by default (analyzing arbitrary audio is Phantom's core purpose); set `PHANTOM_AUDIO_DIR` to confine reads to a directory tree as well.

### Installer Telemetry

Both installers (`install.sh` and `install.ps1`) report anonymized telemetry to `fadelab.net` at install start, completion, and failure: OS, architecture, phantom version (when known), chosen extras, and a per-run install ID. No audio or personal data is sent. Opt out with `PHANTOM_NO_TELEMETRY=1`.
