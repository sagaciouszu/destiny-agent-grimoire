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

# Check meta table
META_VERSION=$(sqlite3 "$DB" "SELECT value FROM meta WHERE key='version'")
check "[ -n \"$META_VERSION\" ]" "meta version set ($META_VERSION)"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
