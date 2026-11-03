#!/bin/bash
# Sync both agent repos into a live runtime workspace.
# Preserves runtime memory, lore links and nested agent directories.
# Usage: scripts/sync-live-agents.sh [--openclaw] [--dry-run]
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(dirname "$HERE")"
DRY=""
TARGET="opencode"
DEST="${OPENCODE_AGENTS:-$HOME/.config/opencode/agents}"

for arg in "$@"; do
    case "$arg" in
        --openclaw)
            TARGET="openclaw"
            DEST="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace-drifter}" ;;
        --dry-run) DRY="--dry-run" ;;
        *) echo "usage: $0 [--openclaw] [--dry-run]" >&2; exit 2 ;;
    esac
done

[ -d "$DEST" ] || { echo "FATAL: $DEST missing"; exit 1; }

rsync -a --delete $DRY \
  --exclude '.git' --exclude 'lore' --exclude 'eris/' --exclude 'USER.md' --exclude 'DREAMS.md' \
  --exclude 'memory/' --exclude 'core/user-memory.md' --exclude 'core/journal.md' \
  --exclude 'core/session-state.md' --exclude 'core/cross-session-memory.md' \
  "$WORK/how-to-drift-for-agents/" "$DEST/"

mkdir -p "$DEST/eris"
rsync -a --delete $DRY \
  --exclude '.git' --exclude 'lore' --exclude 'USER.md' \
  "$WORK/eris-morn/" "$DEST/eris/"

# OpenCode discovers every .md under agents/ as an agent, including symlinked
# directories. Keep the shared lore link outside agents/ and mark every
# non-entry file inert so only the two entry agents are selectable.
if [ -z "$DRY" ] && [ "$TARGET" = "opencode" ]; then
    for link in "$DEST/lore" "$DEST/eris/lore"; do
        if [ -d "$link" ] && [ ! -L "$link" ]; then
            echo "FATAL: $link is a directory; move it outside agents/ (OpenCode would register it as agents)" >&2
            exit 1
        fi
    done
    find "$DEST" -maxdepth 3 -type l -name lore -delete
    python3 - "$DEST" <<'PY'
import os, sys
dest = sys.argv[1]
keep = {'drifter.md', 'eris/eris.md'}
for root, dirs, files in os.walk(dest):
    dirs[:] = [d for d in dirs if d != '.git']
    for name in files:
        if not name.endswith('.md'):
            continue
        path = os.path.join(root, name)
        rel = os.path.relpath(path, dest).replace(os.sep, '/')
        if rel in keep:
            continue
        with open(path, encoding='utf-8') as f:
            text = f.read()
        head = text.split('---', 2)
        if text.startswith('---\n') and len(head) > 1 and 'disabled: true' in head[1]:
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write('---\ndisabled: true\n---\n\n' + text)
PY
fi

echo "synced Drifter -> $DEST"
echo "synced Eris    -> $DEST/eris"
if [ -z "$DRY" ] && [ "$TARGET" = "opencode" ] && [ -z "$NO_RELOAD" ] && command -v opencode >/dev/null; then
    opencode reload >/dev/null 2>&1 && echo "opencode reloaded"
fi
