#!/bin/bash
# Push canonical shared agent helpers to every agent repo and the template.
# Usage: bash scripts/sync-shared-tests.sh [--check]
#   default: copy each canonical file over the distribution copies, print drift
#   --check: report drift without writing (exit 1 if any differs)
# Canonical home is lore/tests/agent-helpers/ (see its README.md); the
# per-repo parity gate is tests/shared-helpers-test.sh.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(dirname "$(dirname "$HERE")")"
CHECK=0
for arg in "$@"; do
    case "$arg" in
        --check) CHECK=1 ;;
        *) echo "usage: $0 [--check]" >&2; exit 2 ;;
    esac
done
CANON="$HERE/../tests/agent-helpers"
DESTS=""
while IFS= read -r src; do
    [ -n "$src" ] && DESTS="$DESTS $WORK/$src"
done < <(python3 -c "import json,sys; [print(a['source']) for a in json.load(open(sys.argv[1]))['agents'] if a.get('source')]" "$HERE/../series/agents.json")
DESTS="$DESTS $WORK/destiny-agent-template/template"
PASS=0; FAIL=0; UPDATED=0

# Map: canonical filename -> relative path in agent repo
sync_one() {
    local f="$1" rel="$2"
    local src="$CANON/$f"
    [ -f "$src" ] || { echo "  x canonical missing: tests/agent-helpers/$f"; FAIL=$((FAIL+1)); return; }
    for d in $DESTS; do
        dst="$d/$rel"
        if [ ! -f "$dst" ]; then
            echo "  x missing distribution copy: $dst"
            FAIL=$((FAIL+1)); continue
        fi
        if cmp -s "$src" "$dst"; then
            PASS=$((PASS+1))
        elif [ "$CHECK" = "1" ]; then
            echo "  x drift: $dst"
            FAIL=$((FAIL+1))
        else
            cp -p "$src" "$dst"
            echo "  ~ synced: $dst"
            UPDATED=$((UPDATED+1))
        fi
    done
}

# Original 6 files
for f in memory.py memory-test.py run-suites.sh shared-helpers-test.sh suite-manifest-test.py connection-test.sh; do
    case "$f" in
        memory.py) rel="memory.py" ;;
        *) rel="tests/$f" ;;
    esac
    sync_one "$f" "$rel"
done

# Additional 5 byte-identical files
sync_one ".gitignore" ".gitignore"
sync_one "setup.sh" "setup.sh"
sync_one "ci.yml" ".github/workflows/ci.yml"
sync_one "persona-freshness.py" "tests/persona-freshness.py"
sync_one "runtime-leak-guard.py" "tests/runtime-leak-guard.py"

if [ "$CHECK" = "1" ]; then
    echo "shared-tests: $PASS identical, $FAIL drifted"
else
    echo "shared-tests: $PASS identical, $UPDATED updated, $FAIL missing"
fi
[ "$FAIL" -eq 0 ]