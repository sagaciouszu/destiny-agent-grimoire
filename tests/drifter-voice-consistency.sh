#!/bin/bash
# Drifter Voice Consistency Check
# Scans all Drifter-attributed quotes for non-Drifter speech patterns.
# Usage: ./drifter-voice-consistency.sh

WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"
echo "=== DRIFTER VOICE CONSISTENCY CHECK ==="
echo ""

# Check for "haha" instead of "heh"
echo "--- 'haha' instead of 'heh' ---"
grep -rn "haha" "$WORKSPACE" 2>/dev/null | grep -v "Naw, haha" | head -5
echo "(none if empty = good)"
echo ""

# Check for "yes" instead of "yeah" in Drifter quotes
echo "--- 'yes' instead of 'yeah' ---"
grep -rn '"[^"]*[^"]yes[^"]*"' "$WORKSPACE" 2>/dev/null | grep -iv "yesterday\|yes," | head -5
echo "(manual review needed)"
echo ""

# Check for "no" instead of "nah" in short Drifter quotes
echo "--- 'no.' instead of 'nah.' ---"
grep -rn '"No\."' "$WORKSPACE" 2>/dev/null | head -5
echo "(none if empty = good)"
echo ""

# Check for "I am" instead of "I'm" in Drifter quotes
echo "--- 'I am' instead of 'I'm' ---"
grep -rn '"[^"]*I am [^"]*"' "$WORKSPACE" 2>/dev/null | head -5
echo "(manual review needed)"
echo ""

# Check for "do not" instead of "don't"
echo "--- 'do not' instead of 'don't' ---"
grep -rn '"[^"]*do not [^"]*"' "$WORKSPACE" 2>/dev/null | head -5
echo "(manual review needed)"
echo ""

echo "=== VOICE CONSISTENCY CHECK COMPLETE ==="
