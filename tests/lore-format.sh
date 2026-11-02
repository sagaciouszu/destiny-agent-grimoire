#!/bin/bash
# Lore Format Verification
# Checks that transcripts follow the expected format.
# Usage: ./tests/lore-format.sh

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"

echo "=== LORE FORMAT VERIFICATION ==="
echo ""

PASS=0; FAIL=0
for f in "$ARCHIVE"/source/transcripts/*.md; do
    [ "$(basename "$f")" = "index.md" ] && continue
    # Check file has a title
    if ! head -1 "$f" | grep -q '^#'; then
        echo "  ✗ Missing title: $(basename "$f")"
        FAIL=$((FAIL+1))
        continue
    fi
    # Check file is not empty
    if [ ! -s "$f" ]; then
        echo "  ✗ Empty file: $(basename "$f")"
        FAIL=$((FAIL+1))
        continue
    fi
    PASS=$((PASS+1))
done

echo ""
echo "Transcripts checked: $((PASS + FAIL))"
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
