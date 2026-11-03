#!/bin/bash
# Lore Archive Integrity Check (SQLite-backed, plus source-corpus format check)
DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
ARCHIVE="$(cd "$(dirname "$0")/.." && pwd)"
[ -f "$DB" ] || { echo "FAIL: database not found at $DB - bootstrap: ./setup.sh, or python3 db/migrate.py (see README)"; exit 1; }

echo "=== LORE ARCHIVE INTEGRITY CHECK ==="
PASS=0; FAIL=0

check() {
    if eval "$1" >/dev/null 2>&1; then echo "  $2"; PASS=$((PASS+1))
    else echo "  $2"; FAIL=$((FAIL+1)); fi
}

source_data="$(cd "$ARCHIVE/source" 2>/dev/null && pwd)"

# Directory structure (source markdown kept as corpus)
check "[ -d $source_data/books ]" "  source/books/ exists"
check "[ -d $source_data/transcripts ]" "  source/transcripts/ exists"
check "[ -f $ARCHIVE/index.md ]" "  index.md exists"
check "[ -f $DB ]" "  db/grimoire.db exists"

# File counts from markdown corpus
BOOKS=$(ls "$source_data/books"/*.md 2>/dev/null | wc -l)
TRANSCRIPTS=$(ls "$source_data/transcripts"/*.md 2>/dev/null | grep -v 'index.md' | wc -l)
check "[ $BOOKS -ge 110 ]" "  Books: $BOOKS (expected 110+)"
check "[ $TRANSCRIPTS -ge 60 ]" "  Transcripts: $TRANSCRIPTS (expected 68+)"

EMPTY=$(find "$source_data" -name '*.md' -empty 2>/dev/null | wc -l)
check "[ $EMPTY -eq 0 ]" "  No empty source files (found: $EMPTY)"

# SQLite-backed database integrity
BOOKSDB=$(sqlite3 "$DB" "SELECT COUNT(*) FROM books")
ENTRIES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM book_entries")
CMDS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM grimoire_cards")
INTS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM interactions")
ITEMS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM items")
RECORDS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM records")
CHARS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM characters")
CLINES=$(sqlite3 "$DB" "SELECT COUNT(*) FROM character_lines")
FTS=$(sqlite3 "$DB" "SELECT COUNT(*) FROM fts")

check "[ $BOOKSDB -ge 100 ]" "  DB books: $BOOKSDB"
check "[ $ENTRIES -ge 1000 ]" "  DB book_entries: $ENTRIES"
check "[ $INTS -ge 1000 ]" "  DB interactions: $INTS"
check "[ $ITEMS -ge 50000 ]" "  DB items: $ITEMS"
check "[ $RECORDS -ge 50 ]" "  DB records: $RECORDS"
check "[ $CHARS -ge 10 ]" "  DB characters: $CHARS"
check "[ $CLINES -ge 1000 ]" "  DB character_lines: $CLINES"
check "[ $FTS -ge 50000 ]" "  DB FTS index: $FTS"

# No empty required sqlite fields
NOSLUG=$(sqlite3 "$DB" "SELECT COUNT(*) FROM books WHERE slug='' OR title=''")
check "[ $NOSLUG -eq 0 ]" "  No books with empty slug/title"
NOREC=$(sqlite3 "$DB" "SELECT COUNT(*) FROM records WHERE slug=''")
check "[ $NOREC -eq 0 ]" "  No records with empty slug"

echo ""
echo "DB: books=$BOOKSDB entries=$ENTRIES cards=$CMDS interactions=$INTS items=$ITEMS records=$RECORDS chars=$CHARS clines=$CLINES fts=$FTS"
echo "Books: $BOOKS | Transcripts: $TRANSCRIPTS | Empty: $EMPTY"
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
