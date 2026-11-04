#!/bin/bash
# Agent connection test: every registry agent present locally must resolve the
# canonical database and the current query/lore/seal surface.
set -u

GRIMOIRE="${GRIMOIRE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK="$(dirname "$GRIMOIRE")"
REG="$GRIMOIRE/series/agents.json"
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
    local dir="$1"
    local root="$WORK/$dir"
    if [ ! -d "$root" ]; then
        echo "  - $dir not present, skipped"
        return
    fi
    local speaker status
    read -r speaker status < <(python3 - "$root/persona.json" <<'PY'
import json, sys
try:
    p = json.load(open(sys.argv[1], encoding='utf-8'))
    print(p.get('speaker') or '-', p.get('status') or 'skeleton')
except Exception:
    print('- skeleton')
PY
)
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
    if [ "$status" != "skeleton" ] && [ "$speaker" != "-" ]; then
        if python3 "$root/lore/db/query.py" character-info "$speaker" >/dev/null 2>&1; then
            ok "$dir: speaker resolved ($speaker)"
        else
            bad "$dir: speaker not resolved ($speaker)"
        fi
        if python3 "$GRIMOIRE/tests/persona-freshness.py" "$root/persona.json" "$root/lore/db/grimoire.db" >/dev/null 2>&1; then
            ok "$dir: canon line count fresh"
        else
            bad "$dir: canon line count stale"
        fi
    else
        echo "  - $dir: speaker not sourced yet, skipped"
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
while IFS=$'\t' read -r id source entry; do
    check_agent "$source"
done < <(python3 - "$REG" <<'PY'
import json, sys
for a in json.load(open(sys.argv[1], encoding='utf-8'))['agents']:
    print(f"{a['id']}\t{a['source']}\t{a['entry']}")
PY
)

if python3 - "$REG" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
ids = [a['id'] for a in d['agents']]
assert len(ids) == len(set(ids))
assert all(a.get('source') and a.get('entry') for a in d['agents'])
PY
then
    ok "series registry is valid"
else
    bad "series registry is invalid"
fi

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
