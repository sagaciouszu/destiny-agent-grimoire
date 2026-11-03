#!/bin/bash
# Eris Module Completeness Test
ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0" eris)}"
echo "=== ERIS MODULE TEST ==="
PASS=0; FAIL=0
check() { if eval "$1" >/dev/null 2>&1; then echo "  ✓ $2"; PASS=$((PASS+1)); else echo "  ✗ $2"; FAIL=$((FAIL+1)); fi; }
for f in INDEX.md eris-core.md eris-voice.md SOUL.md IDENTITY.md AGENTS.md TOOLS.md README.md; do
    check "[ -f $WORKSPACE/$f ]" "$f exists"
done
for d in core world voice reference; do
    check "[ -d $WORKSPACE/$d ]" "$d/ exists"
done
# headers
MISSING=$(python3 - "$WORKSPACE" << 'PY'
import os,sys
ws=sys.argv[1]
n=0
for root,_,fs in os.walk(ws):
    if '/.git' in root or '/lore' in root: continue
    for f in fs:
        if not f.endswith('.md'): continue
        p=os.path.join(root,f)
        s=open(p,encoding='utf-8',errors='ignore').read()
        if '**Depends On:**' not in s or 'Token Estimate:' not in s:
            n+=1
print(n)
PY
)
check "[ $MISSING -eq 0 ]" "All md files have headers (missing: $MISSING)"
# em-dashes
EM=$(grep -rl '—\|–' "$WORKSPACE" --include='*.md' --exclude-dir=lore --exclude-dir=.git 2>/dev/null | wc -l)
check "[ $EM -eq 0 ]" "No em/en-dashes (found: $EM)"
# personal paths
PER=$(grep -rniE '/home/[a-z0-9._-]+/' "$WORKSPACE" --include='*.md' --include='*.sh' --exclude-dir=lore --exclude-dir=.git 2>/dev/null | wc -l)
check "[ $PER -eq 0 ]" "No personal paths (found: $PER)"
# lore present as symlink or clone
check "[ -L $WORKSPACE/lore ] || [ -d $WORKSPACE/lore ]" "lore present (symlink or clone)"
echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
