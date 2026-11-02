#!/bin/bash
# Destiny Grimoire - Master Audit (All Checks)
ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")" && pwd)}"
echo "============================================================"
echo "  DESTINY GRIMOIRE - MASTER AUDIT (ALL CHECKS)"
echo "============================================================"
echo ""
PASS=0; FAIL=0
run() {
    if bash "$1" >/dev/null 2>&1; then echo "  ✓ [$2] PASS"; PASS=$((PASS+1));
    else echo "  ✗ [$2] FAIL"; FAIL=$((FAIL+1)); fi
}
run "$ARCHIVE/tests/test-db.sh" "Database Integrity"
run "$ARCHIVE/tests/compendium-check.sh" "Compendium Files"
run "$ARCHIVE/tests/lore-integrity.sh" "Lore Archive Integrity"
echo ""
echo "============================================================"
echo "  SCORECARD: $PASS / $((PASS+FAIL)) SUITES PASSED ($FAIL failed)"
echo "============================================================"
[ "$FAIL" -eq 0 ]
