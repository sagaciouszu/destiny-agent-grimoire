#!/bin/bash
# Module completeness for the generated agent.
# Usage: bash tests/module-test.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
LORE="${LORE:-$REPO/lore}"
WORKSPACE="${WORKSPACE:-$REPO}"
PASS=0; FAIL=0
check() { if eval "$2" >/dev/null 2>&1; then echo "  ✓ $1"; PASS=$((PASS+1)); else echo "  ✗ $1"; FAIL=$((FAIL+1)); fi; }

check "entry file exists" "[ -f '$WORKSPACE/{{id}}.md' ]"
check "core reference exists" "[ -f '$WORKSPACE/{{id}}-core.md' ]"
check "voice reference exists" "[ -f '$WORKSPACE/{{id}}-voice.md' ]"
check "operating program exists" "[ -f '$WORKSPACE/AGENTS.md' ]"
check "index exists" "[ -f '$WORKSPACE/INDEX.md' ]"
check "no placeholders left" "! grep -rEn '\{\{[a-z0-9_]+\}\}' '$WORKSPACE' --include='*.md' --include='*.sh' --exclude-dir=lore"
check "no personal paths" "! grep -rn '/home/[a-z]' '$WORKSPACE' --include='*.md' --include='*.sh' --exclude-dir=lore --exclude=module-test.sh"
check "all documents have headers" "! grep -rL 'Token Estimate' '$WORKSPACE' --include='*.md' --exclude-dir=lore | grep -q ."
check "scripts parse" "for f in '$WORKSPACE'/setup.sh '$WORKSPACE'/tests/*.sh; do bash -n \"\$f\" || exit 1; done"

echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
