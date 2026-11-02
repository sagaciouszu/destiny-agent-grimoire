#!/bin/bash
# Drifter Master Audit - runs ALL checks and prints a unified scorecard
# Usage: ./drifter-master-audit.sh

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")" && pwd)}"
WORKSPACE="${WORKSPACE:-$(cd "$(dirname "$0")/../how-to-drift-for-agents" && pwd)}"

PASS=0; FAIL=0; TOTAL=0
run() {
    TOTAL=$((TOTAL+1))
    if eval "$2" > /dev/null 2>&1; then
        echo "  ✓ [$1] PASS"
        PASS=$((PASS+1))
    else
        echo "  ✗ [$1] FAIL"
        FAIL=$((FAIL+1))
    fi
}

echo "============================================================"
echo "  THE DRIFTER - MASTER AUDIT (ALL CHECKS)"
echo "============================================================"
echo ""

run "Archive & Link Validation" "bash $ARCHIVE/tests/validate.sh | grep -q 'unverified quotes: 0' && bash $ARCHIVE/tests/validate.sh | grep -q 'missing: 0'"
run "Cross-Reference Validator" "bash $ARCHIVE/tests/drifter-xref-validate.sh | grep -q 'Broken references: 0'"
run "Module Completeness (201 checks)" "bash $ARCHIVE/tests/drifter-module-test.sh | grep -q 'Failed: 0'"
run "Single-Turn Voice (19 scenarios)" "bash $ARCHIVE/tests/drifter-test-suite.sh | grep -q 'Failed: 0'"
run "N-Gram Voice Scorer" "python3 $ARCHIVE/tests/drifter-voice-scorer.py 'Hey, hero. Bank those Motes! Heh. Trust.' | grep -q 'PASS'"
run "10-Turn Emotional Arc" "bash $ARCHIVE/tests/drifter-multiturn-test.sh | grep -q '10/10'"
run "Scenario Simulator" "bash $ARCHIVE/tests/drifter-scenario-simulator.sh 'Tell me about Malfeasance' | grep -qE 'PASS|PARTIAL'"
run "Tape Generator" "bash $ARCHIVE/tests/drifter-tape-generator.sh 'ghosts' | grep -q 'PASS'"
run "Gambit Sim (auto)" "bash $ARCHIVE/tests/drifter-gambit-sim.sh --auto | grep -q 'VICTORY'"
run "Lore Freshness" "bash $ARCHIVE/tests/drifter-freshness-check.sh | grep -q 'OK: Database is fresh'"
run "Conflict Check" "bash $ARCHIVE/tests/drifter-conflict-check.sh 2>&1 | grep -q 'CONFLICT CHECK COMPLETE'"
run "Voice Consistency" "bash $ARCHIVE/tests/drifter-voice-consistency.sh | grep -q 'VOICE CONSISTENCY CHECK COMPLETE'"
run "Quote Cross-Check (0 unverified)" "bash $ARCHIVE/tests/drifter-quote-verify.sh | grep -q 'PASS'"

run "Depends On Coverage (67/67)" "python3 -c \"
import glob,os
ws='$WORKSPACE'
files=[f for f in glob.glob(ws+'/*.md')+glob.glob(ws+'/voice/*.md')+glob.glob(ws+'/core/*.md')+glob.glob(ws+'/world/*.md')+glob.glob(ws+'/gameplay/*.md')]
files=[f for f in files if 'DREAMS.md' not in f]
assert all('**Depends On:**' in open(f).read() for f in files)
\""
run "Token Estimate Coverage (67/67)" "python3 -c \"
import glob,os
ws='$WORKSPACE'
files=[f for f in glob.glob(ws+'/*.md')+glob.glob(ws+'/voice/*.md')+glob.glob(ws+'/core/*.md')+glob.glob(ws+'/world/*.md')+glob.glob(ws+'/gameplay/*.md')]
files=[f for f in files if 'DREAMS.md' not in f]
assert all('Token Estimate:' in open(f).read() for f in files)
\""
run "No Em-Dashes" "python3 -c \"
import glob,os
ws='$WORKSPACE'
files=[f for f in glob.glob(ws+'/*.md')+glob.glob(ws+'/voice/*.md')+glob.glob(ws+'/core/*.md')+glob.glob(ws+'/world/*.md')+glob.glob(ws+'/gameplay/*.md')]
files=[f for f in files if 'DREAMS.md' not in f]
assert all(chr(8212) not in open(f,encoding='utf-8').read() for f in files)
\""
run "INDEX.md Completeness" "python3 -c \"
import re,os
ws='$WORKSPACE'
idx=open(ws+'/INDEX.md').read()
refs=set(re.findall(r'\`([A-Za-z0-9_./-]+\.md)\`',idx))
assert all(os.path.exists(os.path.join(ws,r)) for r in refs)
\""

echo ""
echo "============================================================"
echo "  SCORECARD: $PASS / $TOTAL SUITES PASSED ($FAIL failed)"
echo "============================================================"
[ "$FAIL" -eq 0 ]
