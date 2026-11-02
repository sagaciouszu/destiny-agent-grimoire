#!/bin/bash
# Lore Archive Integrity Check
# Verifies the archive structure: books, transcripts, indexes.
# Usage: ./tests/lore-integrity.sh

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"

echo "=== LORE ARCHIVE INTEGRITY CHECK ==="
echo ""

PASS=0; FAIL=0

check() {
    if eval "$1" >/dev/null 2>&1; then
        echo "  ✓ $2"; PASS=$((PASS+1))
    else
        echo "  ✗ $2"; FAIL=$((FAIL+1))
    fi
}

# Directory structure
check "[ -d $ARCHIVE/source/books ]" "books/ directory exists"
check "[ -d $ARCHIVE/source/transcripts ]" "transcripts/ directory exists"
check "[ -f $ARCHIVE/index.md ]" "index.md exists"
check "[ -f $ARCHIVE/source/transcripts/index.md ]" "transcripts/index.md exists"

# File counts
BOOKS=$(ls "$ARCHIVE/source/books"/*.md 2>/dev/null | wc -l)
TRANSCRIPTS=$(ls "$ARCHIVE/source/transcripts"/*.md 2>/dev/null | grep -v 'index.md' | wc -l)
check "[ $BOOKS -ge 100 ]" "Books: $BOOKS (expected 109+)"
check "[ $TRANSCRIPTS -ge 60 ]" "Transcripts: $TRANSCRIPTS (expected 68+)"

# No empty files
EMPTY=$(find "$ARCHIVE/source/books" "$ARCHIVE/source/transcripts" -name '*.md' -empty 2>/dev/null | wc -l)
check "[ $EMPTY -eq 0 ]" "No empty files (found: $EMPTY)"

# Verify index.md has book entries and every slug maps to a file
python3 - "$ARCHIVE" << 'PYEOF'
import os, sys
archive = sys.argv[1]
idx = open(os.path.join(archive, 'index.md')).read()
entries = []
for l in idx.split('\n'):
    if not l.strip().startswith('|'): continue
    if '|' not in l: continue
    cells = [c.strip() for c in l.strip().strip('|').split('|')]
    if len(cells) >= 3 and cells[2] in ('done','partial','pending','in-progress'):
        entries.append(l)
print("  ✓ index.md has %d book entries" % len(entries))
if len(entries) < 100:
    sys.exit(1)
slugs = []
for l in entries:
    cells = [c.strip() for c in l.strip().strip('|').split('|')]
    if len(cells) >= 2:
        slugs.append(cells[1].removeprefix('book-'))
files = {f[:-3] for f in os.listdir(os.path.join(archive, 'source', 'books')) if f.endswith('.md')}
missing = [s for s in slugs if s not in files]
if missing:
    print("  ✗ Missing book files: %s" % missing)
    sys.exit(1)
print("  ✓ All %d index slugs have book files" % len(slugs))
PYEOF
if [ $? -eq 0 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); fi

echo ""
echo "Books: $BOOKS | Transcripts: $TRANSCRIPTS | Empty: $EMPTY"
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
