#!/bin/bash
# Batch YouTube Transcript Extractor
# Processes multiple YouTube videos and saves transcripts
# Usage: ./yt-batch.sh <url1> <url2> ... OR ./yt-batch.sh --file urls.txt

OUTPUT_DIR="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}/source/transcripts"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$1" = "--file" ] && [ -n "$2" ]; then
    URLS=$(cat "$2")
else
    URLS="$@"
fi

if [ -z "$URLS" ]; then
    echo "Usage: $0 <url1> <url2> ... OR $0 --file urls.txt"
    echo "Batch extracts transcripts from multiple YouTube videos."
    exit 1
fi

COUNT=0
for URL in $URLS; do
    COUNT=$((COUNT + 1))
    echo "=== Processing video $COUNT: $URL ==="
    VIDEO_ID=$(echo "$URL" | sed -n 's/.*[?&]v=\([^&]*\).*/\1/p; s/.*youtu\.be\/\([^?]*\).*/\1/p')
    if [ -z "$VIDEO_ID" ]; then
        VIDEO_ID="$URL"
    fi
    OUTPUT="$OUTPUT_DIR/yt-$VIDEO_ID-transcript.txt"
    "$SCRIPT_DIR/yt-transcript.sh" "$URL" "$OUTPUT" 2>&1 | tail -3
    echo "Saved to: $OUTPUT"
    echo ""
done

echo "=== Batch complete: $COUNT videos processed ==="