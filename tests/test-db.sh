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

# Item title index mirrors titled items
T_EXPECTED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM items WHERE title != ''")
T_ACTUAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM item_title_fts")
check "[ $T_ACTUAL -eq $T_EXPECTED ]" "item title index complete ($T_ACTUAL rows)"

# Verification index mirrors indexable rows
V_EXPECTED=$(sqlite3 "$DB" "SELECT (SELECT COUNT(*) FROM transcript_lines)+(SELECT COUNT(*) FROM book_entries)+(SELECT COUNT(*) FROM grimoire_cards)+(SELECT COUNT(*) FROM interactions)+(SELECT COUNT(*) FROM items WHERE text!='')+(SELECT COUNT(*) FROM records) + COALESCE((SELECT COUNT(*) FROM lore_entries WHERE is_duplicate=0),0)")
V_ACTUAL=$(sqlite3 "$DB" "SELECT COUNT(*) FROM verify_fts")
check "[ $V_ACTUAL -eq $V_EXPECTED ]" "verification index complete ($V_ACTUAL rows)"

# Taxonomy integrity (additive layer, see docs/TAXONOMY.md)
for t in expansions seasons events event_occurrences activities transcript_classification item_classification document_classification; do
    check "[ -n \"\$(sqlite3 \"$DB\" \"SELECT name FROM sqlite_master WHERE type='table' AND name='$t'\")\" ]" "table $t exists"
done
ORPHANS=$(sqlite3 "$DB" "SELECT (SELECT COUNT(*) FROM activities a LEFT JOIN seasons s ON s.slug=a.season_slug WHERE a.season_slug IS NOT NULL AND s.slug IS NULL) + (SELECT COUNT(*) FROM activities a LEFT JOIN expansions x ON x.slug=a.expansion_slug WHERE a.expansion_slug IS NOT NULL AND x.slug IS NULL) + (SELECT COUNT(*) FROM activities a LEFT JOIN events e ON e.slug=a.event_slug WHERE a.event_slug IS NOT NULL AND e.slug IS NULL) + (SELECT COUNT(*) FROM transcript_classification c LEFT JOIN seasons s ON s.slug=c.season_slug WHERE c.season_slug IS NOT NULL AND s.slug IS NULL) + (SELECT COUNT(*) FROM transcript_classification c LEFT JOIN activities a ON a.slug=c.activity_slug WHERE c.activity_slug IS NOT NULL AND a.slug IS NULL) + (SELECT COUNT(*) FROM item_classification c LEFT JOIN seasons s ON s.slug=c.season_slug WHERE c.season_slug IS NOT NULL AND s.slug IS NULL)")
check "[ $ORPHANS -eq 0 ]" "taxonomy references resolve ($ORPHANS orphans)"
UNCLASSIFIED=$(sqlite3 "$DB" "SELECT COUNT(*) FROM transcripts t LEFT JOIN transcript_classification c ON c.transcript_id=t.id WHERE c.transcript_id IS NULL")
check "[ $UNCLASSIFIED -eq 0 ]" "every transcript has a classification row ($UNCLASSIFIED missing)"
SEASON_NUMBERS=$(sqlite3 "$DB" "SELECT COUNT(DISTINCT season_number) FROM seasons WHERE season_number IS NOT NULL")
check "[ $SEASON_NUMBERS -eq 28 ]" "official season numbers are unique ($SEASON_NUMBERS seasons)"
UNKNOWN_SHARE=$(sqlite3 "$DB" "SELECT CAST(100 * SUM(confidence='unknown') / COUNT(*) AS INT) FROM transcript_classification")
check "[ $UNKNOWN_SHARE -lt 50 ]" "unknown classification below 50% ($UNKNOWN_SHARE%)"

# Shipped artifact: no WAL mode, no -wal/-shm sidecars
JOURNAL=$(sqlite3 "$DB" "PRAGMA journal_mode")
SIDECARS=$(ls "$(dirname "$DB")"/grimoire.db-wal "$(dirname "$DB")"/grimoire.db-shm 2>/dev/null | wc -l)
check "[ \"$JOURNAL\" = \"delete\" ] && [ $SIDECARS -eq 0 ]" "no WAL sidecars (journal_mode=$JOURNAL)"

# Check meta table
META_VERSION=$(sqlite3 "$DB" "SELECT value FROM meta WHERE key='version'")
FILE_VERSION=$(cat "$(dirname "$DB")/SCHEMA_VERSION" 2>/dev/null || true)
check "[ -n \"$META_VERSION\" ] && [ \"$META_VERSION\" = \"$FILE_VERSION\" ]" "schema version matches file ($META_VERSION)"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
