#!/usr/bin/env bash
# scripts/check-ai-session-links.sh -- block AI session links in commit messages
# Runs at the commit-msg stage: $1 is the commit message file.
# Provider-agnostic: catches session trailers (Claude-Session:, Codex-Session-Id:,
# ...) and session/conversation/share URLs from any AI assistant.
# Co-Authored-By: trailers and plain prose mentions of "session" (common in this
# repo: Reaper sessions, session-architect) are allowed.
set -euo pipefail

MSG_FILE="$1"

# Keep only the real message: cut at the scissors line (git commit --verbose
# appends the staged diff below it), then drop comment lines.
MSG=$(sed -n '/^# ------------------------ >8 ------------------------$/q;p' "$MSG_FILE" | grep -v '^#' || true)

# 1. Trailer-shaped lines whose key contains "session" AND whose value is a URL
#    or a single opaque id -- Claude-Session:, Session-Id:, AI-Session-URL:, etc.
#    Prose like "session-architect: fix typo in skill" does not match.
TRAILER_HITS=$(echo "$MSG" | grep -inE '^[a-z0-9-]*session[a-z0-9-]*:[[:space:]]*(https?://|[a-z0-9_/+=-]{12,}[[:space:]]*$)' || true)

# 2. Session/conversation/share URLs on known AI assistant hosts.
#    claude.ai/c/<id> and claude.ai/code/<id> are listed explicitly: the
#    (session|share|chat) alternation never matched them, because the opaque id
#    sits where those words would be. Those two are the shapes Claude Code and
#    claude.ai actually hand out, so the canonical case was the one getting
#    through as a bare URL. Only the trailer rule above caught it, and only when
#    it carried a Claude-Session: key.
URL_HITS=$(echo "$MSG" | grep -inE 'claude\.(ai|com)/[a-z/]*(session|share|chat)|claude\.(ai|com)/(c|code)/[A-Za-z0-9][A-Za-z0-9_-]{7,}|chat\.openai\.com/(share|c)/|chatgpt\.com/(share|c|codex|g)/|gemini\.google\.com/(share|app)/|g\.co/gemini|copilot\.microsoft\.com/(shares|chats)|github\.com/copilot/(share|c)|cursor\.(com|sh)/(share|s|agents|composer)|app\.devin\.ai/session|windsurf\.com/(share|s)/|grok\.com/(share|c)/|poe\.com/s/|perplexity\.ai/search' || true)

# 3. Any URL carrying an opaque session/conversation/thread id -- catches
#    assistants not on the list above.
GENERIC_HITS=$(echo "$MSG" | grep -inE 'https?://[^[:space:]]*/(session|conversation|thread)s?[_/-][a-z0-9_-]{8,}' || true)

HITS=$(printf '%s\n%s\n%s\n' "$TRAILER_HITS" "$URL_HITS" "$GENERIC_HITS" | grep -v '^$' | sort -u || true)

if [ -n "$HITS" ]; then
  echo "BLOCKED: AI session link or session trailer in the commit message:"
  echo "$HITS"
  echo ""
  echo "Session links must never land in this public repo. Remove the URL or"
  echo "trailer and commit again. Co-Authored-By: trailers are fine."
  exit 1
fi

exit 0
