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
check "$Q verify 'Absolutely not.' --speaker Eris | grep -q VERIFIED" "verify accepts a name prefix"
check "! $Q verify 'Absolutely not.' --speaker Morn | grep -q VERIFIED" "verify rejects a name fragment"
check "! $Q verify 'Absolutely not.' --speaker ris | grep -q VERIFIED" "verify rejects a mid-word fragment"
check "! $Q book '%' 2>&1 | grep -q '^===' " "book treats % literally"
check "! $Q character '%' 2>&1 | grep -q '^===' " "character treats % literally"
if $Q search "$(printf 'crota\u202e')" --limit 1 | python3 -c 'import sys; sys.exit(1 if "\u202e" in sys.stdin.read() else 0)'; then
    echo "  ✓ search strips bidi overrides"; PASS=$((PASS+1))
else
    echo "  ✗ search strips bidi overrides"; FAIL=$((FAIL+1))
fi
check "$Q character eris --limit 2 | grep -q 'Eris Morn'" "character curated quotes"
check "$Q character calus --limit 2 | grep -q 'transcript lines'" "character falls back to transcripts"
check "$Q character 'Lord Shaxx' --all --limit 2 | grep -q 'caption lines'" "character labels caption-only speakers"
CAP_TIER=$($Q character 'Lord Shaxx' --all --limit 1 --json | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["source_tier"])')
check "[ \"$CAP_TIER\" = game_caption ]" "character rows carry source_tier ($CAP_TIER)"
check "$Q character 'The Drifter' --limit 1 | grep -q '(drifter)'" "character resolves curated aliases"
check "$Q character-info calus | grep -qE 'spoken lines: [1-9]'" "character-info falls back to transcripts"
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
check "$Q stats --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d[\"seasons\"]==28 and d[\"events\"]==9'" "stats reports taxonomy counts"
check "$Q coverage --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert len(d[\"activities\"])>=60'" "coverage --json parses"
check "$Q list seasons --limit 30 | grep -q 'Season of Opulence'" "list seasons"
check "$Q list events | grep -q 'Festival of the Lost'" "list events"
check "$Q search calus --season 17 --limit 3 | grep -q 'results'" "search filters by season number"
check "$Q search calus --season haunted --limit 3 | grep -q 'results'" "search filters by season name"
check "$Q search nightmare --activity nightmare-containment --limit 3 | grep -q 'results'" "search filters by activity"
check "$Q search dawning --event 'The Dawning' --limit 3 | grep -q 'results'" "search filters by event"
check "$Q activity nightmare-containment | grep -q 'Coverage:'" "activity details and coverage"
check "$Q event the-dawning | grep -q 'Occurrences:'" "event details and occurrences"
check "$Q transcript 'savathuns-spire' --limit 1 | grep -q 'Taxonomy:'" "transcript reports taxonomy"
check "$Q search calus --season 99 --limit 1 | grep -q '0 results of 0'" "unknown season returns no rows"
check "$Q activity menagerie | grep -q '316 lines'" "menagerie dialogue ingested (count verified post-curation: +4 game-caption announcer VO tables in derived facet)"
check "$Q character calus --about Hunter | grep -q 'cunning'" "menagerie Hunter callout"
check "$Q character calus --about Titan | grep -q 'bravery'" "menagerie Titan callout"
check "$Q character calus --about Warlock | grep -q 'wisdom'" "menagerie Warlock callout"
check "$Q verify 'Light the way, Hunter.' --speaker Calus --exact | grep -q VERIFIED" "menagerie variant verifies"
check "$Q search 'Light the way, Warlock' --activity menagerie --limit 1 | grep -q 'results'" "menagerie search by activity"
check "$Q activity last-wish | grep -q 'Coverage:'" "last wish coverage"
check "$Q activity vow-of-the-disciple | grep -q 'Rhulk'" "vow transcript has Rhulk"
check "$Q activity vespers-host | grep -q '71 lines'" "vespers host dialogue"
check "$Q character rhulk --limit 3 | grep -q 'transcript lines'" "rhulk speaker depth"
check "$Q activity breach-executable | grep -q '272 lines'" "breach executable dialogue"
check "$Q activity the-nether | grep -q 'Sloane'" "nether speakers"
check "$Q activity the-coil | grep -q 'Riven'" "coil dialogue"
check "[ \"$($Q search failsafe --season 24 --limit 1 | tail -1)\" = \"$($Q search failsafe --season echoes --limit 1 | tail -1)\" ]" "episode number and name agree"
check "[ \"$($Q search sloane --season 26 --limit 1 | tail -1)\" = \"$($Q search sloane --season heresy --limit 1 | tail -1)\" ]" "heresy number and name agree"
check "$Q list activities --limit 3 --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert isinstance(d,list) and len(d)==3'" "list activities --json"
check "$Q event the-dawning --json | python3 -c 'import json,sys; d=json.load(sys.stdin); assert len(d)>5'" "event occurrences json"
check "$Q activity presage | grep -q 'Caiatl'" "presage dialogue"
check "$Q activity vox-obscura | grep -q 'Zavala'" "vox obscura dialogue"
check "$Q activity encore | grep -q 'Maya Sundaresh'" "encore dialogue"
check "$Q activity override | grep -q '252 lines'" "override dialogue"
check "$Q activity salvage | grep -q 'Sloane'" "salvage dialogue"
check "$Q activity seraph-towers | grep -q 'Ana Bray'" "seraph towers dialogue"
check "$Q activity astral-alignment | grep -q 'Petra Venj'" "astral alignment dialogue"
HAS_LORE=$(sqlite3 "$ARCHIVE/db/grimoire.db" "SELECT COUNT(*) FROM lore_entries" 2>/dev/null || echo 0)
if [ "${HAS_LORE:-0}" -gt 0 ]; then
    check "$Q list lore --limit 3 | grep -q 'is_duplicate'" "list lore entries"
    check "$Q search 'iris unfurls' --type lore --limit 1 | grep -q 'lore_entry'" "search lore entries"
else
    echo "  - lore enrichment not present (source build), skipped"
fi
HAS_SEALS=$(sqlite3 "$ARCHIVE/db/grimoire.db" "SELECT COUNT(*) FROM seals" 2>/dev/null || echo 0)
if [ "${HAS_SEALS:-0}" -gt 0 ]; then
    check "$Q seals | grep -q 'Conqueror'" "seal list"
    check "$Q seal Conqueror | grep -q 'Grandmaster'" "seal records"
    check "$Q list seals --limit 3 | grep -q 'records'" "list seals"
else
    echo "  - seal enrichment not present (source build), skipped"
fi
check "$Q character Calus --class hunter --about Hunter | grep -q 'cunning'" "class hunter variants"
check "$Q character Calus --class titan --about Titan | grep -q 'bravery'" "class titan variants"
check "$Q search 'pride themselves' --class warlock --limit 1 | grep -q 'wisdom'" "class warlock search"
check "python3 $ARCHIVE/tests/class-filter-test.py" "class transcript filter"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
