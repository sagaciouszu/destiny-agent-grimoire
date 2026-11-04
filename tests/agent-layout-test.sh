#!/bin/bash
# Agent Layout Test - guards the OpenCode/OpenClaw deployment shape.
# Registry-driven: every ready agent gets one primary entry and one read-only
# consult copy; every other markdown file must be inert. No lore symlink may
# live inside the agents directory.
# Usage: ./tests/agent-layout-test.sh
set -u

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK="$(dirname "$ARCHIVE")"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

REGISTRY="$ARCHIVE/series/agents.json"
if [ -d "$WORK/how-to-drift-for-agents" ] && [ -d "$WORK/eris-morn" ] && [ -d "$WORK/destiny-agent-calus" ]; then
    SRC="$WORK"
else
    SRC="$TMP/src"
    for id in drifter eris; do
        mkdir -p "$SRC/$id/core"
        printf -- '---\nmode: primary\n---\n\n> **Depends On:** %s-core.md, INDEX.md\n\nEntry.\n' "$id" > "$SRC/$id/$id.md"
        printf '# Companion\n' > "$SRC/$id/core/guardrails.md"
        printf '# Readme\n' > "$SRC/$id/README.md"
    done
    REGISTRY="$TMP/agents.json"
    cat > "$REGISTRY" <<'EOF'
{"series":"x","agents":[
 {"id":"drifter","name":"The Drifter","source":"drifter","entry":"drifter.md","summary":"Gambit handler","consult":"Gambit"},
 {"id":"eris","name":"Eris Morn","source":"eris","entry":"eris.md","summary":"Hive expert","consult":"Hive"}
]}
EOF
fi

AGENTS=$(python3 - "$REGISTRY" <<'PY'
import json, sys
for a in json.load(open(sys.argv[1]))['agents']:
    print(a['id'])
PY
)
N=$(printf '%s\n' "$AGENTS" | sed '/^$/d' | wc -l)
DEST="$TMP/agents"
mkdir -p "$DEST"
ln -s "$ARCHIVE" "$DEST/lore"

NO_RELOAD=1 AGENT_REPOS_DIR="$SRC" OPENCODE_AGENTS="$DEST" SERIES_MANIFEST="$REGISTRY" \
    bash "$ARCHIVE/scripts/sync-live-agents.sh" >/dev/null 2>&1 || {
    echo "FAIL: sync-live-agents.sh exited non-zero"
    exit 1
}

PASS=0; FAIL=0
check() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; PASS=$((PASS+1)); else echo "  ✗ $1"; FAIL=$((FAIL+1)); fi; }

check "lore symlink removed from agents root" '[ -z "$(find "$DEST" -type l -name lore -print -quit)" ]'
check "no lore directory left behind" '[ ! -e "$DEST/lore" ]'
check "series registry is installed" '[ -f "$(dirname "$DEST")/series/agents.json" ]'

for id in $AGENTS; do
    check "$id entry is active" '! grep -q "^disabled: true$" "'"$DEST/$id.md"'"'
    check "$id consult is active" '! grep -q "^disabled: true$" "'"$DEST/$id-consult.md"'"'
    check "$id primary is primary-only" 'grep -q "^mode: primary$" "'"$DEST/$id.md"'"'
    check "$id consult is a subagent" 'grep -q "^mode: subagent$" "'"$DEST/$id-consult.md"'"'
    check "$id consult denies edit, shell and delegation" \
        'grep -q "action: edit" "'"$DEST/$id-consult.md"'" && grep -q "action: shell" "'"$DEST/$id-consult.md"'" && grep -q "action: subagent" "'"$DEST/$id-consult.md"'"'
    check "$id entry references its own directory" 'grep -q "'"$id"'/INDEX.md" "'"$DEST/$id.md"'"'
    check "$id entry carries the series block" 'grep -q "series:begin" "'"$DEST/$id.md"'"'
    for peer in $AGENTS; do
        [ "$peer" = "$id" ] && continue
        check "$id entry denies $peer directory" 'grep -qF "agents/'"$peer"'/**" "'"$DEST/$id.md"'"'
        check "$id entry lists $peer consult" 'grep -q "'"$peer"'-consult" "'"$DEST/$id.md"'"'
    done
done

ACTIVE=$((N * 2))
check "exactly $ACTIVE active markdown files" \
    '[ "$(grep -rL --include="*.md" "^disabled: true$" "$DEST" | wc -l)" -eq '"$ACTIVE"' ]'
TOTAL=$(find "$DEST" -name "*.md" | wc -l)
check "every companion file is disabled" \
    '[ "$(grep -rl --include="*.md" "^disabled: true$" "$DEST" | wc -l)" -eq "$((TOTAL - ACTIVE))" ]'

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
