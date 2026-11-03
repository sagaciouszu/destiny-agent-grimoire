#!/bin/bash
# YouTube Transcript Extractor
# Uses yt-dlp to extract transcripts/subtitles from YouTube videos
# Usage: ./yt-transcript.sh <video_url_or_id> [output_file]

VIDEO="$1"
OUTPUT="${2:-}"
LANG="${3:-en}"

if [ -z "$VIDEO" ]; then
    echo "Usage: $0 <video_url_or_id> [output_file] [language]"
    echo ""
    echo "Examples:"
    echo "  $0 'https://www.youtube.com/watch?v=abc123'"
    echo "  $0 'abc123' /tmp/transcript.txt"
    echo "  $0 'abc123' '' 'en'"
    echo ""
    echo "Extracts transcripts/subtitles from YouTube videos using yt-dlp."
    echo "Supports both manual and auto-generated captions."
    exit 1
fi

# Convert video ID to URL if needed
if [[ "$VIDEO" != http* ]]; then
    VIDEO="https://www.youtube.com/watch?v=$VIDEO"
fi

TMPDIR=$(mktemp -d)
cd "$TMPDIR" || exit 1

echo "Extracting transcript from: $VIDEO"
echo "Language: $LANG"
echo ""

# Try to get subtitles (manual first, then auto-generated)
yt-dlp --write-sub --write-auto-sub --sub-lang "$LANG" --skip-download --sub-format vtt -o "transcript" "$VIDEO" 2>&1 | tail -5

# Find the subtitle file
SUBFILE=$(ls transcript*.vtt 2>/dev/null | head -1)

if [ -z "$SUBFILE" ]; then
    echo "No subtitles found for this video."
    echo "The video may not have captions available."
    rm -rf "$TMPDIR"
    exit 1
fi

# Convert VTT to plain text (strip timestamps and tags)
TMP_CLEAN="$(mktemp)"
python3 - "$SUBFILE" > "$TMP_CLEAN" <<'PYEOF'

import re, sys
with open(sys.argv[1], 'r') as f:
    content = f.read()
# Remove VTT header
content = re.sub(r'WEBVTT.*?\n\n', '', content, flags=re.DOTALL)
# Remove timestamp lines
content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*\n', '', content)
# Remove tags
content = re.sub(r'<[^>]+>', '', content)
# Remove empty lines and deduplicate consecutive identical lines
lines = content.split('\n')
result = []
prev = ''
for line in lines:
    line = line.strip()
    if line and line != prev:
        result.append(line)
        prev = line
print('\n'.join(result))
PYEOF

if [ -n "$OUTPUT" ]; then
    cp "$TMP_CLEAN" "$OUTPUT" && rm -f "$TMP_CLEAN"
    echo "Transcript saved to: $OUTPUT"
else
    cat "$TMP_CLEAN"
    rm -f "$TMP_CLEAN"
fi

# Cleanup
rm -rf "$TMPDIR"
echo ""
echo "=== Extraction complete ==="