#!/bin/bash
# Agent connection test: every local agent must resolve the canonical database
# and the current query surface (character, verify, lore, seal).
# Skips agents that are not present.
set -u

GRIMOIRE="${GRIMOIRE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK="$(dirname "$GRIMOIRE")"
PRIMARY_DB="$GRIMOIRE/db/grimoire.db"
PASS=0; FAIL=0
ok()  { echo "  ✓ $1"; PASS=$((PASS+1)); }
bad() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }

if [ ! -f "$PRIMARY_DB" ]; then
    echo "SKIP: primary database missing"
    exit 0
fi
PRIMARY_SUM=$(sha256sum "$PRIMARY_DB" | cut -d' ' -f1)

check_agent() {
    local dir="$1" speaker="$2"
    local root="$WORK/$dir"
    if [ ! -d "$root" ]; then
        echo "  - $dir not present, skipped"
        return
    fi
    if [ ! -f "$root/lore/db/grimoire.db" ]; then
        bad "$dir: lore database missing"
        return
    fi
    local sum
    sum=$(sha256sum "$root/lore/db/grimoire.db" | cut -d' ' -f1)
    if [ "$sum" = "$PRIMARY_SUM" ]; then
        ok "$dir: database matches canonical"
    else
        bad "$dir: database checksum differs"
    fi
    if python3 "$root/lore/db/query.py" stats >/dev/null 2>&1; then
        ok "$dir: query interface"
    else
        bad "$dir: query interface failed"
    fi
    if python3 "$root/lore/db/query.py" character-info "$speaker" >/dev/null 2>&1; then
        ok "$dir: speaker resolved ($speaker)"
    else
        bad "$dir: speaker not resolved ($speaker)"
    fi
    if python3 "$root/lore/db/query.py" lore "Gate Lord's Eye" >/dev/null 2>&1; then
        ok "$dir: lore lookup"
    else
        bad "$dir: lore lookup failed"
    fi
    if python3 "$root/lore/db/query.py" seal Conqueror >/dev/null 2>&1; then
        ok "$dir: seal lookup"
    else
        bad "$dir: seal lookup failed"
    fi
    if [ -x "$root/lore/mcp-server/run.sh" ]; then
        ok "$dir: MCP launcher present"
    else
        bad "$dir: MCP launcher missing"
    fi
}

echo "=== AGENT CONNECTION TEST ==="
check_agent how-to-drift-for-agents Drifter
check_agent eris-morn Eris
check_agent destiny-agent-calus Calus

REG="$GRIMOIRE/series/agents.json"
if [ -f "$REG" ] && grep -q '"drifter"' "$REG" && grep -q '"eris"' "$REG"; then
    ok "series registry has Drifter and Eris"
else
    bad "series registry incomplete"
fi

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
