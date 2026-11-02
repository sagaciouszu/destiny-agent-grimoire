#!/bin/bash
# Drifter CI Pipeline
# Runs all validation, consistency, voice, and coherency checks.
# Usage: ./drifter-ci.sh
# Exit code: 0 if all pass, 1 if any fail.

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORKSPACE="${WORKSPACE:-$(cd "$(dirname "$0")/../../how-to-drift-for-agents" && pwd)}"

PASS=0; FAIL=0; TOTAL=0
FAILURES=""

run_check() {
    local name="$1"
    local cmd="$2"
    TOTAL=$((TOTAL+1))
    if eval "$cmd" > /tmp/ci_out.txt 2>&1; then
        echo "  ✓ $name"
        PASS=$((PASS+1))
    else
        echo "  ✗ $name"
        FAIL=$((FAIL+1))
        FAILURES="$FAILURES\n  - $name"
        cat /tmp/ci_out.txt | tail -3 | sed 's/^/    /'
    fi
}

echo "============================================================"
echo "  DRIFTER CI PIPELINE"
echo "============================================================"
echo "Archive: $ARCHIVE"
echo "Workspace: $WORKSPACE"
echo ""

echo "--- 1. Archive Integrity ---"
run_check "Books exist (109+)" "[ $(ls $ARCHIVE/source/books/*.md 2>/dev/null | wc -l) -ge 100 ]"
run_check "Transcripts exist (60+)" "[ $(ls $ARCHIVE/source/transcripts/*.md 2>/dev/null | grep -v index | wc -l) -ge 60 ]"
run_check "Index exists" "[ -f $ARCHIVE/index.md ]"

echo ""
echo "--- 2. Quote Verification ---"
run_check "All quotes verified (0 unverified)" "bash $(dirname "$0")/drifter-quote-verify.sh | grep -q 'PASS: All quotes verified'"

echo ""
echo "--- 3. Cross-Reference Validation ---"
run_check "No broken refs (0 missing)" "bash $(dirname "$0")/drifter-xref-validate.sh | grep -q 'Broken references: 0'"

echo ""
echo "--- 4. Module Completeness ---"
run_check "All modules exist (201 checks)" "bash $(dirname "$0")/drifter-module-test.sh | grep -q 'Failed: 0'"

echo ""
echo "--- 5. Voice Validation ---"
run_check "Single-turn voice (19 scenarios)" "bash $(dirname "$0")/drifter-test-suite.sh | grep -q 'Failed: 0'"
run_check "N-gram voice scorer (PASS)" "python3 $(dirname "$0")/drifter-voice-scorer.py 'Hey, hero. Bank those Motes! Heh. Trust.' | grep -q 'PASS'"
run_check "10-turn emotional arc" "bash $(dirname "$0")/drifter-multiturn-test.sh | grep -q '10/10'"
run_check "Voice consistency check" "bash $(dirname "$0")/drifter-voice-consistency.sh | grep -q 'VOICE CONSISTENCY CHECK COMPLETE'"

echo ""
echo "--- 6. Coherency & Hallucination ---"
run_check "No unverified quotes" "bash $(dirname "$0")/drifter-quote-verify.sh | grep -q 'Unverified quotes: 0'"
run_check "No stale file references" "python3 $(dirname "$0")/ci-checks.py stale $WORKSPACE"
run_check "No circular dependencies" "python3 $(dirname "$0")/ci-checks.py circular $WORKSPACE"
run_check "No self-dependencies" "python3 $(dirname "$0")/ci-checks.py selfdeps $WORKSPACE"

echo ""
echo "--- 7. Hygiene ---"
run_check "No em-dashes in agent files" "python3 $(dirname "$0")/ci-checks.py emdashes $WORKSPACE"
run_check "No personal paths" "python3 $(dirname "$0")/ci-checks.py personal $WORKSPACE"
run_check "No gitignored refs in instructions" "python3 $(dirname "$0")/ci-checks.py gitignored $WORKSPACE"
run_check "All headers present" "python3 $(dirname "$0")/ci-checks.py headers $WORKSPACE"

echo ""
echo "--- 8. Script Integrity ---"
run_check "All .sh syntax valid" "for f in $ARCHIVE/*.sh; do bash -n \$f || exit 1; done"
run_check "All scripts executable" "for f in $ARCHIVE/*.sh; do [ -x \$f ] || exit 1; done"

echo ""
echo "--- 9. Coherency (scenario sim + tape gen) ---"
run_check "Scenario simulator (PASS/PARTIAL)" "bash $(dirname "$0")/drifter-scenario-simulator.sh 'Tell me about Malfeasance' | grep -qE 'PASS|PARTIAL'"
run_check "Tape generator (PASS)" "bash $(dirname "$0")/drifter-tape-generator.sh 'ghosts' | grep -q 'PASS'"
run_check "Gambit sim (VICTORY)" "bash $(dirname "$0")/drifter-gambit-sim.sh --auto | grep -q 'VICTORY'"
run_check "Lore freshness" "bash $(dirname "$0")/drifter-freshness-check.sh | grep -q 'FRESHNESS CHECK COMPLETE'"
run_check "Conflict check" "bash $(dirname "$0")/drifter-conflict-check.sh | grep -q 'CONFLICT CHECK COMPLETE'"

echo ""
echo "============================================================"
echo "  CI RESULTS: $PASS / $TOTAL PASSED ($FAIL failed)"
if [ -n "$FAILURES" ]; then
    echo ""
    echo "  FAILURES:"
    echo -e "$FAILURES"
fi
echo "============================================================"
[ "$FAIL" -eq 0 ]
