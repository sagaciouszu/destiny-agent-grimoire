#!/bin/bash
# Sync docs/wiki/ into the GitHub wiki clone and verify it.
#
# Usage:
#   scripts/sync-wiki.sh            # copy docs/wiki/*.md into the wiki clone + verify
#   scripts/sync-wiki.sh --check    # verify only: fail on drift or corruption
#   scripts/sync-wiki.sh --push     # copy, then commit and push the wiki
#
# Environment:
#   WIKI_DIR   wiki checkout (default: sibling destiny-agent-grimoire.wiki;
#              cloned automatically on first run)
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$HERE/docs/wiki"
WIKI_DIR="${WIKI_DIR:-$HERE/../destiny-agent-grimoire.wiki}"
WIKI_URL="https://github.com/sagaciouszu/destiny-agent-grimoire.wiki.git"
MODE="sync"
for arg in "$@"; do
    case "$arg" in
        --check) MODE="check" ;;
        --push)  MODE="push" ;;
        *) echo "usage: $0 [--check|--push]" >&2; exit 2 ;;
    esac
done

[ -d "$SRC" ] || { echo "FATAL: missing $SRC" >&2; exit 1; }

if [ ! -d "$WIKI_DIR/.git" ]; then
    [ "$MODE" = "check" ] && { echo "FATAL: wiki clone missing: $WIKI_DIR" >&2; exit 1; }
    echo "cloning wiki -> $WIKI_DIR"
    git clone -q "$WIKI_URL" "$WIKI_DIR"
fi

if [ "$MODE" != "check" ]; then
    cp "$SRC"/*.md "$WIKI_DIR"/
fi

# The wiki is client-facing: raw model-control tokens must never ship.
if grep -rl '<|' "$WIKI_DIR"/*.md >/dev/null 2>&1; then
    echo "FATAL: model-control tokens found in wiki pages:" >&2
    grep -rl '<|' "$WIKI_DIR"/*.md >&2
    exit 1
fi

# Every source page must exist in the wiki.
missing=0
for f in "$SRC"/*.md; do
    base="$(basename "$f")"
    if [ ! -f "$WIKI_DIR/$base" ]; then
        echo "MISSING: $base" >&2
        missing=1
    fi
done
[ "$missing" -eq 0 ] || exit 1

# Content must match the source exactly.
drift=0
for f in "$SRC"/*.md; do
    base="$(basename "$f")"
    cmp -s "$f" "$WIKI_DIR/$base" || { echo "DRIFT: $base" >&2; drift=1; }
done
[ "$drift" -eq 0 ] || exit 1

if [ "$MODE" = "push" ]; then
    cd "$WIKI_DIR"
    if [ -z "$(git status --porcelain)" ]; then
        echo "wiki already in sync; nothing to push"
    else
        git add -A
        git -c user.name="${GIT_USER_NAME:-$(git config user.name || echo wiki-sync)}" \
            -c user.email="${GIT_USER_EMAIL:-$(git config user.email || echo wiki@localhost)}" \
            commit -q -m "Sync docs/wiki from the archive"
        git push origin HEAD
        echo "wiki pushed"
    fi
fi

echo "wiki OK: $(ls "$WIKI_DIR"/*.md | wc -l) pages, $(grep -c '<|' "$WIKI_DIR"/*.md | awk -F: '{s+=$2} END {print s+0}') token artifacts"
