#!/bin/bash
# Extended verification: fault injection, MCP matrix, checksum behavior, source
# cross-validation. On demand; requires the optional MCP venv for the MCP parts.
set -u

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
PASS=0; FAIL=0
run() {
    local name="$1" cmd="$2"
    if eval "$cmd" >/tmp/opencode/extended-$$.log 2>&1; then
        echo "  ✓ [$name] PASS"; PASS=$((PASS+1))
    else
        echo "  ✗ [$name] FAIL"; tail -5 /tmp/opencode/extended-$$.log | sed 's/^/      /'
        FAIL=$((FAIL+1))
    fi
    rm -f /tmp/opencode/extended-$$.log
}

echo "============================================================"
echo "  EXTENDED VERIFICATION"
echo "============================================================"
run "Robustness (inputs, corrupt DB, concurrency)" "python3 '$ARCHIVE/tests/robustness-test.py'"
run "MCP contract" "'$ARCHIVE/mcp-server/.venv/bin/python' '$ARCHIVE/tests/mcp-test.py'"
run "MCP matrix (141 calls, 3 clients)" "'$ARCHIVE/mcp-server/.venv/bin/python' '$ARCHIVE/tests/mcp-matrix-test.py'"
run "Checksum acceptance and rejection" "bash '$ARCHIVE/tests/checksum-test.sh'"
run "DB vs source cross-check" "python3 '$ARCHIVE/tests/db-source-crosscheck.py'"
run "Retrieval evaluation" "python3 '$ARCHIVE/tests/retrieval-eval.py'"
run "Item provenance audit" "python3 '$ARCHIVE/tests/item-audit.py'"
run "Documentation commands" "python3 '$ARCHIVE/tests/docs-audit.py'"
run "Golden voice snapshots" "bash '$ARCHIVE/tests/golden-voice-test.sh'"

echo ""
echo "============================================================"
echo "  EXTENDED: $PASS passed, $FAIL failed"
echo "============================================================"
[ "$FAIL" -eq 0 ]
