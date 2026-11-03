#!/bin/bash
# Database integrity test
DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
if [ ! -f "$DB" ]; then echo "FAIL: database not found at $DB - bootstrap: ./setup.sh, or python3 db/migrate.py (see README)"; exit 1; fi

echo "=== DATABASE INTEGRITY TEST ==="
PASS=0; FAIL=0
check() {
    if eval "$1" >/dev/null 2>&1; then echo "  ✓ $2"; PASS=$((PASS+1));
    else echo "  ✗ $2"; FAIL=$((FAIL+1)); fi
}

# Check tables exist
for t in books book_entries transcripts transcript_lines grimoire_cards interactions items records characters character_lines fts meta; do
    check "[ -n \"\$(sqlite3 \"$DB\" \"SELECT name FROM sqlite_master WHERE type='table' AND name='$t'\")\" ]" "table $t exists"
done

# Check counts > 0
for t in books book_entries transcripts transcript_lines grimoire_cards interactions items records characters character_lines; do
    N=$(sqlite3 "$DB" "SELECT COUNT(*) FROM $t")
    check "[ $N -gt 0 ]" "table $t has rows ($N)"
done

# Check FTS works
# HTML entity leakage (double-escaped Ishtar pages are a known risk)
ENT=$(sqlite3 "$DB" "SELECT (SELECT COUNT(*) FROM transcript_lines WHERE line LIKE '%&#%' OR line LIKE '%&amp;%') + (SELECT COUNT(*) FROM items WHERE item_type LIKE '%&#%' OR item_type LIKE '%&amp;%' OR text LIKE '%&#%' OR text LIKE '%&amp;%') + (SELECT COUNT(*) FROM interactions WHERE text LIKE '%&#%' OR text LIKE '%&amp;%') + (SELECT COUNT(*) FROM book_entries WHERE body LIKE '%&#%' OR body LIKE '%&amp;%') + (SELECT COUNT(*) FROM grimoire_cards WHERE body LIKE '%&#%' OR body LIKE '%&amp;%') + (SELECT COUNT(*) FROM records WHERE body LIKE '%&#%' OR body LIKE '%&amp;%')")
check "[ $ENT -eq 0 ]" "no HTML entity leakage ($ENT rows)"
# Standards gates (see STANDARDS.md)
VSPK=$(sqlite3 "$DB" "SELECT COUNT(*) FROM v_speakers" 2>/dev/null || echo 0)
check "[ $VSPK -gt 50 ]" "v_speakers view populated ($VSPK speakers)"
ALIASES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM speaker_aliases" 2>/dev/null || echo 0)
check "[ $ALIASES -ge 6 ]" "speaker_aliases table populated ($ALIASES aliases)"
VARIANTS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE speaker IN ('Commander Zavala','Cayde','Eris','Eris morn','Ikora Rey','Chiomi Esi')")
check "[ $VARIANTS -eq 0 ]" "speakers canonical (no alias variants: $VARIANTS)"
CARDURL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM grimoire_cards WHERE source_url IS NULL OR source_url NOT LIKE 'https://www.ishtar-collective.net/%'")
check "[ $CARDURL -eq 0 ]" "every card has a valid source_url ($CARDURL bad)"
CHARPROV=$(sqlite3 "$DB" "SELECT COUNT(*) FROM character_lines WHERE source_slug != '' AND source_slug NOT IN (SELECT slug FROM transcripts)")
check "[ $CHARPROV -eq 0 ]" "character quotes trace to real transcripts ($CHARPROV broken)"

FTS_COUNT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM fts")
check "[ $FTS_COUNT -gt 1000 ]" "FTS index populated ($FTS_COUNT entries)"

# Check FTS query returns results
FTS_RESULT=$(sqlite3 "$DB" "SELECT COUNT(*) FROM fts WHERE fts MATCH 'hive'")
check "[ $FTS_RESULT -gt 0 ]" "FTS query 'hive' returns results ($FTS_RESULT)"

# Check no empty critical fields
EMPTY_BOOKS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM books WHERE slug='' OR title=''")
check "[ $EMPTY_BOOKS -eq 0 ]" "no books with empty slug/title"

EMPTY_CHARS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM characters WHERE name='' OR slug=''")
check "[ $EMPTY_CHARS -eq 0 ]" "no characters with empty name/slug"

# Check foreign keys
ORPHAN_ENTRIES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM book_entries WHERE book_id NOT IN (SELECT id FROM books)")
check "[ $ORPHAN_ENTRIES -eq 0 ]" "no orphan book_entries"

ORPHAN_LINES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcript_lines WHERE transcript_id NOT IN (SELECT id FROM transcripts)")
check "[ $ORPHAN_LINES -eq 0 ]" "no orphan transcript_lines"

# Shipped artifact: no WAL mode, no -wal/-shm sidecars
JOURNAL=$(sqlite3 "$DB" "PRAGMA journal_mode")
SIDECARS=$(ls "$(dirname "$DB")"/grimoire.db-wal "$(dirname "$DB")"/grimoire.db-shm 2>/dev/null | wc -l)
check "[ \"$JOURNAL\" = \"delete\" ] && [ $SIDECARS -eq 0 ]" "no WAL sidecars (journal_mode=$JOURNAL)"

# Check meta table
META_VERSION=$(sqlite3 "$DB" "SELECT value FROM meta WHERE key='version'")
check "[ -n \"$META_VERSION\" ]" "meta version set ($META_VERSION)"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
