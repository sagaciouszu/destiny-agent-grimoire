#!/bin/bash
# Conversation smoke: confirm the database has lines for this speaker.
# Usage: bash tests/conversation-test.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
LORE="${LORE:-$REPO/lore}"
DB="$LORE/db/grimoire.db"
SPEAKER="{{name}}"

[ -f "$DB" ] || { echo "FAIL: database not found at $DB - run ./setup.sh"; exit 1; }

COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE speaker LIKE '%' || '$SPEAKER' || '%';" 2>/dev/null || echo 0)
echo "speaker lines for $SPEAKER: $COUNT"
[ "$COUNT" -gt 0 ] || echo "note: no transcript lines yet; populate the persona from canon"
