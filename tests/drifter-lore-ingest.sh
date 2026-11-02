#!/bin/bash
# Drifter Lore Ingestion Script
# Scrapes new Ishtar Collective content and adds it to the archive.
# Usage: ./drifter-lore-ingest.sh <url> <output-slug>
#
# Example: ./drifter-lore-ingest.sh "https://www.ishtar-collective.net/entries/..." "new-entry"

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
URL="$1"
SLUG="$2"

if [ -z "$URL" ] || [ -z "$SLUG" ]; then
    echo "Usage: $0 <url> <output-slug>"
    echo "Example: $0 'https://www.ishtar-collective.net/entries/...' 'new-entry'"
    exit 1
fi

OUTPUT="$ARCHIVE/source/transcripts/$SLUG.md"

echo "=== DRIFTER LORE INGESTION ==="
echo "URL: $URL"
echo "Output: $OUTPUT"
echo ""

# Fetch content using curl
echo "Fetching..."
CONTENT=$(curl -s -L "$URL" 2>/dev/null)

if [ -z "$CONTENT" ]; then
    echo "ERROR: Failed to fetch content from $URL"
    exit 1
fi

# Check if it's a transcript page
if echo "$CONTENT" | grep -q "transcript"; then
    echo "Detected transcript page."
    # Extract Drifter dialogue lines
    echo "$CONTENT" | grep -i "drifter" | head -20
else
    echo "Not a transcript page. Saving raw content."
fi

# Save to file
echo "# Ingested: $SLUG" > "$OUTPUT"
echo "" >> "$OUTPUT"
echo "Source: $URL" >> "$OUTPUT"
echo "Ingested: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$OUTPUT"
echo "" >> "$OUTPUT"
echo "## Raw Content" >> "$OUTPUT"
echo "$CONTENT" | head -100 >> "$OUTPUT"

echo ""
echo "Saved to $OUTPUT"
echo "Next: review the file, extract Drifter dialogue, and add to source/transcripts/index.md"
echo "=== INGESTION COMPLETE ==="
