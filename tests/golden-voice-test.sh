#!/bin/bash
# Golden voice snapshots: fixed responses must keep their pass/fail verdict.
set -u
ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
PASS=0; FAIL=0
while IFS=$'\t' read -r agent tool text expect; do
    [ -z "$agent" ] && continue
    if [ "$tool" = "scorer" ]; then
        if python3 "$ARCHIVE/tests/${agent}-voice-scorer.py" "$text" >/dev/null 2>&1; then got=pass; else got=fail; fi
    else
        if bash "$ARCHIVE/tests/${agent}-validate-response.sh" "$text" >/dev/null 2>&1; then got=pass; else got=fail; fi
    fi
    if [ "$got" = "$expect" ]; then
        echo "  ✓ $agent $tool: $expect"; PASS=$((PASS+1))
    else
        echo "  ✗ $agent $tool: expected $expect, got $got"; FAIL=$((FAIL+1))
    fi
done < <(python3 - "$ARCHIVE/tests/golden-voice.json" <<'PY'
import json, sys
for case in json.load(open(sys.argv[1], encoding='utf-8'))['cases']:
    print('\t'.join([case['agent'], case['tool'], case['text'], case['expect']]))
PY
)
echo ""
echo "Passed: $PASS | Failed: $FAIL"
[ "$FAIL" -eq 0 ]
