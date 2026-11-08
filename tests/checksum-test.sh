#!/bin/bash
# Checkum tests for onboarding: verified download, mismatch, missing sums.
# Uses local file:// URLs and a throwaway agent clone; no network.
set -u

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORK="$(dirname "$ARCHIVE")"
if [ ! -d "$WORK/destiny-agent-drifter" ]; then
    echo "SKIP: destiny-agent-drifter not present"
    exit 0
fi
TMP="$(mktemp -d /tmp/opencode/checksum-test.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
check() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; PASS=$((PASS+1)); else echo "  ✗ $1"; FAIL=$((FAIL+1)); fi; }

[ -f "$ARCHIVE/db/grimoire.db" ] || { echo "FATAL: build the database first"; exit 1; }
DB="$ARCHIVE/db/grimoire.db"
DIGEST=$(sha256sum "$DB" | awk '{print $1}')

mkdir -p "$TMP/good" "$TMP/bad"
cp --reflink=auto "$DB" "$TMP/good/grimoire.db"
echo "$DIGEST  grimoire.db" > "$TMP/good/SHA256SUMS"
cp --reflink=auto "$DB" "$TMP/bad/grimoire.db"
echo "0000000000000000000000000000000000000000000000000000000000000000  grimoire.db" > "$TMP/bad/SHA256SUMS"

# A fake archive whose migration always fails, so a rejected download cannot hide
# behind a successful local build.
mkdir -p "$TMP/fake/db"; cd "$TMP/fake"
git init -q; printf 'import sys\nsys.exit(1)\n' > db/migrate.py
git add -A >/dev/null 2>&1; git -c user.email=t@t -c user.name=t commit -qm init >/dev/null 2>&1

run_setup() {
    local dir="$1" dburl="$2" sumsurl="$3" loreurl="$4"
    git clone -q "$WORK/destiny-agent-drifter" "$dir" 2>/dev/null
    ( cd "$dir" && LORE_URL="$loreurl" RELEASE_DB_URL="$dburl" RELEASE_SUMS_URL="$sumsurl" \
        BOOTSTRAP=1 ./setup.sh --no-mcp </dev/null 2>&1 )
}

echo "checksum test"
out=$(run_setup "$TMP/ok" "file://$TMP/good/grimoire.db" "file://$TMP/good/SHA256SUMS" "$ARCHIVE")
check "verified download accepted" "echo \"\$out\" | grep -q 'downloaded and verified'"
check "installed database matches checksum" "[ \"\$(sha256sum '$TMP/ok/lore/db/grimoire.db' | awk '{print \$1}')\" = '$DIGEST' ]"

out=$(run_setup "$TMP/no-sum" "file://$TMP/good/grimoire.db" "file://$TMP/nonexistent/SHA256SUMS" "$ARCHIVE")
check "missing checksum warns but installs" "echo \"\$out\" | grep -q 'cannot be verified' && [ -f '$TMP/no-sum/lore/db/grimoire.db' ]"

out=$(run_setup "$TMP/reject" "file://$TMP/bad/grimoire.db" "file://$TMP/bad/SHA256SUMS" "$TMP/fake")
check "mismatch is rejected" "echo \"\$out\" | grep -q 'Checksum mismatch'"
check "mismatch leaves no database file" "[ ! -f '$TMP/reject/lore/db/grimoire.db' ]"
check "mismatch leaves no partial file" "[ ! -f '$TMP/reject/lore/db/grimoire.db.part' ]"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
