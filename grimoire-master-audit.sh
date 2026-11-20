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
# Suites are read-only checks, so they run in parallel; results are
# collected by index and reported in registry order below.
TMPDIR_AUDIT=$(mktemp -d)
trap 'rm -rf "$TMPDIR_AUDIT"' EXIT
N=0
run() {
    N=$((N+1))
    ( bash "$1" >/dev/null 2>&1; echo $? > "$TMPDIR_AUDIT/$N" ) &
    eval "LABEL_$N=\"$2\""
}
run_py() {
    label="$1"; shift
    N=$((N+1))
    ( python3 "$@" >/dev/null 2>&1; echo $? > "$TMPDIR_AUDIT/$N" ) &
    eval "LABEL_$N=\"$label\""
}
run "$ARCHIVE/tests/test-db.sh" "Database Integrity (68 checks)"
# run() executes a suite with bash, so Python suites are invoked explicitly.
run_py "Game Caption Corpus" "$ARCHIVE/tests/caption-test.py"
run "$ARCHIVE/tests/compendium-check.sh" "Compendium Files"
run "$ARCHIVE/tests/lore-integrity.sh" "Lore Archive Integrity"
run "$ARCHIVE/tests/cutscene-verify.sh" "Cutscene Caption Verification"
run "$ARCHIVE/tests/query-interface-test.sh" "Query Interface (98 checks)"
run "$ARCHIVE/tests/agent-layout-test.sh" "Agent Layout (OpenCode/OpenClaw, 354 checks)"
run_py "File Conformance" "$ARCHIVE/tests/conformance.py"
run_py "Agnostic Contract" "$ARCHIVE/tests/agnostic-test.py"
run_py "Documentation Consistency" "$ARCHIVE/tests/docs-consistency.py"
run_py "Agent Access" "$ARCHIVE/tests/agent-access-test.py"
run_py "Knowledge Webs" "$ARCHIVE/scripts/generate-knowledge-web.py" --check
run_py "Source Overlap vs Live" "$ARCHIVE/tests/source-overlap-verify.py"
run_py "Speaker Noise Gate" "$ARCHIVE/tests/speaker-audit.py"
run_py "Agent Suite Manifests" "$ARCHIVE/tests/suite-manifest-test.py"
run_py "Tree Mirror (rsync replacement)" "$ARCHIVE/tests/mirror-tree-test.py"
run_py "Peer Permission Leak Audit" "$ARCHIVE/tests/permission-leak-audit.py"
run_py "Persona/DB/Prose Count Consistency" "$ARCHIVE/tests/count-consistency.py"
run_py "README Quality (sections, demo, wiki, budgets)" "$ARCHIVE/tests/readme-quality.py"
wait
i=1
while [ "$i" -le "$N" ]; do
    eval "label=\"\$LABEL_$i\""
    code=$(cat "$TMPDIR_AUDIT/$i")
    if [ "$code" -eq 0 ]; then echo "  ✓ [$label] PASS"; PASS=$((PASS+1));
    else echo "  ✗ [$label] FAIL"; FAIL=$((FAIL+1)); fi
    i=$((i+1))
done
echo ""
echo "============================================================"
echo "  SCORECARD: $PASS / $((PASS+FAIL)) SUITES PASSED ($FAIL failed, $SKIP skipped)"
echo "============================================================"
[ "$FAIL" -eq 0 ]
