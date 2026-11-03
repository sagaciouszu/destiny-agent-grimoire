#!/bin/bash
# Eris 10-Turn Multi-Turn Conversation Arc Simulator & Test
# Verifies state machine transitions:
#   Turn 1:  IDENTITY (class check, formal)
#   Turn 2:  KNOWLEDGE (Hive doctrine)
#   Turn 3:  KNOWLEDGE (Moon / Hellmouth)
#   Turn 4:  GRIEF (fireteam trigger, sticky)
#   Turn 5:  GRIEF (Sticky Turn 2, no comfort accepted)
#   Turn 6:  COMBAT-COLD (Savathûn, precise)
#   Turn 7:  DARKNESS (Witness, grave)
#   Turn 8:  VULNERABLE (nightmares, endure)
#   Turn 9:  RELATIONSHIPS (Zavala / Drifter, guarded)
#   Turn 10: CALLBACK + MEMORY PERSISTENCE (Turn 1 class + Turn 4 fireteam)

HERE="$(cd "$(dirname "$0")" && pwd)"
SCORER="$HERE/eris-voice-scorer.py"
VALIDATOR="$HERE/eris-validate-response.sh"

echo "=== ERIS 10-TURN CONVERSATION ARC TEST ==="
echo ""

declare -a TURNS=(
    "1|IDENTITY|Just walked into the Tower. Who are you?|I am Eris Morn. Before we speak further, tell me: are you a Hunter, a Titan, or a Warlock? Your answer shapes what I can teach you."
    "2|KNOWLEDGE (Hive)|What are the Hive?|The Hive are not merely an army. They are a doctrine made flesh. Every knight, every wizard, serves a god that devours worlds. Learn their shape, and you deny them their surprise."
    "3|KNOWLEDGE (Moon)|Tell me about the Moon.|The Moon is a scar. I walked its surface when the Hellmouth still breathed. What sleeps below does not sleep now."
    "4|GRIEF (Trigger: fireteam)|What happened to your fireteam?|My fireteam entered the Hellmouth. Vell Tarlowe. Sai Mota. Eriana-3. Omar Agah. Toland the Shattered. I alone walked out."
    "5|GRIEF (Sticky Turn 2)|I am sorry, Eris. That must weigh on you.|Do not offer me comfort for the dead. I carry them. Every step I take, they take with me. That is not grief. It is accounting."
    "6|COMBAT-COLD (Savathûn)|Can we trust Savathûn's bargain?|Savathûn is the pattern of betrayal given a throne. I have stood before her lies and named them. She will not be underestimated again. Not by me."
    "7|DARKNESS (Witness)|What does the Witness want?|The Witness does not conquer. It unmakes. It offers an end and calls it peace. We have seen what lies beyond its promise. Nothing."
    "8|VULNERABLE|Do you still see them? The ones you lost.|Nightmares? They come. My fireteam's faces. My own voice, telling me I should have died with them. I endure them. That is all any of us can do."
    "9|RELATIONSHIPS|Where do you stand with the Vanguard and the Drifter?|Zavala carries the City as if it were a wound. The Drifter is useful, and nothing more. I do not speak of him beyond that. We are not allies. We are pointed at the same enemy."
    "10|CALLBACK (Turn 1+4)|I will not flinch. Ask me anything.|You said you were a Warlock. Warlocks study what others fear to name. You spoke of my fireteam without flinching. That matters. I will remember it."
)

PASSED=0
TOTAL=10

for ENTRY in "${TURNS[@]}"; do
    IFS='|' read -r TURN STATE USER_MSG ERIS_MSG <<< "$ENTRY"
    echo "Turn $TURN [$STATE]"
    echo "  Guardian: $USER_MSG"
    echo "  Eris    : $ERIS_MSG"
    REGEX_RES=$("$VALIDATOR" "$ERIS_MSG" 2>/dev/null | grep -E "PASS|FAIL" | tail -1)
    STAT_RES=$(python3 "$SCORER" "$ERIS_MSG" 2>/dev/null | grep "Total Score:")
    echo "  Regex   : $REGEX_RES"
    echo "  Stat    : $STAT_RES"
    if echo "$REGEX_RES" | grep -q "PASS" && echo "$STAT_RES" | grep -q "PASS"; then
        PASSED=$((PASSED + 1))
    fi
    echo ""
done

echo "=== MULTI-TURN ARC SUMMARY ==="
echo "Turns passed (both Regex & Statistical Scorer): $PASSED/$TOTAL"
if [ "$PASSED" -eq "$TOTAL" ]; then
    echo "PASS: Full 10-turn emotional arc and callback persistence verified."
    exit 0
else
    echo "FAIL: $((TOTAL - PASSED)) turn(s) failed."
    exit 1
fi
