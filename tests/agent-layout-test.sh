#!/bin/bash
# Agent Layout Test - guards the OpenCode/OpenClaw deployment shape.
# Asserts that only the two entry agents are active, that no lore symlink is
# left inside the agents directory, and that every companion file is inert.
# Usage: ./tests/agent-layout-test.sh
set -u

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK="$(dirname "$ARCHIVE")"
DRIFTER="$WORK/how-to-drift-for-agents"
ERIS="$WORK/eris-morn"

if [ ! -d "$DRIFTER" ] || [ ! -d "$ERIS" ]; then
    echo "SKIP: agent repos not present (single-repo checkout)"
    exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DEST="$TMP/agents"
mkdir -p "$DEST"
# Simulate the historical failure: a lore symlink inside the agents root.
ln -s "$ARCHIVE" "$DEST/lore"

NO_RELOAD=1 OPENCODE_AGENTS="$DEST" bash "$ARCHIVE/scripts/sync-live-agents.sh" >/dev/null 2>&1 || {
    echo "FAIL: sync-live-agents.sh exited non-zero"
    exit 1
}

PASS=0; FAIL=0
check() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; PASS=$((PASS+1)); else echo "  ✗ $1"; FAIL=$((FAIL+1)); fi; }

check "lore symlink removed from agents root" '[ -z "$(find "$DEST" -type l -name lore -print -quit)" ]'
check "no lore directory left behind" '[ ! -e "$DEST/lore" ]'
check "entry agents stay active" \
    '! grep -q "^disabled: true$" "$DEST/drifter.md" && ! grep -q "^disabled: true$" "$DEST/eris/eris.md"'
check "only two markdown files lack the disabled marker" \
    '[ "$(grep -rL --include="*.md" "^disabled: true$" "$DEST" | wc -l)" -eq 2 ]'
check "every companion file is disabled" \
    '[ "$(grep -rl --include="*.md" "^disabled: true$" "$DEST" | wc -l)" -eq "$(( $(find "$DEST" -name "*.md" | wc -l) - 2 ))" ]'

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
