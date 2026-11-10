#!/bin/bash
# shared-helpers-test.sh: byte-compare the distribution copies of the shared
# agent helpers with their canonical copies in the grimoire archive
# (lore/tests/agent-helpers/). These files are intentionally identical in every
# agent repo so an offline agent has the same contract; a difference is drift.
# Input: none (paths derive from this script's location).
# Output: one PASS/FAIL line per helper.
# Exit: 0 when every helper matches; 1 if any differs or a canonical copy is
# missing (a missing canonical copy is a defect, not a skip).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
CANON="$HERE/../lore/tests/agent-helpers"
PASS=0; FAIL=0

check() {
    local local_rel="$1" canon_name="$2"
    local local_path="$REPO/$local_rel"
    if [ ! -f "$local_path" ]; then
        echo "  FAIL $local_rel (missing from $(basename "$REPO"))"
        FAIL=$((FAIL+1))
        return
    fi
    if [ ! -f "$CANON/$canon_name" ]; then
        echo "  FAIL $local_rel (no canonical copy at lore/tests/agent-helpers/$canon_name)"
        FAIL=$((FAIL+1))
        return
    fi
    if cmp -s "$local_path" "$CANON/$canon_name"; then
        echo "  PASS $local_rel"
        PASS=$((PASS+1))
    else
        echo "  FAIL $local_rel (differs from lore/tests/agent-helpers/$canon_name)"
        FAIL=$((FAIL+1))
    fi
}

echo "=== SHARED HELPERS TEST ==="
for helper in memory-test.py run-suites.sh suite-manifest-test.py; do
    check "tests/$helper" "$helper"
done
check "memory.py" "memory.py"
check "tests/shared-helpers-test.sh" "shared-helpers-test.sh"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
