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
FILES="memory.py memory-test.py run-suites.sh shared-helpers-test.sh suite-manifest-test.py connection-test.sh"
CANON="$HERE/../tests/agent-helpers"
DESTS=""
for r in destiny-agent-calus destiny-agent-drifter destiny-agent-eris-morn \
         destiny-agent-ghost destiny-agent-mara-sov destiny-agent-zavala; do
    DESTS="$DESTS $WORK/$r"
done
DESTS="$DESTS $WORK/destiny-agent-template/template"
PASS=0; FAIL=0; UPDATED=0
for f in $FILES; do
    src="$CANON/$f"
    [ -f "$src" ] || { echo "  ✗ canonical missing: tests/agent-helpers/$f"; FAIL=$((FAIL+1)); continue; }
    case "$f" in
        memory.py) rel="memory.py" ;;
        *) rel="tests/$f" ;;
    esac
    for d in $DESTS; do
        dst="$d/$rel"
        if [ ! -f "$dst" ]; then
            echo "  ✗ missing distribution copy: $dst"
            FAIL=$((FAIL+1)); continue
        fi
        if cmp -s "$src" "$dst"; then
            PASS=$((PASS+1))
        elif [ "$CHECK" = "1" ]; then
            echo "  ✗ drift: $dst"
            FAIL=$((FAIL+1))
        else
            cp -p "$src" "$dst"
            echo "  ~ synced: $dst"
            UPDATED=$((UPDATED+1))
        fi
    done
done
if [ "$CHECK" = "1" ]; then
    echo "shared-tests: $PASS identical, $FAIL drifted"
else
    echo "shared-tests: $PASS identical, $UPDATED updated, $FAIL missing"
fi
[ "$FAIL" -eq 0 ]
