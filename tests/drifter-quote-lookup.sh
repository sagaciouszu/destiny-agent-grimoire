#!/bin/bash
# Drifter Quote Lookup (Fast)
# Uses inverted index for O(1) keyword lookup
# Usage: ./drifter-quote-lookup.sh "keyword or phrase"
# All words are used; quoting is optional.

KEYWORD="$*"

if [ -z "$KEYWORD" ]; then
    echo "Usage: $0 \"keyword or phrase\""
    echo "Fast quote lookup using inverted index."
    echo "Examples:"
    echo "  $0 \"gambit\""
    echo "  $0 \"eris\""
    echo "  $0 \"darkness\""
    exit 1
fi

WS="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"

python3 - "$WS" "$KEYWORD" <<'PY'
import json, re, sys

ws, raw = sys.argv[1], sys.argv[2]
keyword = re.sub(r'[\x00-\x1f\x7f]+', ' ', raw)
keyword = ' '.join(keyword.split()).lower()

with open(f'{ws}/reference/quote-inverted-index.json', 'r', encoding='utf-8') as f:
    index = json.load(f)

if keyword in index:
    print(f'Found {len(index[keyword])} quotes for "{keyword}":')
    print()
    for q in index[keyword]:
        print(f'  "{q}..."')
else:
    matches = [k for k in index if keyword in k]
    if matches:
        print(f'No exact match for "{keyword}". Did you mean:')
        for m in matches[:10]:
            print(f'  {m} ({len(index[m])} quotes)')
    else:
        print(f'No quotes found for "{keyword}"')
PY
