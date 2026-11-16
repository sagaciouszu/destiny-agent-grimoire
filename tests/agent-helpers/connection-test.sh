#!/bin/bash
# Connection test for a generated agent: the workspace must reach the canonical
# grimoire and the current query/lore/seal surface.
# Usage: bash tests/connection-test.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
LORE="${LORE:-$REPO/lore}"
WORKSPACE="${WORKSPACE:-$REPO}"
PASS=0; FAIL=0
check() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; PASS=$((PASS+1)); else echo "  ✗ $1"; FAIL=$((FAIL+1)); fi; }

SPEAKER=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('speaker') or '')" "$REPO/persona.json" 2>/dev/null)
STATUS=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('status') or '')" "$REPO/persona.json" 2>/dev/null)

check "lore directory" "[ -d '$LORE' ]"
check "database present" "[ -f '$LORE/db/grimoire.db' ]"
check "query interface" "python3 '$LORE/db/query.py' stats"
if [ "$STATUS" != "skeleton" ] && [ -n "$SPEAKER" ]; then
    check "speaker declared" "[ -n '$SPEAKER' ]"
    check "speaker in canon" "python3 '$LORE/db/query.py' character-info '$SPEAKER'"
    check "canon line count fresh" "python3 '$REPO/tests/persona-freshness.py' '$REPO/persona.json' '$LORE/db/grimoire.db'"
else
    echo "  - speaker not sourced yet, skipped"
fi
check "lore lookup" "python3 '$LORE/db/query.py' lore \"Gate Lord's Eye\""
check "seal lookup" "python3 '$LORE/db/query.py' seal Conqueror"
check "MCP launcher" "[ -x '$LORE/mcp-server/run.sh' ]"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
