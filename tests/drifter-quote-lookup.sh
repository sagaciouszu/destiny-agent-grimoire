#!/bin/bash
# Drifter Quote Lookup (Fast)
# Uses inverted index for O(1) keyword lookup
# Usage: ./drifter-quote-lookup.sh "keyword"

KEYWORD=$(echo "$1" | tr '[:upper:]' '[:lower:]')

if [ -z "$KEYWORD" ]; then
    echo "Usage: $0 \"keyword\""
    echo "Fast quote lookup using inverted index."
    echo "Examples:"
    echo "  $0 \"gambit\""
    echo "  $0 \"eris\""
    echo "  $0 \"darkness\""
    exit 1
fi

python3 -c "
import json, sys
with open('${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}/reference/quote-inverted-index.json', 'r') as f:
    index = json.load(f)
keyword = '$KEYWORD'.lower()
if keyword in index:
    print(f'Found {len(index[keyword])} quotes for \"{keyword}\":')
    print()
    for q in index[keyword]:
        print(f'  \"{q}...\"')
else:
    # Try partial match
    matches = [k for k in index.keys() if keyword in k]
    if matches:
        print(f'No exact match for \"{keyword}\". Did you mean:')
        for m in matches[:10]:
            print(f'  {m} ({len(index[m])} quotes)')
    else:
        print(f'No quotes found for \"{keyword}\"')
"