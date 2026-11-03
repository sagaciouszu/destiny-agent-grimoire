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

echo "synced Drifter -> $DEST"
echo "synced Eris    -> $DEST/eris"
if [ -z "$DRY" ] && [ "$TARGET" = "opencode" ] && command -v opencode >/dev/null; then
    opencode reload >/dev/null 2>&1 && echo "opencode reloaded"
fi
