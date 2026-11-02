#!/bin/bash
# Lore quote count verification (SQLite)
DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
[ -f "$DB" ] || { echo "FAIL: database not found"; exit 1; }
echo "=== LORE QUOTE COUNT VERIFICATION ==="
TOTAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE speaker = 'Drifter'")
echo "Drifter transcript lines (exact): $TOTAL (expected: 473)"
if [ "$TOTAL" -eq "473" ]; then echo "PASS: Quote count within expected range"
else echo "WARN: Quote count diff: $((TOTAL - 473))"; fi
TOTAL_ALL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE speaker LIKE '%Drifter%'")
echo "Drifter all variants: $TOTAL_ALL"
ERIS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE speaker LIKE '%Eris%'")
echo "Eris Morn transcript lines: $ERIS"
LINES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines")
echo "Total transcript lines: $LINES"
