#!/bin/bash
# Rolling backup of the archive minus the database, with a checksum.
# Usage: scripts/backup.sh [output.zip]
set -e
HERE="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$HOME/destiny-agent-grimoire-backup.zip}"
rm -f "$OUT" "$OUT.sha256"
cd "$(dirname "$HERE")"
zip -rq "$OUT" "$(basename "$HERE")" -x "$(basename "$HERE")/db/grimoire.db"
sha256sum "$OUT" > "$OUT.sha256"
ls -lh "$OUT" | awk '{print "backup:", $5, $9}'
cat "$OUT.sha256"
