#!/bin/bash
# Drifter Transcript Search Tool
# Usage: ./drifter-search.sh "search term" [directory]
# Searches all Drifter transcripts and agent files for matching quotes

SEARCH_DIR="${2:-${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}/source/transcripts}"
PATTERN="$1"

if [ -z "$PATTERN" ]; then
    echo "Usage: $0 \"search term\" [directory]"
    echo "Searches all Drifter transcripts and agent files for matching quotes."
    echo ""
    echo "Examples:"
    echo "  $0 \"bad ideas\""
    echo "  $0 \"moondust\""
    echo "  $0 \"gambit\" ${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"
    exit 1
fi

echo "=== Searching for: \"$PATTERN\" ==="
echo ""

# Search transcripts
echo "--- TRANSCRIPTS ---"
grep -rn -i -- "$PATTERN" "$SEARCH_DIR" --include="*.md" | head -50

# Search agent files
echo ""
echo "--- AGENT FILES ---"
grep -rn -i -- "$PATTERN" "${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}" --include="*.md" | head -30

echo ""
echo "=== Search complete ==="