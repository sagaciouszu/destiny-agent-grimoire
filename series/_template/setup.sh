#!/bin/bash
# Seed this agent workspace: link or clone the grimoire and get the database.
# Usage: ./setup.sh [grimoire-repo-path]
set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
LORE="$REPO/lore"
SOURCE="${1:-}"

if [ -n "$SOURCE" ] && [ -d "$SOURCE" ]; then
    rm -f "$LORE"
    ln -s "$(cd "$SOURCE" && pwd)" "$LORE"
    echo "linked $LORE -> $SOURCE"
elif [ -d "$LORE" ] && [ -f "$LORE/db/grimoire.db" ]; then
    echo "using existing $LORE"
else
    [ -d "$LORE" ] || git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git "$LORE"
    echo "cloned $LORE"
fi

if [ ! -f "$LORE/db/grimoire.db" ]; then
    mkdir -p "$LORE/db"
    curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db \
        -o "$LORE/db/grimoire.db"
    echo "downloaded grimoire.db"
fi

echo
echo "README: read README.md"
echo "Audit:  bash tests/master-audit.sh"
