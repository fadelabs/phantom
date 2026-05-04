#!/usr/bin/env bash
# Phantom installer
# curl -sSL https://raw.githubusercontent.com/fadelabs/phantom/main/install.sh | bash

main() {
    set -e

    # ── Cleanup trap (CR-03: kill orphan processes on Ctrl+C) ──
    SPAWNED_PID=""
    TMPFILES=()
    cleanup() {
        if [ -n "$SPAWNED_PID" ] && kill -0 "$SPAWNED_PID" 2>/dev/null; then
            kill "$SPAWNED_PID" 2>/dev/null
            wait "$SPAWNED_PID" 2>/dev/null || true
        fi
        for f in "${TMPFILES[@]}"; do rm -f "$f"; done
    }
    trap cleanup EXIT INT TERM

    # ── Colors (TTY-gated, NO_COLOR respected) ──────────────
    if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "${TERM:-}" != "dumb" ]; then
        BOLD=$'\033[1m'      DIM=$'\033[2m'
        RED=$'\033[31m'      GREEN=$'\033[32m'
        YELLOW=$'\033[33m'   CYAN=$'\033[36m'
        RESET=$'\033[0m'
    else
        BOLD='' DIM='' RED='' GREEN='' YELLOW='' CYAN='' RESET=''
    fi

    ok()   { printf "  %s✓%s %s\n" "$GREEN" "$RESET" "$1"; }
    fail() { printf "  %s✗%s %s\n" "$RED" "$RESET" "$1" >&2; }
    info() { printf "  %s▸%s %s\n" "$CYAN" "$RESET" "$1"; }
    warn() { printf "  %s!%s %s\n" "$YELLOW" "$RESET" "$1"; }
    _ping() { :; }
    err()  { fail "$1"; _ping "install_failed" 2>/dev/null; exit 1; }

    # ── Spinner (CR-03: tracks PID for cleanup, WR-04: ASCII fallback) ──
    run_with_spinner() {
        local msg="$1"
        shift
        local logfile
        logfile=$(mktemp)
        TMPFILES+=("$logfile")

        "$@" > "$logfile" 2>&1 &
        SPAWNED_PID=$!
        local exit_code=0

        if [ -t 1 ]; then
            # Use ASCII spinner for C/POSIX locale compatibility (WR-04)
            local frames
            if [[ "${LANG:-}" == *UTF-8* ]] || [[ "${LC_ALL:-}" == *UTF-8* ]] || [[ "${LC_CTYPE:-}" == *UTF-8* ]]; then
                frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
            else
                frames=('-' '\\' '|' '/')
            fi
            local i=0
            while kill -0 "$SPAWNED_PID" 2>/dev/null; do
                printf "\r  %s %s" "${frames[$((i % ${#frames[@]}))]}" "$msg"
                i=$((i + 1))
                sleep 0.1
            done
            printf "\r\033[2K"
        fi

        wait "$SPAWNED_PID" 2>/dev/null || exit_code=$?
        SPAWNED_PID=""

        if [ "$exit_code" -eq 0 ]; then
            ok "$msg"
            rm -f "$logfile"
            return 0
        else
            # Check if uv reported success despite non-zero exit (WR-03)
            if grep -q "Installed.*executable" "$logfile" 2>/dev/null; then
                warn "$msg (completed with warnings — exit code $exit_code)"
                rm -f "$logfile"
                return 0
            fi
            fail "$msg"
            printf "    %sLog: %s%s\n" "$DIM" "$logfile" "$RESET" >&2
            return 1
        fi
    }

    # ── Header ──────────────────────────────────────────────
    printf "\n"
    printf "  %sPhantom%s %s— AI Audio Engineering%s\n" "$BOLD" "$RESET" "$DIM" "$RESET"
    printf "\n"

    # ── Step 1: OS detection ────────────────────────────────
    OS=$(uname -s)
    ARCH=$(uname -m)

    case "$OS" in
        Darwin) PLATFORM="macOS" ;;
        Linux)  PLATFORM="Linux" ;;
        *)      err "Unsupported OS: $OS (phantom supports macOS and Linux). Windows users: see install.ps1" ;;
    esac

    case "$ARCH" in
        x86_64|amd64)  ARCH_LABEL="x86_64" ;;
        arm64|aarch64) ARCH_LABEL="arm64" ;;
        *)             err "Unsupported architecture: $ARCH" ;;
    esac

    ok "Detected ${PLATFORM} ${ARCH_LABEL}"

    # ── Telemetry (opt-out via PHANTOM_NO_TELEMETRY=1) ─────
    _ping() {
        if [ "${PHANTOM_NO_TELEMETRY:-0}" = "1" ]; then return; fi
        curl -sfL "https://fadelab.net/api/ping?event=$1&os=${PLATFORM}&arch=${ARCH_LABEL}&version=${2:-unknown}&extras=${INSTALL_EXTRAS:-none}" > /dev/null 2>&1 &
    }
    _ping "install_started"

    # ── Step 2: Check/install uv ────────────────────────────
    if command -v uv >/dev/null 2>&1; then
        ok "$(uv --version 2>/dev/null | head -1)"
    else
        info "Installing uv..."
        UV_VERSION="0.11.7"
        local uv_log
        uv_log=$(mktemp)
        TMPFILES+=("$uv_log")
        if command -v curl >/dev/null 2>&1; then
            curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh > "$uv_log" 2>&1
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh > "$uv_log" 2>&1
        else
            err "curl or wget required. Install one and re-run."
        fi

        # Source uv env
        # shellcheck disable=SC1091
        [ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"
        # shellcheck disable=SC1091
        [ -f "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"

        if ! command -v uv >/dev/null 2>&1; then
            fail "uv installation failed"
            printf "    %sLog: %s%s\n" "$DIM" "$uv_log" "$RESET" >&2
            err "See https://docs.astral.sh/uv/ for manual install"
        fi
        ok "uv installed"
    fi

    # ── Step 3: Install phantom ─────────────────────────────
    if command -v phantom >/dev/null 2>&1; then
        EXISTING=$(uv tool list 2>/dev/null | grep phantom-audio | head -1 | sed 's/phantom-audio //' | sed 's/ .*//' || echo "unknown")
        warn "Existing install found: phantom ${EXISTING} — upgrading"
    fi

    # ── Extras prompt (interactive TTY only) ───────────────
    INSTALL_EXTRAS=""
    if [ -t 0 ]; then
        printf "\n"
        printf "  %sWhat to install?%s\n" "$BOLD" "$RESET"
        printf "\n"
        printf "  Core %s(~50MB)%s gives you spectral, loudness, dynamics, stereo,\n" "$DIM" "$RESET"
        printf "  phase, and problem analysis — enough for full mix diagnostics.\n"
        printf "\n"
        printf "  Extras unlock additional capabilities:\n"
        printf "    %s•%s Stem separation %s— split a track into vocals, drums, bass, other%s\n" "$CYAN" "$RESET" "$DIM" "$RESET"
        printf "    %s•%s Reference matching %s— auto-match your mix to a reference track%s\n" "$CYAN" "$RESET" "$DIM" "$RESET"
        # TODO: uncomment when pedalboard integration is wired up
        # printf "    %s•%s Audio processing %s— headless EQ, compression, effects without a DAW%s\n" "$CYAN" "$RESET" "$DIM" "$RESET"
        printf "\n"
        printf "    %s1)%s All extras %s(recommended)%s %s~2.5GB%s\n" "$CYAN" "$RESET" "$DIM" "$RESET" "$DIM" "$RESET"
        printf "    %s2)%s Core only %s~50MB%s\n" "$CYAN" "$RESET" "$DIM" "$RESET"
        printf "    %s3)%s Choose individually\n" "$CYAN" "$RESET"
        printf "\n"
        printf "  Enter choice [1]: "
        read -r EXTRAS_CHOICE
        EXTRAS_CHOICE="${EXTRAS_CHOICE:-1}"

        case "$EXTRAS_CHOICE" in
            1)
                INSTALL_EXTRAS="all"
                ;;
            2)
                INSTALL_EXTRAS=""
                ;;
            3)
                INSTALL_EXTRAS=""
                printf "\n"
                printf "  %sStem separation%s %s~2.5GB%s\n" "$BOLD" "$RESET" "$DIM" "$RESET"
                printf "  Split tracks into vocals, drums, bass, other (Demucs + PyTorch)\n"
                printf "  Install? [Y/n]: "
                read -r SEP_CHOICE
                if [ "${SEP_CHOICE:-y}" != "n" ] && [ "${SEP_CHOICE:-y}" != "N" ]; then
                    INSTALL_EXTRAS="separation"
                fi

                printf "\n"
                printf "  %sReference matching%s %s~10MB, GPLv3 license%s\n" "$BOLD" "$RESET" "$YELLOW" "$RESET"
                printf "  Auto-match your mix's loudness, EQ, and width to a reference track\n"
                printf "  Install? [Y/n]: "
                read -r MATCH_CHOICE
                if [ "${MATCH_CHOICE:-y}" != "n" ] && [ "${MATCH_CHOICE:-y}" != "N" ]; then
                    if [ -n "$INSTALL_EXTRAS" ]; then
                        INSTALL_EXTRAS="${INSTALL_EXTRAS},matching"
                    else
                        INSTALL_EXTRAS="matching"
                    fi
                fi

                # TODO: uncomment when pedalboard integration is wired up
                # printf "\n"
                # printf "  %sAudio processing%s %s~5MB%s\n" "$BOLD" "$RESET" "$DIM" "$RESET"
                # printf "  Headless EQ, compression, and effects without a DAW (Pedalboard)\n"
                # printf "  Install? [Y/n]: "
                # read -r PROC_CHOICE
                # if [ "${PROC_CHOICE:-y}" != "n" ] && [ "${PROC_CHOICE:-y}" != "N" ]; then
                #     if [ -n "$INSTALL_EXTRAS" ]; then
                #         INSTALL_EXTRAS="${INSTALL_EXTRAS},processing"
                #     else
                #         INSTALL_EXTRAS="processing"
                #     fi
                # fi
                ;;
            *)
                INSTALL_EXTRAS="all"
                ;;
        esac
    else
        # Non-interactive: install all by default
        INSTALL_EXTRAS="all"
    fi

    printf "\n"

    if [ -n "$INSTALL_EXTRAS" ]; then
        INSTALL_PKG="phantom-audio[${INSTALL_EXTRAS}]"
    else
        INSTALL_PKG="phantom-audio"
    fi

    if ! run_with_spinner "Installing phantom (this may take a minute)" \
        uv tool install "$INSTALL_PKG" --python 3.13 --force; then

        if [ -n "$INSTALL_EXTRAS" ]; then
            info "Full install failed, trying core only..."
            if ! run_with_spinner "Installing phantom core" \
                uv tool install phantom-audio --python 3.13 --force; then
                err "Installation failed. Check Python 3.13: uv python list | grep 3.13"
            fi
            warn "Extras skipped — install later: uv tool install \"phantom-audio[all]\" --python 3.13 --force"
        else
            err "Installation failed. Check Python 3.13: uv python list | grep 3.13"
        fi
    fi

    # ── Verify install ──────────────────────────────────────
    hash -r 2>/dev/null || true
    export PATH="$HOME/.local/bin:$PATH"
    command -v phantom >/dev/null 2>&1 || err "phantom not found on PATH. Add ~/.local/bin to your PATH."

    INSTALLED_VERSION=$(uv tool list 2>/dev/null | grep phantom-audio | head -1 | sed 's/phantom-audio //' | sed 's/ .*//' || echo "unknown")
    _ping "install_complete" "$INSTALLED_VERSION"
    ok "Phantom ${INSTALLED_VERSION}"

    # ── Step 4: Configure MCP server (CR-01: check exit code properly) ──
    printf "\n  %sConfiguring%s\n\n" "$BOLD" "$RESET"

    run_with_spinner "MCP server" \
        bash -c 'set -o pipefail; cd "$HOME" && phantom setup --skip-plugin --skip-reaper 2>&1 | grep -v "DeprecationWarning\|AuthlibDeprecation\|scipy.ndimage\|from authlib\|from scipy\|It will be compatible" > /dev/null' \
        || warn "MCP setup had issues — run 'phantom setup' to retry"

    # ── Step 5: Reaper bridge ───────────────────────────────
    REAPER_SCRIPTS=""
    case "$OS" in
        Darwin) REAPER_SCRIPTS="$HOME/Library/Application Support/REAPER/Scripts" ;;
        Linux)  REAPER_SCRIPTS="$HOME/.config/REAPER/Scripts" ;;
    esac

    if [ -d "$REAPER_SCRIPTS" ]; then
        run_with_spinner "Reaper bridge" \
            bash -c 'set -o pipefail; phantom setup-reaper 2>&1 | grep -v "DeprecationWarning\|AuthlibDeprecation\|scipy.ndimage\|from authlib\|from scipy\|It will be compatible" > /dev/null' \
            || warn "Reaper setup had issues — run 'phantom setup-reaper' to retry"
    else
        info "Reaper not detected — skipping bridge"
    fi

    # ── Step 6: Claude Code plugin ──────────────────────────
    if command -v claude >/dev/null 2>&1; then
        run_with_spinner "Claude Code plugin" \
            bash -c 'claude plugin marketplace add https://github.com/fadelabs/phantom.git 2>/dev/null; claude plugin install phantom 2>/dev/null' \
            || warn "Plugin install failed — run: claude plugin install phantom"
    else
        info "Claude Code not found — install from https://claude.ai/code"
    fi

    # ── Success ─────────────────────────────────────────────
    PHANTOM_BIN=$(command -v phantom 2>/dev/null || echo "$HOME/.local/bin/phantom")
    PHANTOM_DIR=$(dirname "$PHANTOM_BIN" 2>/dev/null || echo "$HOME/.local/bin")

    printf "\n"
    printf "  %s%sPhantom is ready.%s\n" "$GREEN" "$BOLD" "$RESET"
    printf "\n"
    printf "  %sGet started:%s\n" "$DIM" "$RESET"
    printf "    %sphantom analyze your-track.wav%s\n" "$CYAN" "$RESET"
    printf "    %sphantom --help%s\n" "$CYAN" "$RESET"

    # PATH warning if needed (WR-01: use $HOME not tilde in export command)
    case ":$PATH:" in
        *":$PHANTOM_DIR:"*) ;;
        *)
            printf "\n"
            printf "  %sAdd to your PATH:%s\n" "$YELLOW" "$RESET"

            SHELL_NAME=$(basename "${SHELL:-sh}" 2>/dev/null || echo "sh")
            case "$SHELL_NAME" in
                zsh)
                    printf "    echo 'export PATH=\"%s:\$PATH\"' >> %s/.zshrc\n" "$PHANTOM_DIR" "\$HOME"
                    printf "    source ~/.zshrc\n"
                    ;;
                bash)
                    printf "    echo 'export PATH=\"%s:\$PATH\"' >> %s/.bashrc\n" "$PHANTOM_DIR" "\$HOME"
                    printf "    source ~/.bashrc\n"
                    ;;
                fish)
                    printf "    fish_add_path %s\n" "$PHANTOM_DIR"
                    ;;
                *)
                    printf "    echo 'export PATH=\"%s:\$PATH\"' >> %s/.profile\n" "$PHANTOM_DIR" "\$HOME"
                    printf "    source ~/.profile\n"
                    ;;
            esac
            ;;
    esac

    printf "\n"
}

main "$@"
