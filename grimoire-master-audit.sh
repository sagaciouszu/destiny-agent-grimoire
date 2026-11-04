#!/bin/bash
# Destiny Grimoire - Master Audit (All Checks)
ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")" && pwd)}"
echo "============================================================"
echo "  DESTINY GRIMOIRE - MASTER AUDIT (ALL CHECKS)"
echo "============================================================"
echo ""
# Bootstrap guard: a clear message beats nine confusing suite failures
if [ ! -f "$ARCHIVE/db/grimoire.db" ]; then
    echo "FATAL: database not built at $ARCHIVE/db/grimoire.db"
    echo "       bootstrap: python3 db/migrate.py (build) or ./setup.sh (prebuilt asset)"
    echo "       see README Quick start"
    exit 1
fi
PASS=0; FAIL=0; SKIP=0
run() {
    if bash "$1" >/dev/null 2>&1; then echo "  ✓ [$2] PASS"; PASS=$((PASS+1));
    else echo "  ✗ [$2] FAIL"; FAIL=$((FAIL+1)); fi
}
run "$ARCHIVE/tests/test-db.sh" "Database Integrity (50 checks)"
run "$ARCHIVE/tests/compendium-check.sh" "Compendium Files"
run "$ARCHIVE/tests/lore-integrity.sh" "Lore Archive Integrity"
run "$ARCHIVE/tests/cutscene-verify.sh" "Cutscene Caption Verification"
run "$ARCHIVE/tests/query-interface-test.sh" "Query Interface (80 checks)"
run "$ARCHIVE/tests/agent-layout-test.sh" "Agent Layout (OpenCode/OpenClaw)"
if python3 "$ARCHIVE/tests/conformance.py" >/dev/null 2>&1; then echo "  ✓ [File Conformance (all 3 repos)] PASS"; PASS=$((PASS+1)); else echo "  ✗ [File Conformance (all 3 repos)] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/source-overlap-verify.py" >/dev/null 2>&1; then echo "  ✓ [Source Overlap vs Live] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Source Overlap vs Live] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/speaker-audit.py" >/dev/null 2>&1; then echo "  ✓ [Speaker Noise Gate] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Speaker Noise Gate] FAIL"; FAIL=$((FAIL+1)); fi
echo ""
echo "============================================================"
echo "  SCORECARD: $PASS / $((PASS+FAIL)) SUITES PASSED ($FAIL failed, $SKIP skipped)"
echo "============================================================"
[ "$FAIL" -eq 0 ]
