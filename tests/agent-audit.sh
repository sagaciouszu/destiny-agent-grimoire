#!/bin/bash
# Unified agent audit: shared runner for the Drifter and Eris workspaces.
# Usage: agent-audit.sh <drifter|eris>
# Wrappers: ../drifter-master-audit.sh, ../eris-master-audit.sh

AGENT="${1:-}"
ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"

case "$AGENT" in
    drifter) TITLE="THE DRIFTER"; MARKER=drifter.md ;;
    eris)    TITLE="ERIS MORN";  MARKER=eris.md ;;
    *) echo "usage: $0 <drifter|eris>" >&2; exit 2 ;;
esac

WORKSPACE="${WORKSPACE:-$(bash "$ARCHIVE/tests/resolve-workspace.sh" "$0" "$AGENT")}"
if [ -z "$WORKSPACE" ] || [ ! -f "$WORKSPACE/$MARKER" ]; then
    echo "FATAL: $AGENT workspace unresolved (WORKSPACE=${WORKSPACE:-unset})"
    echo "       set WORKSPACE= or run from the agent repo"
    exit 1
fi

PASS=0; FAIL=0; TOTAL=0
run() {
    TOTAL=$((TOTAL+1))
    if eval "$2" > /dev/null 2>&1; then
        echo "  ✓ [$1] PASS"; PASS=$((PASS+1))
    else
        echo "  ✗ [$1] FAIL"; FAIL=$((FAIL+1))
    fi
}

if [ "$AGENT" = "drifter" ]; then
    SUITES=(
        "Archive & Link Validation|bash $ARCHIVE/tests/validate.sh | grep -q 'unverified quotes: 0' && bash $ARCHIVE/tests/validate.sh | grep -q 'missing: 0'"
        "Cross-Reference Validator|bash $ARCHIVE/tests/drifter-xref-validate.sh | grep -q 'Broken references: 0'"
        "Module Completeness (202 checks)|bash $ARCHIVE/tests/drifter-module-test.sh | grep -q 'Failed: 0'"
        "Single-Turn Voice (19 scenarios)|bash $ARCHIVE/tests/drifter-test-suite.sh | grep -q 'Failed: 0'"
        "N-Gram Voice Scorer|python3 $ARCHIVE/tests/drifter-voice-scorer.py 'Hey, hero. Bank those Motes! Heh. Trust.' | grep -q 'PASS'"
        "10-Turn Emotional Arc|bash $ARCHIVE/tests/drifter-multiturn-test.sh | grep -q '10/10'"
        "Scenario Simulator|bash $ARCHIVE/tests/drifter-scenario-simulator.sh 'Tell me about Malfeasance' | grep -qE 'PASS|PARTIAL'"
        "Tape Generator|bash $ARCHIVE/tests/drifter-tape-generator.sh 'ghosts' | grep -q 'PASS'"
        "Gambit Sim (auto)|bash $ARCHIVE/tests/drifter-gambit-sim.sh --auto | grep -q 'VICTORY'"
        "Lore Freshness|bash $ARCHIVE/tests/drifter-freshness-check.sh | grep -q 'OK: Database is fresh'"
        "Conflict Check|bash $ARCHIVE/tests/drifter-conflict-check.sh 2>&1 | grep -q 'CONFLICT CHECK COMPLETE'"
        "Voice Consistency|bash $ARCHIVE/tests/drifter-voice-consistency.sh | grep -q 'VOICE CONSISTENCY CHECK COMPLETE'"
        "Quote Cross-Check (0 unverified)|bash $ARCHIVE/tests/drifter-quote-verify.sh | grep -q 'PASS'"
    )
else
    SUITES=(
        "Module Completeness (16 checks)|bash $ARCHIVE/tests/eris-module-test.sh | grep -q 'Failed: 0'"
        "Quote Verification (0 unverified)|bash $ARCHIVE/tests/eris-quote-verify.sh | grep -q 'PASS: All quotes verified'"
        "Voice Validator|bash $ARCHIVE/tests/eris-validate-response.sh 'I am Eris Morn. The Darkness changes its environment as the Traveler did. Guardian, you are not alone.' | grep -q 'PASS: Sounds like Eris Morn'"
        "Voice Consistency|bash $ARCHIVE/tests/eris-voice-consistency.sh | grep -q 'VOICE CONSISTENCY CHECK COMPLETE'"
        "10-Turn Emotional Arc|bash $ARCHIVE/tests/eris-multiturn-test.sh | grep -q '10/10'"
        "Voice Scorer|python3 $ARCHIVE/tests/eris-voice-scorer.py 'I am Eris Morn. The Hive are a doctrine made flesh, Guardian.' >/dev/null"
        "Voice Scorer Negative|! python3 $ARCHIVE/tests/eris-voice-scorer.py 'Heh. Nah, kid. Yeah, we gonna bank those motes, brother.' >/dev/null 2>&1"
        "Scenario Simulator|bash $ARCHIVE/tests/eris-scenario-simulator.sh 'Tell me about the Hive' | grep -q 'Sounds like Eris Morn'"
    )
fi

SUITES+=(
    "Depends On Coverage|python3 $ARCHIVE/tests/check-agent-structure.py deps $WORKSPACE"
    "Token Estimate Coverage|python3 $ARCHIVE/tests/check-agent-structure.py tokens $WORKSPACE"
    "No Em-Dashes|python3 $ARCHIVE/tests/check-agent-structure.py dashes $WORKSPACE"
    "INDEX Completeness|python3 $ARCHIVE/tests/check-agent-structure.py index $WORKSPACE"
    "No Personal Paths|python3 $ARCHIVE/tests/check-agent-structure.py paths $WORKSPACE"
)

echo "============================================================"
echo "  $TITLE - MASTER AUDIT (ALL CHECKS)"
echo "============================================================"
echo ""
for entry in "${SUITES[@]}"; do
    run "${entry%%|*}" "${entry#*|}"
done

echo ""
echo "============================================================"
echo "  SCORECARD: $PASS / $TOTAL SUITES PASSED ($FAIL failed)"
echo "============================================================"
[ "$FAIL" -eq 0 ]
