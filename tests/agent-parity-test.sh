#!/bin/bash
# Cross-agent parity: every present agent must expose the same shared
# capabilities even when it has extra persona-specific suites.
set -u
GRIMOIRE="${GRIMOIRE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK="$(dirname "$GRIMOIRE")"
PASS=0; FAIL=0
ok()  { echo "  ✓ $1"; PASS=$((PASS+1)); }
bad() { echo "  ✗ $1"; FAIL=$((FAIL+1)); }

check_agent() {
    local repo="$1"
    local root="$WORK/$repo"
    if [ ! -d "$root" ]; then
        echo "  - $repo not present, skipped"
        return
    fi
    for rel in memory.py core/multi-user.md USER.template.md \
               tests/connection-test.sh tests/memory-test.py tests/persona-freshness.py \
               reference/cross-reference.md reference/speech-pattern-analysis.md; do
        if [ -e "$root/$rel" ]; then ok "$repo: $rel"; else bad "$repo: missing $rel"; fi
    done
    if python3 - "$root/persona.json" <<'PY'
import json, sys
p = json.load(open(sys.argv[1], encoding='utf-8'))
missing = [k for k in ('canon_lines','canon_variant_lines','activities','seasons',
                       'source_tiers','grimoire_version','manifest_version','sourced_at')
           if k not in p]
raise SystemExit(1 if missing else 0)
PY
    then ok "$repo: persona metrics"; else bad "$repo: incomplete persona metrics"; fi
    if grep -q -- '--class' "$root/AGENTS.md" && grep -q 'Canon discovery' "$root/AGENTS.md"; then
        ok "$repo: class-aware discovery"
    else
        bad "$repo: class-aware discovery missing"
    fi
    if grep -q 'activity' "$root/TOOLS.md" && grep -q 'lore' "$root/TOOLS.md" && grep -q 'seal' "$root/TOOLS.md"; then
        ok "$repo: taxonomy/lore/seal tools"
    else
        bad "$repo: tool surface incomplete"
    fi
    if (cd "$root" && bash tests/master-audit.sh 2>&1 | grep -q '0 failed'); then
        ok "$repo: master audit"
    else
        bad "$repo: master audit"
    fi
}

echo "=== AGENT PARITY TEST ==="
REG="$GRIMOIRE/series/agents.json"
while IFS=$'\t' read -r id source; do
    check_agent "$source"
done < <(python3 - "$REG" <<'PY'
import json, sys
for a in json.load(open(sys.argv[1], encoding='utf-8'))['agents']:
    print(f"{a['id']}\t{a['source']}")
PY
)
echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
