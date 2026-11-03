#!/bin/bash
# Drifter Cross-Reference Validator
# Verifies every "Depends On:" reference points to an existing file.
# Usage: ./drifter-xref-validate.sh

WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"
echo "=== DRIFTER CROSS-REFERENCE VALIDATION ==="
echo ""

python3 - "$WORKSPACE" << 'PY'
import os, re, glob, sys
ws = sys.argv[1]
files = []
for root,_,fs in os.walk(ws):
    for f in fs:
        if f.endswith('.md'):
            files.append(os.path.join(root,f))
errors = 0
for f in files:
    rel = os.path.relpath(f, ws)
    for line in open(f, encoding='utf-8', errors='ignore'):
        if 'Depends On:' in line:
            # extract file refs
            for m in re.finditer(r'`([A-Za-z0-9_./-]+\.md)`', line):
                ref = m.group(1)
                if not os.path.exists(os.path.join(ws, ref)):
                    print("BROKEN: %s -> %s" % (rel, ref))
                    errors += 1
print("Total files checked:", len(files))
print("Broken references:", errors)
if errors == 0:
    print("✓ All cross-references valid.")
PY
echo ""
echo "=== CROSS-REFERENCE VALIDATION COMPLETE ==="
