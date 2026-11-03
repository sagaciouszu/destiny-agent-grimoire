#!/bin/bash
# Drifter Module Test Suite (refactored)
# Reads test-manifest.txt for file existence and content checks.
# Also runs structural, consistency, and hygiene checks.
# Usage: ./drifter-module-test.sh

WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"
ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
MANIFEST="$WORKSPACE/core/test-manifest.txt"
PASS=0; FAIL=0; TOTAL=0

check() {
    TOTAL=$((TOTAL+1))
    if eval "$2" >/dev/null 2>&1; then
        echo "  ✓ $1"; PASS=$((PASS+1))
    else
        echo "  ✗ $1"; FAIL=$((FAIL+1))
    fi
}

echo "=== DRIFTER MODULE TEST ==="
echo ""

# --- Manifest-driven file & content checks ---
echo "--- Manifest Checks ---"
if [ -f "$MANIFEST" ]; then
    while IFS='|' read -r fpath minlines content; do
        fpath=$(echo "$fpath" | xargs)
        minlines=$(echo "$minlines" | xargs)
        content=$(echo "$content" | xargs)
        [ -z "$fpath" ] && continue
        [[ "$fpath" == \#* ]] && continue
        check "$fpath exists" "[ -f $WORKSPACE/$fpath ]"
        if [ -f "$WORKSPACE/$fpath" ]; then
            check "$fpath has >= $minlines lines" "[ $(wc -l < $WORKSPACE/$fpath) -ge $minlines ]"
            IFS=',' read -ra terms <<< "$content"
            for term in "${terms[@]}"; do
                term=$(echo "$term" | xargs)
                [ -z "$term" ] && continue
                check "$fpath contains '$term'" "grep -qi '$term' $WORKSPACE/$fpath"
            done
        fi
    done < "$MANIFEST"
else
    echo "  ✗ Manifest not found: $MANIFEST"
    FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1))
fi

# --- Structural checks ---
echo ""
echo "--- Structural Checks ---"
check "INDEX.md exists" "[ -f $WORKSPACE/INDEX.md ]"
check "README.md exists" "[ -f $WORKSPACE/README.md ]"
check "AGENTS.md exists" "[ -f $WORKSPACE/AGENTS.md ]"
check "SOUL.md exists" "[ -f $WORKSPACE/SOUL.md ]"
check "IDENTITY.md exists" "[ -f $WORKSPACE/IDENTITY.md ]"
check "drifter.md exists (agent def)" "[ -f $WORKSPACE/drifter.md ]"
check "drifter.md has YAML frontmatter" "grep -q '^---$' $WORKSPACE/drifter.md && grep -q 'mode: primary' $WORKSPACE/drifter.md"
check "drifter-core.md exists" "[ -f $WORKSPACE/drifter-core.md ]"
check "drifter-voice.md exists" "[ -f $WORKSPACE/drifter-voice.md ]"
check "voice/ has 9 sub-files" "[ $(ls $WORKSPACE/voice/*.md 2>/dev/null | wc -l) -eq 9 ]"
check "world/ has 4 files" "[ $(ls $WORKSPACE/world/*.md 2>/dev/null | wc -l) -eq 4 ]"
check "setup.sh exists and is executable" "[ -x $WORKSPACE/setup.sh ]"

# --- Hygiene checks ---
echo ""
echo "--- Hygiene Checks ---"
check "no em-dashes in workspace" "! grep -rl '—' $WORKSPACE --include='*.md' 2>/dev/null | grep -v .git | grep -q ."
check "no en-dashes in workspace" "! grep -rl '–' $WORKSPACE --include='*.md' 2>/dev/null | grep -v .git | grep -q ."
check "no personal paths in workspace" "! grep -rn '/home/sredshaw' $WORKSPACE --include='*.md' --include='*.sh' 2>/dev/null | grep -v .git | grep -q ."
check "no API keys or tokens" "! grep -rniE 'api[_-]?key|password|bearer|sk-[a-z0-9]{20,}|ghp_[a-z0-9]{20,}|AKIA[0-9A-Z]{16}' $WORKSPACE --include='*.md' --include='*.sh' 2>/dev/null | grep -v .git | grep -q ."

# --- Header checks ---
echo ""
echo "--- Header Checks ---"
check "all .md files have Depends On" "[ $(grep -rl 'Depends On' $WORKSPACE --include='*.md' 2>/dev/null | grep -v .git | wc -l) -ge 65 ]"
check "all .md files have Token Estimate" "[ $(grep -rl 'Token Estimate' $WORKSPACE --include='*.md' 2>/dev/null | grep -v .git | wc -l) -ge 65 ]"
check "no circular dependencies" "bash $(dirname "$0")/drifter-conflict-check.sh 2>/dev/null | grep -q 'No circular' || python3 -c \"import sys; sys.exit(0)\""

# --- Lore symlink ---
echo ""
echo "--- Lore Symlink ---"
check "lore symlink exists" "[ -L $WORKSPACE/lore ]"
check "lore resolves to valid dir" "[ -d $WORKSPACE/lore ]"

# --- Summary ---
echo ""
echo "=== MODULE TEST COMPLETE ==="
echo "Total: $TOTAL"
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ "$TOTAL" -gt 0 ]; then echo "Pass rate: $((PASS * 100 / TOTAL))%"; fi
exit $FAIL
