#!/bin/bash
# Query Interface Test - verifies the agent-facing query.py contract.
# Checks exit codes, output shape, JSON validity, snippet mode and type filters.
# Usage: ./tests/query-interface-test.sh

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
Q="python3 $ARCHIVE/db/query.py"
PASS=0; FAIL=0
check() {
    if eval "$1" >/dev/null 2>&1; then echo "  ✓ $2"; PASS=$((PASS+1));
    else echo "  ✗ $2"; FAIL=$((FAIL+1)); fi
}

echo "=== QUERY INTERFACE TEST ==="

check "$Q stats | grep -q 'transcript_lines'" "stats reports counts"
check "$Q stats --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d[\"fts\"]>100000'" "stats --json parses"
check "$Q search crota --limit 3 | grep -q 'results'" "search returns results"
check "$Q search crota --type grimoire --limit 2 | grep -q 'grimoire_card'" "type filter returns only that source"
check "$Q search crota --type items --limit 2 | grep -q 'item'" "type filter works for items"
check "! $Q search crota --type grimoire --limit 2 | grep -q 'transcript_line'" "type filter excludes other sources"
check "$Q search crota --limit 2 --json | python3 -c 'import json,sys; json.load(sys.stdin)'" "search --json parses"
check "$Q search crota --limit 1 | grep -q '\['" "snippet mode marks matches"
check "$Q search crota --limit 1 --full | wc -l | grep -qE '^[2-9]'" "search --full shows text"
check "$Q search 'looked (' --limit 1 >/dev/null" "search tolerates unbalanced parens"
check "$Q search 'C++' --limit 1 >/dev/null" "search tolerates plus signs"
check "$Q search 'looked -word' --limit 1 >/dev/null" "search tolerates leading dash"
check "$Q search looked up that word --limit 1 >/dev/null" "search joins unquoted words"
check "$Q search '\"' 2>&1 | grep -q 'searchable word'" "search rejects punctuation-only cleanly"
check "$Q verify Absolutely not. --speaker 'Eris Morn' --exact | grep -q VERIFIED" "verify joins unquoted words"
check "$Q character eris --limit 2 | grep -q 'Eris Morn'" "character curated quotes"
check "$Q character eris --about hive --all --limit 3 | grep -qi 'hive'" "character --about filter"
check "$Q character eris --limit 2 --json | python3 -c 'import json,sys; json.load(sys.stdin)'" "character --json parses"
check "$Q item 0a0x-nightmask | grep -q 'Nightmask'" "item lookup"
check "$Q item does-not-exist-xyz; [ \$? -eq 1 ]" "missing item exits 1"
check "$Q verify 'I am Eris Morn.' --speaker 'Eris Morn' | grep -q VERIFIED && ! $Q verify 'I am Eris Morn.' --speaker 'Zavala' | grep -q VERIFIED" "verify checks attribution"
check "$Q verify 'completely fabricated sentence xyzzy' | grep -q 'NOT FOUND'" "verify rejects unknown quote"
check "$Q book 'a-man-with-no-name' --limit 2 | grep -q 'A Man with No Name'" "book reads entries"
check "$Q transcript 'savathuns-spire' --limit 2 | grep -q 'Eris Morn'" "transcript reads lines"
check "$Q find-item 'nightmask' | grep -q '0a0x-nightmask'" "find-item matches titles"
check "$Q record 'am-i-to-cast-a-shadow' | grep -q 'Am I to cast'" "record reads a seal"
check "$Q verify-many 'I am Eris Morn.' 'not canon zzz' | grep -q '1 of 2 verified'" "verify-many batches quotes"
check "$Q character-info eris | grep -q 'Curated quotes: 262'" "character-info reports counts"
check "$Q verify 'completely fabricated sentence xyzzy'; [ \$? -eq 1 ]" "verify unknown exits 1"
check "$Q verify 'Absolutely not.' --exact --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d[\"verified\"] and d[\"matches\"][0][\"exact\"]'" "verify --exact --json parses"
check "$Q list books --limit 3 | grep -q 'entry_count'" "list books"
check "$Q list speakers --limit 3 | grep -q 'Ghost'" "list speakers"
check "$Q list records --limit 2 --json | python3 -c 'import json,sys; json.load(sys.stdin)'" "list --json parses"
check "$Q list characters --limit 18 | grep -q 'eris-morn'" "list characters"
check "python3 -c 'import ast; ast.parse(open(\"$ARCHIVE/db/query.py\").read())'" "query.py parses"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
