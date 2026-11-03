#!/bin/bash
# Verify every quoted string in this workspace against the grimoire.
# Usage: bash tests/quote-verify.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
LORE="${LORE:-$REPO/lore}"
SPEAKER="{{name}}"

python3 - "$REPO" "$LORE" "$SPEAKER" <<'PY'
import os, re, subprocess, sys
repo, lore, speaker = sys.argv[1], sys.argv[2], sys.argv[3]
query = os.path.join(lore, 'db', 'query.py')
if not os.path.exists(query):
    sys.exit('FAIL: grimoire query.py not found; run ./setup.sh')
quoted = []
for root, dirs, files in os.walk(repo):
    dirs[:] = [d for d in dirs if d not in ('.git', 'lore', 'tests')]
    for name in files:
        if not name.endswith('.md'):
            continue
        text = open(os.path.join(root, name), encoding='utf-8', errors='replace').read()
        in_fence = False
        in_front = text.startswith('---\n')
        for raw in text.splitlines():
            if raw.strip() == '---' and in_front:
                in_front = False
                continue
            if in_front:
                continue
            if raw.strip().startswith('```'):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for line in re.findall(r'"([^"\n]{30,})"', raw):
                if len(line.split()) >= 5:
                    quoted.append(line.strip())
bad = []
for line in dict.fromkeys(quoted):
    result = subprocess.run(
        [sys.executable, query, 'verify', line, '--speaker', speaker, '--exact'],
        capture_output=True, text=True)
    if result.returncode != 0:
        bad.append(line)
print(f'unverified quotes: {len(bad)}')
for line in bad[:10]:
    print(f'  {line[:100]}')
sys.exit(1 if bad else 0)
PY
