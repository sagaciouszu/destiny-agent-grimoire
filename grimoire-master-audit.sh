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
run "$ARCHIVE/tests/test-db.sh" "Database Integrity (68 checks)"
# run() executes a suite with bash, so Python suites are invoked explicitly.
if python3 "$ARCHIVE/tests/caption-test.py" >/dev/null 2>&1; then echo "  ✓ [Game Caption Corpus] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Game Caption Corpus] FAIL"; FAIL=$((FAIL+1)); fi
run "$ARCHIVE/tests/compendium-check.sh" "Compendium Files"
run "$ARCHIVE/tests/lore-integrity.sh" "Lore Archive Integrity"
run "$ARCHIVE/tests/cutscene-verify.sh" "Cutscene Caption Verification"
run "$ARCHIVE/tests/query-interface-test.sh" "Query Interface (98 checks)"
run "$ARCHIVE/tests/agent-layout-test.sh" "Agent Layout (OpenCode/OpenClaw, 108 checks)"
if python3 "$ARCHIVE/tests/conformance.py" >/dev/null 2>&1; then echo "  ✓ [File Conformance] PASS"; PASS=$((PASS+1)); else echo "  ✗ [File Conformance] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/agnostic-test.py" >/dev/null 2>&1; then echo "  ✓ [Agnostic Contract] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Agnostic Contract] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/docs-consistency.py" >/dev/null 2>&1; then echo "  ✓ [Documentation Consistency] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Documentation Consistency] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/agent-access-test.py" >/dev/null 2>&1; then echo "  ✓ [Agent Access] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Agent Access] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/scripts/generate-knowledge-web.py" --check >/dev/null 2>&1; then echo "  ✓ [Knowledge Webs] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Knowledge Webs] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/source-overlap-verify.py" >/dev/null 2>&1; then echo "  ✓ [Source Overlap vs Live] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Source Overlap vs Live] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/speaker-audit.py" >/dev/null 2>&1; then echo "  ✓ [Speaker Noise Gate] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Speaker Noise Gate] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/suite-manifest-test.py" >/dev/null 2>&1; then echo "  ✓ [Agent Suite Manifests] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Agent Suite Manifests] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/mirror-tree-test.py" >/dev/null 2>&1; then echo "  ✓ [Tree Mirror (rsync replacement)] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Tree Mirror (rsync replacement)] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/permission-leak-audit.py" >/dev/null 2>&1; then echo "  ✓ [Peer Permission Leak Audit] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Peer Permission Leak Audit] FAIL"; FAIL=$((FAIL+1)); fi
if python3 "$ARCHIVE/tests/count-consistency.py" >/dev/null 2>&1; then echo "  ✓ [Persona/DB/Prose Count Consistency] PASS"; PASS=$((PASS+1)); else echo "  ✗ [Persona/DB/Prose Count Consistency] FAIL"; FAIL=$((FAIL+1)); fi
echo ""
echo "============================================================"
echo "  SCORECARD: $PASS / $((PASS+FAIL)) SUITES PASSED ($FAIL failed, $SKIP skipped)"
echo "============================================================"
[ "$FAIL" -eq 0 ]
