#!/bin/bash
# Sync both agent repos into the live OpenCode agents directory.
# Preserves runtime memory, lore links and the nested Eris agent.
# Usage: scripts/sync-live-agents.sh [--dry-run]
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(dirname "$HERE")"
DEST="${OPENCODE_AGENTS:-$HOME/.config/opencode/agents}"
DRY=""
[ "${1:-}" = "--dry-run" ] && DRY="--dry-run"

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
[ -z "$DRY" ] && command -v opencode >/dev/null && opencode reload >/dev/null 2>&1 && echo "opencode reloaded"
