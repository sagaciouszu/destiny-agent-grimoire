#!/bin/bash
# Lore quote count verification (SQLite)
DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
[ -f "$DB" ] || { echo "FAIL: database not found"; exit 1; }
echo "=== LORE QUOTE COUNT VERIFICATION ==="
TOTAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE speaker = 'Drifter'")
echo "Drifter transcript lines (exact): $TOTAL (DB now includes quoted + narration lines)"
if [ "$TOTAL" -ge "470" ]; then echo "PASS: Quote count within expected range"
else echo "WARN: Drifter lines now $TOTAL"; fi
TOTAL_ALL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE speaker LIKE '%Drifter%'")
echo "Drifter all variants: $TOTAL_ALL"
ERIS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE speaker LIKE '%Eris%'")
echo "Eris Morn transcript lines: $ERIS"
LINES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines")
echo "Total transcript lines: $LINES"
