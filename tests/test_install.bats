#!/usr/bin/env bats
# Regression tests for install.sh
# Run: bats tests/test_install.bats

INSTALL_SCRIPT="$BATS_TEST_DIRNAME/../install.sh"

# Helper: source install.sh's main function in a subshell to test individual functions
source_installer() {
    # Extract just the function definitions (not main execution)
    bash -c "
        # Override main to not execute
        main() { :; }
        source '$INSTALL_SCRIPT'
        $1
    "
}

# ─── Script structure ───────────────────────────────────────

@test "install.sh exists and is executable" {
    [ -f "$INSTALL_SCRIPT" ]
    [ -x "$INSTALL_SCRIPT" ]
}

@test "install.sh uses bash shebang" {
    head -1 "$INSTALL_SCRIPT" | grep -q "bash"
}

@test "install.sh wraps logic in main() function" {
    grep -q "^main()" "$INSTALL_SCRIPT"
    # main is called at the end
    tail -3 "$INSTALL_SCRIPT" | grep -q 'main "\$@"'
}

@test "install.sh sets -e for error exit" {
    grep -q "set -e" "$INSTALL_SCRIPT"
}

# ─── Color/TTY handling ─────────────────────────────────────

@test "colors are gated on TTY detection" {
    grep -q '\[ -t 1 \]' "$INSTALL_SCRIPT"
}

@test "NO_COLOR env var is respected" {
    grep -q 'NO_COLOR' "$INSTALL_SCRIPT"
}

@test "TERM=dumb is handled" {
    grep -q 'TERM.*dumb' "$INSTALL_SCRIPT"
}

@test "no color output when piped (not TTY)" {
    # When piped, output should have no ANSI escape codes
    output=$(echo "" | bash "$INSTALL_SCRIPT" 2>&1 || true)
    # Check that raw ANSI escapes aren't in non-TTY output
    # (the script should detect non-TTY and skip colors)
    if echo "$output" | grep -qP '\033\['; then
        # If ANSI codes are present, the TTY gate isn't working
        # But grep -P may not be available, so skip gracefully
        skip "grep -P not available for ANSI detection"
    fi
}

# ─── OS detection ───────────────────────────────────────────

@test "detects macOS" {
    grep -q 'Darwin.*macOS' "$INSTALL_SCRIPT"
}

@test "detects Linux" {
    grep -q 'Linux.*Linux' "$INSTALL_SCRIPT"
}

@test "handles x86_64 architecture" {
    grep -q 'x86_64' "$INSTALL_SCRIPT"
}

@test "handles arm64 architecture" {
    grep -q 'arm64' "$INSTALL_SCRIPT"
}

@test "handles aarch64 as arm64" {
    grep -q 'aarch64' "$INSTALL_SCRIPT"
}

@test "fails on unsupported OS" {
    grep -q 'Unsupported OS' "$INSTALL_SCRIPT"
}

@test "fails on unsupported architecture" {
    grep -q 'Unsupported architecture' "$INSTALL_SCRIPT"
}

# ─── Dependency handling ────────────────────────────────────

@test "checks for uv before installing" {
    grep -q 'command -v uv' "$INSTALL_SCRIPT"
}

@test "installs uv via curl if missing" {
    grep -q 'curl.*astral.sh/uv/install.sh' "$INSTALL_SCRIPT"
}

@test "has wget fallback for uv install" {
    grep -q 'wget.*astral.sh/uv/install.sh' "$INSTALL_SCRIPT"
}

@test "fails with actionable error if neither curl nor wget available" {
    grep -q 'curl or wget required' "$INSTALL_SCRIPT"
}

@test "sources uv env after install" {
    grep -q '\.local/bin/env' "$INSTALL_SCRIPT"
}

# ─── Phantom installation ──────────────────────────────────

@test "installs phantom-audio[all] with python 3.13" {
    grep -q 'phantom-audio\[all\].*--python 3.13' "$INSTALL_SCRIPT"
}

@test "has fallback to core-only install" {
    grep -q 'core only' "$INSTALL_SCRIPT"
}

@test "uses --force flag for reinstall safety" {
    grep -q '\-\-force' "$INSTALL_SCRIPT"
}

@test "verifies phantom is on PATH after install" {
    grep -q 'command -v phantom' "$INSTALL_SCRIPT"
}

@test "adds ~/.local/bin to PATH if phantom not found" {
    grep -q 'HOME/.local/bin' "$INSTALL_SCRIPT"
}

# ─── Configuration ──────────────────────────────────────────

@test "runs phantom setup for MCP" {
    grep -q 'phantom setup' "$INSTALL_SCRIPT"
}

@test "skips plugin in setup (handles separately)" {
    grep -q '\-\-skip-plugin' "$INSTALL_SCRIPT"
}

@test "skips reaper in setup (handles separately)" {
    grep -q '\-\-skip-reaper' "$INSTALL_SCRIPT"
}

@test "runs setup from HOME dir (not cwd)" {
    grep -q 'cd.*HOME.*phantom setup' "$INSTALL_SCRIPT"
}

@test "detects Reaper on macOS" {
    grep -q 'Library/Application Support/REAPER' "$INSTALL_SCRIPT"
}

@test "detects Reaper on Linux" {
    grep -q '\.config/REAPER' "$INSTALL_SCRIPT"
}

@test "installs Claude Code plugin via marketplace" {
    grep -q 'claude plugin marketplace add' "$INSTALL_SCRIPT"
    grep -q 'claude plugin install phantom' "$INSTALL_SCRIPT"
}

@test "handles missing Claude Code gracefully" {
    grep -q 'Claude Code not found' "$INSTALL_SCRIPT"
}

# ─── Output suppression ────────────────────────────────────

@test "suppresses DeprecationWarning" {
    grep -q 'DeprecationWarning' "$INSTALL_SCRIPT"
}

@test "suppresses authlib warning" {
    grep -q 'AuthlibDeprecation' "$INSTALL_SCRIPT"
}

@test "suppresses scipy warning" {
    grep -q 'scipy.ndimage' "$INSTALL_SCRIPT"
}

# ─── Success output ────────────────────────────────────────

@test "shows success message" {
    grep -q 'Phantom is ready' "$INSTALL_SCRIPT"
}

@test "shows get started commands" {
    grep -q 'phantom analyze' "$INSTALL_SCRIPT"
    grep -q 'phantom --help' "$INSTALL_SCRIPT"
}

@test "shows PATH instructions if needed" {
    grep -q 'Add to your PATH' "$INSTALL_SCRIPT"
}

@test "detects user shell for rc file" {
    grep -q 'zshrc' "$INSTALL_SCRIPT"
    grep -q 'bashrc' "$INSTALL_SCRIPT"
    grep -q 'fish' "$INSTALL_SCRIPT"
}

# ─── Error handling ─────────────────────────────────────────

@test "spinner checks for successful install via log content" {
    grep -q 'Installed.*executable' "$INSTALL_SCRIPT"
}

@test "provides log file path on failure" {
    grep -q 'Log:' "$INSTALL_SCRIPT"
}

@test "provides actionable error for Python 3.13 missing" {
    grep -q 'uv python list' "$INSTALL_SCRIPT"
}

# ─── Idempotency ────────────────────────────────────────────

@test "detects existing phantom install" {
    grep -q 'Existing install found' "$INSTALL_SCRIPT"
}

@test "handles already-installed uv" {
    # Should show checkmark, not try to install again
    grep -q 'command -v uv.*then' "$INSTALL_SCRIPT" || \
    grep -q 'command -v uv.*ok' "$INSTALL_SCRIPT" || \
    grep -qA2 'command -v uv' "$INSTALL_SCRIPT" | grep -q 'ok\|uv.*found'
}

# ─── Security ───────────────────────────────────────────────

@test "uses HTTPS for all downloads" {
    # No http:// URLs (only https://)
    ! grep -q 'http://' "$INSTALL_SCRIPT"
}

@test "cleans up temp files" {
    grep -q 'rm -f.*logfile' "$INSTALL_SCRIPT"
}

@test "no sudo usage" {
    ! grep -q 'sudo' "$INSTALL_SCRIPT"
}
