#!/usr/bin/env bash
# scripts/check-large-binaries.sh -- block large audio files
set -euo pipefail

MAX_SIZE=$((1024 * 1024))  # 1MB
AUDIO_EXTS="wav|mp3|flac|aiff|ogg|m4a"
EXEMPT="examples/demo.wav"

STAGED=$(git diff --cached --name-only --diff-filter=ACM | \
  grep -iE "\.($AUDIO_EXTS)$" || true)

if [ -z "$STAGED" ]; then
  exit 0
fi

BLOCKED=""
while IFS= read -r file; do
  # Skip exempt files
  if [ "$file" = "$EXEMPT" ]; then
    continue
  fi
  # Check file size of staged version
  SIZE=$(git cat-file -s ":$file" 2>/dev/null || echo "0")
  if [ "$SIZE" -gt "$MAX_SIZE" ]; then
    BLOCKED="${BLOCKED}\n  $file ($(( SIZE / 1024 ))KB)"
  fi
done <<< "$STAGED"

if [ -n "$BLOCKED" ]; then
  echo "BLOCKED: Large audio files detected (>1MB):"
  echo -e "$BLOCKED"
  echo ""
  echo "Audio files belong outside the repo. Use PHANTOM_AUDIO_DIR instead."
  echo "Exempt: $EXEMPT"
  exit 1
fi

exit 0
