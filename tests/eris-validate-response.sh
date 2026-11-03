#!/bin/bash
# Eris Response Validator
# Checks if a response sounds authentically like Eris Morn.
# Usage: ./tests/eris-validate-response.sh "response text"

RESPONSE="$1"
if [ -z "$RESPONSE" ]; then
    echo "Usage: $0 \"response text\""
    exit 1
fi

PASS=0; FAIL=0; WARN=0

# Check 1: No Drifter slang
if echo "$RESPONSE" | grep -qiE "heh|nah|yeah|kid|brother|y'know|gotta|nothin'|more'n"; then
    echo "FAIL: Drifter slang detected (heh/nah/yeah/kid/brother)"
    FAIL=$((FAIL+1))
else
    echo "PASS: No Drifter slang"
    PASS=$((PASS+1))
fi

# Check 2: Formal tone (no excessive contractions beyond standard)
# Check 3: No chuckling/laughter
if echo "$RESPONSE" | grep -qiE "\[chuckles\]|\[laughs\]|haha|lol"; then
    echo "FAIL: Laughter detected (Eris does not laugh)"
    FAIL=$((FAIL+1))
else
    echo "PASS: No laughter"
    PASS=$((PASS+1))
fi

# Check 4: Length (should be short, 1-4 sentences)
SENTENCES=$(echo "$RESPONSE" | grep -oE '[.!?]' | wc -l)
if [ "$SENTENCES" -ge 1 ] && [ "$SENTENCES" -le 6 ]; then
    echo "PASS: Sentence count OK ($SENTENCES)"
    PASS=$((PASS+1))
else
    echo "WARN: Sentence count unusual ($SENTENCES)"
    WARN=$((WARN+1))
fi

# Check 5: Contains "Guardian" or formal address (optional but good)
if echo "$RESPONSE" | grep -qi "Guardian\|you"; then
    echo "PASS: Formal address present"
    PASS=$((PASS+1))
else
    echo "WARN: No formal address (Guardian/you)"
    WARN=$((WARN+1))
fi

# Check 6: No "I dig it" or Drifter catchphrases
if echo "$RESPONSE" | grep -qiE "I dig it|I'll be seein'|watch your back, hero|all bets on"; then
    echo "FAIL: Drifter catchphrase detected"
    FAIL=$((FAIL+1))
else
    echo "PASS: No Drifter catchphrases"
    PASS=$((PASS+1))
fi

echo ""
echo "=== VALIDATION COMPLETE ==="
echo "Passed: $PASS | Failed: $FAIL | Warnings: $WARN"
if [ "$FAIL" -eq 0 ]; then
    echo "PASS: Sounds like Eris Morn"
    exit 0
else
    echo "FAIL: Does not sound like Eris Morn"
    exit 1
fi
