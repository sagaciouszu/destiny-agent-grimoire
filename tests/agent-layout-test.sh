#!/bin/bash
# Agent Layout Test - guards the OpenCode/OpenClaw deployment shape.
# Asserts that only the two entry agents are active, that no lore symlink is
# left inside the agents directory, and that every companion file is inert.
# Usage: ./tests/agent-layout-test.sh
set -u

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK="$(dirname "$ARCHIVE")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

if [ -d "$WORK/how-to-drift-for-agents" ] && [ -d "$WORK/eris-morn" ]; then
    SRC="$WORK"
else
    SRC="$TMP/src"
    mkdir -p "$SRC/how-to-drift-for-agents/core" "$SRC/eris-morn/core"
    printf -- '---\nmode: primary\n---\n\n> **Depends On:** drifter-core.md, INDEX.md\n\nEntry.\n' > "$SRC/how-to-drift-for-agents/drifter.md"
    printf '# Companion\n' > "$SRC/how-to-drift-for-agents/core/guardrails.md"
    printf '# Readme\n' > "$SRC/how-to-drift-for-agents/README.md"
    printf '# Agent\n' > "$SRC/how-to-drift-for-agents/AGENTS.md"
    printf -- '---\nmode: primary\n---\n\n> **Depends On:** eris-core.md, INDEX.md\n\nEntry.\n' > "$SRC/eris-morn/eris.md"
    printf '# Companion\n' > "$SRC/eris-morn/core/guardrails.md"
    printf '# Readme\n' > "$SRC/eris-morn/README.md"
    printf '# Agent\n' > "$SRC/eris-morn/AGENTS.md"
fi

DEST="$TMP/agents"
mkdir -p "$DEST"
# Simulate the historical failure: a lore symlink inside the agents root.
ln -s "$ARCHIVE" "$DEST/lore"

NO_RELOAD=1 AGENT_REPOS_DIR="$SRC" OPENCODE_AGENTS="$DEST" \
    bash "$ARCHIVE/scripts/sync-live-agents.sh" >/dev/null 2>&1 || {
    echo "FAIL: sync-live-agents.sh exited non-zero"
    exit 1
}

PASS=0; FAIL=0
check() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; PASS=$((PASS+1)); else echo "  ✗ $1"; FAIL=$((FAIL+1)); fi; }

check "lore symlink removed from agents root" '[ -z "$(find "$DEST" -type l -name lore -print -quit)" ]'
check "no lore directory left behind" '[ ! -e "$DEST/lore" ]'
check "entry and consult agents stay active" \
    '! grep -q "^disabled: true$" "$DEST/drifter.md" && ! grep -q "^disabled: true$" "$DEST/eris.md" && ! grep -q "^disabled: true$" "$DEST/drifter-consult.md" && ! grep -q "^disabled: true$" "$DEST/eris-consult.md"'
check "primaries are primary-only" 'grep -q "^mode: primary$" "$DEST/drifter.md" && grep -q "^mode: primary$" "$DEST/eris.md"'
check "consult copies are read-only subagents" 'grep -q "^mode: subagent$" "$DEST/drifter-consult.md" && grep -q "action: edit" "$DEST/drifter-consult.md" && grep -q "action: shell" "$DEST/drifter-consult.md" && grep -q "action: subagent" "$DEST/drifter-consult.md"'
check "series registry is installed" '[ -f "$(dirname "$DEST")/series/agents.json" ]'
check "both entries carry the series block" 'grep -q "series:begin" "$DEST/drifter.md" && grep -q "series:begin" "$DEST/eris.md"'
check "entries point at consult peers" 'grep -q "Hive expert" "$DEST/drifter.md" && grep -q "Gambit handler" "$DEST/eris.md"'
check "peer directories are read-denied" 'grep -qF "agents/eris/**" "$DEST/drifter.md" && grep -qF "agents/drifter/**" "$DEST/eris.md"'
check "eris entry references its own directory" 'grep -q "eris/INDEX.md" "$DEST/eris.md"'
check "drifter entry references its own directory" 'grep -q "drifter/INDEX.md" "$DEST/drifter.md"'
check "only four markdown files lack the disabled marker" \
    '[ "$(grep -rL --include="*.md" "^disabled: true$" "$DEST" | wc -l)" -eq 4 ]'
check "every companion file is disabled" \
    '[ "$(grep -rl --include="*.md" "^disabled: true$" "$DEST" | wc -l)" -eq "$(( $(find "$DEST" -name "*.md" | wc -l) - 4 ))" ]'

OC="$TMP/openclaw"
if OPENCLAW_ROOT="$OC" NO_RELOAD=1 AGENT_REPOS_DIR="$SRC" \
    bash "$ARCHIVE/scripts/sync-live-agents.sh" --openclaw >/dev/null 2>&1; then
    check "OpenClaw workspace per agent" '[ -d "$OC/workspace-drifter" ] && [ -d "$OC/workspace-eris" ]'
    check "OpenClaw series block and registry" 'grep -q "series:begin" "$OC/workspace-drifter/AGENTS.md" && [ -f "$OC/workspace-eris/series/agents.json" ]'
else
    echo "  ✗ OpenClaw sync"; FAIL=$((FAIL+1))
fi

BAD="$TMP/bad-registry.json"
printf '%s' '{"series":"x","agents":[{"id":"evil","name":"Evil","source":"how-to-drift-for-agents","entry":"../../evil.md"}]}' > "$BAD"
if SERIES_MANIFEST="$BAD" AGENT_REPOS_DIR="$SRC" OPENCODE_AGENTS="$DEST" NO_RELOAD=1 \
    bash "$ARCHIVE/scripts/sync-live-agents.sh" >/dev/null 2>&1; then
    echo "  ✗ registry rejects path traversal"; FAIL=$((FAIL+1))
else
    echo "  ✓ registry rejects path traversal"; PASS=$((PASS+1))
fi

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
