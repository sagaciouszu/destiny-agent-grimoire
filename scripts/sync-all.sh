#!/bin/bash
# Run all documentation/count/sync checks in one pass.
# Usage: bash scripts/sync-all.sh [--check]
#   default: run each sync tool in write mode (updates files)
#   --check: report drift without writing (exit 1 if any fails)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
CHECK=""
for arg in "$@"; do
    case "$arg" in
        --check) CHECK="--check" ;;
        *) echo "usage: $0 [--check]" >&2; exit 2 ;;
    esac
done

FAIL=0
run() {
    echo "=== $1 ==="
    if ! "$@"; then
        FAIL=1
    fi
    echo
}

cd "$ROOT"
run python3 tests/sync-doc-counts.py $CHECK
run python3 tests/sync-readme-meta.py $CHECK
run bash scripts/sync-shared-tests.sh $CHECK

# Export site stats (only if site repo exists and not in check mode)
SITE="$(dirname "$ROOT")/destiny-agent-grimoire-site"
if [ -d "$SITE" ] && [ -z "$CHECK" ]; then
    run python3 scripts/export-site-stats.py --out "$SITE/_data/grimoire.json"
fi

if [ "$FAIL" -ne 0 ]; then
    echo "sync-all: FAILURES detected"
    exit 1
fi
echo "sync-all: all checks passed"