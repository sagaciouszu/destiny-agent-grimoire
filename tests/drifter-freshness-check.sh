#!/bin/bash
# Drifter Lore Freshness Check (SQLite)
DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
if [ ! -f "$DB" ]; then echo "FAIL: database not found at $DB - bootstrap: ./setup.sh, or python3 db/migrate.py (see README)"; exit 1; fi

echo "=== DRIFTER LORE FRESHNESS CHECK ==="
echo ""
LAST_SCRAPE=$(sqlite3 "$DB" "SELECT value FROM meta WHERE key='last_updated'")
echo "Database last updated: $LAST_SCRAPE"
echo "Current date: $(date +%Y-%m-%d)"
if [ -n "$LAST_SCRAPE" ]; then
    LAST_EPOCH=$(date -d "$LAST_SCRAPE" +%s 2>/dev/null || echo "0")
    NOW_EPOCH=$(date +%s)
    AGE_DAYS=$(( (NOW_EPOCH - LAST_EPOCH) / 86400 ))
    echo "Database age: $AGE_DAYS days"
    if [ "$AGE_DAYS" -gt 30 ]; then
        echo "WARNING: Database is $AGE_DAYS days old. Consider re-scraping."
    else
        echo "OK: Database is fresh ($AGE_DAYS days old)."
    fi
else
    echo "WARNING: Could not determine database age."
fi
echo ""
BOOKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM books")
ENTRIES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM book_entries")
TRANSCRIPTS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcripts")
CARDS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM grimoire_cards")
INTERACTIONS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM interactions")
ITEMS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM items")
RECORDS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM records")
echo "Books: $BOOKS"
echo "Book entries: $ENTRIES"
echo "Transcripts: $TRANSCRIPTS"
echo "Grimoire cards: $CARDS"
echo "Interactions: $INTERACTIONS"
echo "Items: $ITEMS"
echo "Records: $RECORDS"
echo ""
echo "=== FRESHNESS CHECK COMPLETE ==="
