#!/bin/bash
# Onboarding smoke test: every local agent, symlink and clone modes, fully offline.
# Uses the local checkout and its built database; no network, no releases.
# Usage: bash tests/onboarding-smoke.sh
set -u

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK="$(dirname "$ARCHIVE")"
SANDBOX="${TMPDIR:-/tmp/opencode}/onboarding-smoke.$$"
PASS=0; FAIL=0

[ -f "$ARCHIVE/db/grimoire.db" ] || {
    echo "FATAL: database missing at $ARCHIVE/db/grimoire.db"
    echo "       run: python3 db/migrate.py"
    exit 1
}

mkdir -p "$SANDBOX"
trap 'rm -rf "$SANDBOX"' EXIT

check() {
    if eval "$2" >/dev/null 2>&1; then
        echo "  ✓ $1"; PASS=$((PASS+1))
    else
        echo "  ✗ $1"; FAIL=$((FAIL+1))
    fi
}

smoke() {
    local repo="$1" audit="$2" suites="$3" mode="$4"
    local dir="$SANDBOX/$repo-$mode"
    local src="$WORK/$repo"

    echo "=== $repo ($mode mode)"
    check "clone succeeds" "git clone -q '$src' '$dir'"

    if [ "$mode" = "symlink" ]; then
        check "setup links the archive" "cd '$dir' && ./setup.sh '$ARCHIVE' >/dev/null 2>&1"
        check "lore is a symlink" "[ -L '$dir/lore' ]"
    else
        check "archive cloned into lore/" "git clone -q '$ARCHIVE' '$dir/lore'"
        check "database present" "cp '$ARCHIVE/db/grimoire.db' '$dir/lore/db/grimoire.db'"
        check "setup accepts an existing clone" "cd '$dir' && ./setup.sh >/dev/null 2>&1"
        check "lore is a real directory" "[ -d '$dir/lore' ] && [ ! -L '$dir/lore' ]"
    fi

    check "audit $suites/$suites" "cd '$dir' && bash '$audit' 2>&1 | grep -q 'SCORECARD: $suites / $suites SUITES PASSED'"
    check "working tree stays clean" "[ -z \"\$(git -C '$dir' status --porcelain)\" ]"
}

smoke how-to-drift-for-agents tests/master-audit.sh 20 symlink
smoke how-to-drift-for-agents tests/master-audit.sh 20 clone
smoke eris-morn tests/master-audit.sh 15 symlink
smoke eris-morn tests/master-audit.sh 15 clone
smoke destiny-agent-calus tests/master-audit.sh 15 symlink
smoke destiny-agent-calus tests/master-audit.sh 15 clone

echo ""
echo "ONBOARDING SMOKE: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
