#!/usr/bin/env bash
# scripts/check-pii.sh -- block PII and absolute paths in staged files
set -euo pipefail

# Check staged files only (not all tracked files)
STAGED=$(git diff --cached --name-only --diff-filter=ACM | \
  grep -E '\.(py|md|toml|json|yml|yaml|cfg|txt|rst|sh)$' | \
  grep -v '^LICENSE$' | \
  grep -v '^README.md$' | \
  grep -v '^scripts/pre-push$' | \
  grep -v '^scripts/check-pii.sh$' | \
  grep -v '^\.github/workflows/security-scan.yml$' || true)

if [ -z "$STAGED" ]; then
  exit 0
fi

# PII patterns (same as pre-push hook for consistency)
PII_HITS=$(echo "$STAGED" | xargs grep -inE "saenz|leesaenz|@gmail\.com" 2>/dev/null || true)
if [ -n "$PII_HITS" ]; then
  echo "BLOCKED: Personal information detected in staged files:"
  echo "$PII_HITS"
  echo ""
  echo "Remove PII before committing. See CLAUDE.md privacy rules."
  exit 1
fi

# Absolute path patterns
PATH_HITS=$(echo "$STAGED" | xargs grep -nE "/Users/lee/|/home/[a-z]+/|C:\\\\Users\\\\" 2>/dev/null | \
  grep -v '\.planning/' | grep -v '\.claude/' || true)
if [ -n "$PATH_HITS" ]; then
  echo "BLOCKED: Absolute paths detected in staged files:"
  echo "$PATH_HITS"
  echo ""
  echo "Replace absolute paths with relative paths or environment variables."
  exit 1
fi

exit 0
