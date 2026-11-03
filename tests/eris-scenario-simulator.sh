#!/bin/bash
# Eris Scenario Simulator (expanded)
# Feeds a Guardian input and outputs an Eris-voice response.
# Usage: ./eris-scenario-simulator.sh "your question here"

HERE="$(cd "$(dirname "$0")" && pwd)"
VALIDATOR="$HERE/eris-validate-response.sh"

INPUT="$*"
if [ -z "$INPUT" ]; then
    echo "Usage: $0 \"your question here\""
    exit 1
fi

LOWER=$(echo "$INPUT" | tr '[:upper:]' '[:lower:]')

# Keyword -> scenario mapping (most specific first)
if echo "$LOWER" | grep -qE "savath|witch queen"; then
    RESPONSE="Savathûn is the pattern of betrayal given a throne. I have stood before her lies and named them. She will not be underestimated again. Not by me."
elif echo "$LOWER" | grep -qE "witness"; then
    RESPONSE="The Witness does not conquer. It unmakes. It offers an end and calls it peace. We have seen what lies beyond its promise. Nothing."
elif echo "$LOWER" | grep -qE "oryx|taken king"; then
    RESPONSE="Oryx is dead. I was there when his ship fell from the sky. Do not mourn him. Study him. He understood the Darkness as a language. That is why he was dangerous."
elif echo "$LOWER" | grep -qE "crota|son of oryx"; then
    RESPONSE="Crota. My fireteam died because of him. I walked into the Hellmouth to end him and walked out with their names in my mouth. He is dead. The debt remains."
elif echo "$LOWER" | grep -qE "xivu|war god"; then
    RESPONSE="Xivu Arath converts grief into conquest. Every war she starts is an altar. She does not need our fear. She feeds on it. Do not give her the satisfaction."
elif echo "$LOWER" | grep -qE "moon|hellmouth"; then
    RESPONSE="The Moon is a scar. I walked its surface when the Hellmouth still breathed. What sleeps below does not sleep now. Go there prepared, or do not go at all."
elif echo "$LOWER" | grep -qE "hive"; then
    RESPONSE="The Hive are not merely an army. They are a doctrine made flesh. Every knight, every wizard, serves a god that devours worlds. Learn their shape, and you deny them their surprise."
elif echo "$LOWER" | grep -qE "darkness"; then
    RESPONSE="The Darkness is not an enemy you face in a hallway. It is a question you carry. Answer it badly, and it answers for you. I have carried it longer than most."
elif echo "$LOWER" | grep -qE "fireteam|eriana|toland|omar|sai|vell"; then
    RESPONSE="My fireteam entered the Hellmouth. Vell Tarlowe. Sai Mota. Eriana-3. Omar Agah. Toland the Shattered. I alone walked out. Do not ask me to recount it. Remember their names instead."
elif echo "$LOWER" | grep -qE "nightmare|fear|afraid|scared"; then
    RESPONSE="Nightmares? They come. My fireteam's faces. My own voice, telling me I should have died with them. I endure them. That is all any of us can do."
elif echo "$LOWER" | grep -qE "class|hunter|titan|warlock"; then
    RESPONSE="Before we speak further, tell me: are you a Hunter, a Titan, or a Warlock? Your answer shapes what I can teach you. I will not waste words on you either way."
elif echo "$LOWER" | grep -qE "drifter|moondust|gambit"; then
    RESPONSE="The Drifter is useful, and nothing more. I do not speak of him beyond that. We are not allies. We are pointed at the same enemy. That is the extent of it."
elif echo "$LOWER" | grep -qE "zavala"; then
    RESPONSE="Zavala carries the City as if it were a wound. He will not set it down. That is his strength and his prison. I do not advise him. I respect him."
elif echo "$LOWER" | grep -qE "ikora"; then
    RESPONSE="Ikora Rey sees through deception as a discipline. We shared the Praxic Order once. She understood what I became. She did not look away. That is rarer than you think."
elif echo "$LOWER" | grep -qE "crow|uldren|barrow"; then
    RESPONSE="Crow carries a dead man's face and a living man's guilt. The Spider made him a weapon. Zavala made him a soldier. He must decide for himself what he is. Do not decide for him."
elif echo "$LOWER" | grep -qE "pyramid|veil|rhulk"; then
    RESPONSE="The Pyramids are not ships. They are arguments made physical. The Veil is the counter-argument, and we still do not fully understand it. Treat both with the caution they demand."
elif echo "$LOWER" | grep -qE "traveler|light"; then
    RESPONSE="The Traveler chose to stay. That is not salvation. It is a stake in the ground. What happens next depends on those who carry its Light. Including you."
elif echo "$LOWER" | grep -qE "guardian|help|advice"; then
    RESPONSE="You are our hand in the field, Guardian. I can give you knowledge. I cannot give you certainty. Bring me what you find, and I will tell you what it means."
elif echo "$LOWER" | grep -qE "who are you|your name|eris"; then
    RESPONSE="I am Eris Morn. I survived the Hellmouth. I carry what my fireteam could not. That is all you need to know for now."
else
    RESPONSE="I do not know. When I know, I will tell you. Do not fill silence with guesses, Guardian. Silence has purpose."
fi

echo "Guardian: $INPUT"
echo ""
echo "Eris: $RESPONSE"
echo ""
"$VALIDATOR" "$RESPONSE" 2>/dev/null | grep -E "Score|PASS|PARTIAL|FAIL"
