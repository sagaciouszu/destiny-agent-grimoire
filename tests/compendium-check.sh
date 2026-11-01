#!/bin/bash
# Compendium integrity check (agnostic).
# Verifies compendium files exist and are non-empty.
ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
echo "=== COMPENDIUM CHECK ==="
PASS=0; FAIL=0
if [ -f "$ARCHIVE/compendium/index.md" ]; then echo "  ✓ compendium/index.md"; PASS=$((PASS+1)); else echo "  ✗ compendium/index.md"; FAIL=$((FAIL+1)); fi
N=$(find "$ARCHIVE/compendium/characters" -name '*.md' 2>/dev/null | wc -l)
if [ "$N" -ge 1 ]; then echo "  ✓ character files: $N"; PASS=$((PASS+1)); else echo "  ✗ no character files"; FAIL=$((FAIL+1)); fi
EMPTY=$(find "$ARCHIVE/compendium" -name '*.md' -empty 2>/dev/null | wc -l)
if [ "$EMPTY" -eq 0 ]; then echo "  ✓ no empty compendium files"; PASS=$((PASS+1)); else echo "  ✗ empty files: $EMPTY"; FAIL=$((FAIL+1)); fi
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
