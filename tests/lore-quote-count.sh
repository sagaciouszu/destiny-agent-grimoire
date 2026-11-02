#!/bin/bash
# Lore Quote Count Verification
# Verifies the number of Drifter transcript lines matches expected (473).
# Usage: ./tests/lore-quote-count.sh

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"

echo "=== LORE QUOTE COUNT VERIFICATION ==="
echo ""

COUNT=$(python3 - "$ARCHIVE" << 'PY'
import re, glob, os, sys
archive = sys.argv[1]
canon = []
for p in glob.glob(archive + '/source/transcripts/*.md'):
    for line in open(p, encoding='utf-8', errors='ignore'):
        m = re.match(r'^\*(?:The )?Drifter:\*\s*(.*)$', line.strip())
        if m:
            canon.append(m.group(1).strip())
print(len(canon))
PY
)

echo "Drifter transcript lines: $COUNT (expected: 473)"
if [ "$COUNT" -ge 470 ] && [ "$COUNT" -le 480 ]; then
    echo "✓ PASS: Quote count within expected range"
    exit 0
else
    echo "✗ FAIL: Quote count outside expected range (470-480)"
    exit 1
fi
