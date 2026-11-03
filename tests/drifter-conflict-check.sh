#!/bin/bash
# Drifter Conflict Detector
# Scans all agent files for contradictory statements.
# Usage: ./drifter-conflict-check.sh

WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"
echo "=== DRIFTER CONFLICT CHECK ==="
echo ""

# Check for Eris alive/dead contradictions
echo "--- Eris Status ---"
grep -rn "Eris is alive\|Eris lives\|Eris survived" "$WORKSPACE" 2>/dev/null | head -3
grep -rn "Eris is dead\|Eris died\|she's dead.*Eris\|Eris.*dead" "$WORKSPACE" 2>/dev/null | head -3
echo "(manual review needed)"
echo ""

# Check for Cayde alive/dead
echo "--- Cayde Status ---"
grep -rn "Cayde is alive\|Cayde lives" "$WORKSPACE" 2>/dev/null | head -3
grep -rn "Cayde is dead\|Cayde's dead\|Cayde died" "$WORKSPACE" 2>/dev/null | head -3
echo ""

# Check for Orin status
echo "--- Orin/Emissary Status ---"
grep -rn "Orin is dead\|Orin died" "$WORKSPACE" 2>/dev/null | head -3
grep -rn "Orin is alive\|Orin lives\|Orin became\|Emissary" "$WORKSPACE" 2>/dev/null | head -3
echo ""

# Check for "I make my own choices" (unverified, should not appear)
echo "--- Unverified Quote Check ---"
_m=$(grep -rn "I make my own choices" "$WORKSPACE" 2>/dev/null | grep -v "NOT FOUND\|removed\|unverified\|(unverified)\|Landing\|biting off")
if [ -n "$_m" ]; then
    echo "$_m" | head -3
    echo "WARNING: Unverified quote found!"
else
    echo "OK: No unverified 'I make my own choices' quotes."
fi
echo ""

# Check for "Function: Go all in" (unverified)
_m=$(grep -rn "Function: Go all in" "$WORKSPACE" 2>/dev/null | grep -v "NOT FOUND\|removed\|unverified\|(unverified)")
if [ -n "$_m" ]; then
    echo "$_m" | head -3
    echo "WARNING: Unverified quote found!"
else
    echo "OK: No unverified 'Function: Go all in' quotes."
fi
echo ""

# Check for "He has lost before" (unverified narration)
_m=$(grep -rn "He has lost before" "$WORKSPACE" 2>/dev/null | grep -v "NOT FOUND\|removed\|unverified\|narration\|(unverified)")
if [ -n "$_m" ]; then
    echo "$_m" | head -3
    echo "WARNING: Unverified quote found!"
else
    echo "OK: No unverified 'He has lost before' quotes."
fi
echo ""

# Check for "The night falls" (Emissary, not Drifter)
_m=$(grep -rn "The night falls" "$WORKSPACE" 2>/dev/null | grep -iv "NOT FOUND\|removed\|unverified\|emissary\|nine\|warning")
if [ -n "$_m" ]; then
    echo "$_m" | head -3
    echo "WARNING: Emissary quote may be attributed to Drifter!"
else
    echo "OK: No Emissary 'night falls' quotes attributed to Drifter."
fi
echo ""

echo "=== CONFLICT CHECK COMPLETE ==="
