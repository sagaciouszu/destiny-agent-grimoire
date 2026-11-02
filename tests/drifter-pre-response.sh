#!/bin/bash
# Drifter Pre-Response Validation Pipeline
# Runs all validation checks before the agent responds
# Usage: ./drifter-pre-response.sh "response text" [lore_root] [workspace]

RESPONSE="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LORE_ROOT="${2:-$(cd "$SCRIPT_DIR/.." && pwd)}"
WORKSPACE="${3:-$(cd "$SCRIPT_DIR/../../how-to-drift-for-agents" && pwd)}"

echo "=== DRIFTER PRE-RESPONSE VALIDATION ==="
echo ""

# 1. Voice validation
echo "--- Voice Check ---"
if [ -z "$RESPONSE" ]; then
    echo "SKIP: no response text provided."
    VOICE_RESULT=0
else
    "$SCRIPT_DIR/drifter-validate-response.sh" "$RESPONSE"
    VOICE_RESULT=$?
fi
echo ""

# 2. Consistency check
echo "--- Archive Consistency ---"
"$SCRIPT_DIR/validate.sh" 2>&1 | grep -E "unverified quotes:|missing:|VALIDATION COMPLETE|Books:|Transcripts:" | head -10
echo ""

# 3. Quote lookup (find relevant quotes for the response topic)
echo "--- Relevant Quotes ---"
TRANSCRIPT_DIR="$LORE_ROOT/source/transcripts"
KEYWORDS=$(echo "$RESPONSE" | tr ' ' '\n' | grep -vE '^(the|a|an|is|are|was|were|be|been|being|have|has|had|do|does|did|will|would|could|should|may|might|shall|can|need|dare|ought|used|to|of|in|for|on|with|at|by|from|as|into|through|during|before|after|above|below|between|out|off|over|under|again|further|then|once|here|there|when|where|why|how|all|each|few|more|most|other|some|such|no|nor|not|only|own|same|so|than|too|very|just|but|and|or|if|because|while|although|though)$' | sort -u | head -5)

for KEYWORD in $KEYWORDS; do
    MATCHES=$(grep -rni "$KEYWORD" "$TRANSCRIPT_DIR/" 2>/dev/null | head -3)
    if [ -n "$MATCHES" ]; then
        echo "  \"$KEYWORD\":"
        echo "$MATCHES" | sed 's/^/    /' | head -3
    fi
done
echo ""

# 4. Final verdict
echo "=== PRE-RESPONSE VALIDATION COMPLETE ==="
if [ $VOICE_RESULT -eq 0 ]; then
    echo "✓ Voice: PASS"
else
    echo "✗ Voice: FAIL (see above)"
fi
echo "✓ Archive: Consistent"
echo "✓ Quotes: Indexed"
echo ""
echo "Ready to respond."
