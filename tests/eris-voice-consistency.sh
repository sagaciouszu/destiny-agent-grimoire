#!/bin/bash
# Eris Voice Consistency Check
# Scans quoted strings in Eris agent files for Drifter-speech contamination
# and non-Eris patterns. Canon-verified quotes are exempt (canon is canon:
# e.g. Eris's single [laughs] in the Prophecy transcript).
# Usage: ./eris-voice-consistency.sh

WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0" eris)}"
DB="${DB:-$WORKSPACE/lore/db/grimoire.db}"
[ -f "$DB" ] || DB="$WORKSPACE/../destiny-agent-grimoire/db/grimoire.db"

echo "=== ERIS VOICE CONSISTENCY CHECK ==="
echo ""

if [ ! -f "$DB" ]; then
    echo "FAIL: grimoire database not found at $DB (needed for canon exemption) - bootstrap: ./setup.sh, or python3 lore/db/migrate.py (see README)"
    exit 1
fi

python3 - "$DB" "$WORKSPACE" << 'PYEOF'
import re, os, sys, sqlite3
db, ws = sys.argv[1], sys.argv[2]

def norm(s):
    s = s.lower().replace('\u2026','...').replace('\u2019',"'").replace('\u2014','-').replace('\u2013','-')
    s = re.sub(r'[^a-z0-9 ]+',' ',s); s = re.sub(r'\s+',' ',s).strip()
    return s

conn = sqlite3.connect(db)
canon = set()
for r in conn.execute("SELECT line FROM transcript_lines WHERE speaker LIKE '%Eris%'"):
    if r[0]:
        cn = norm(r[0])
        if len(cn) >= 15:
            canon.add(cn)
        for sentence in re.split(r'(?<=[.!?])\s+', cn):
            if len(sentence) >= 15:
                canon.add(sentence)

# Drifter-speech patterns: address-slang and casual markers (word + space form
# so single-token rule quotes like Never "kid." are not matched)
SLANG = re.compile(r'\b(heh|nah|yeah|kid|brother|buddy|pal|dude|y\'know|gotta|nothin\')\b', re.I)
LAUGH = re.compile(r'\b(haha|lol)\b|\[chuckles\]|\[laughs\]', re.I)

files = []
for root, _, fs in os.walk(ws):
    if '/lore' in root or '/.git' in root:
        continue
    for f in fs:
        if f.endswith('.md'):
            files.append(os.path.join(root, f))

slang_hits, laugh_hits = [], []
for f in files:
    for line in open(f, encoding='utf-8', errors='ignore'):
        for m in re.finditer(r'"([^"]{7,})"', line):
            q = m.group(1).strip()
            nq = norm(q)
            if not nq or ' ' not in q:
                continue  # single-token quotes are rule references, not speech
            is_canon = any(nq in cn or cn in nq for cn in canon)
            if is_canon:
                continue  # verified canon line: exempt
            if SLANG.search(q):
                slang_hits.append((os.path.relpath(f, ws), q[:80]))
            if LAUGH.search(q):
                laugh_hits.append((os.path.relpath(f, ws), q[:80]))

fail = 0
print("--- Drifter slang in non-canon quotes ---")
if slang_hits:
    for f, q in slang_hits[:5]:
        print(f"  {f}: {q}")
    fail += 1
else:
    print("  (none = good)")

print("")
print("--- Cross-character attribution (quote spoken by someone else?) ---")
# Build one big normalized string per speaker. A quote that matches a named
# non-Eris speaker with no Eris match is misattributed (e.g. a Drifter line
# about Eris sitting in an Eris voice file). Cutscene/Narration matches are
# attribution-pending, not definitive, so they do not flag.
speaker_corpus = {}
for sp, ln in conn.execute(
        "SELECT speaker, norm_line FROM transcript_lines WHERE norm_line != ''"):
    if sp in ('Cutscene', 'Narration'):
        continue
    speaker_corpus.setdefault(sp.lower(), []).append(ln)
speaker_big = {sp: ' ' + ' '.join(parts) + ' ' for sp, parts in speaker_corpus.items()}
conn.close()

misattr = []
for f in files:
    heading = ''
    for line in open(f, encoding='utf-8', errors='ignore'):
        st = line.strip()
        if st.startswith('#'):
            heading = st.lower()
            continue
        for m in re.finditer(r'"([^"]{7,})"', line):
            q = m.group(1).strip()
            nq = norm(q)
            if len(nq) < 15 or ' ' not in q:
                continue
            pad = ' ' + nq + ' '
            matches = [sp for sp, big in speaker_big.items() if pad in big]
            if matches and not any('eris' in sp for sp in matches):
                # Contextual attribution: the line names the speaker.
                if any(sp.split()[0] in line.lower() for sp in matches):
                    continue
                if any(sp.split()[0] in heading for sp in matches):
                    continue
                misattr.append((os.path.relpath(f, ws), q[:70], sorted(matches)[:3]))

if misattr:
    for f, q, sps in misattr[:5]:
        print(f"  {f}: [{', '.join(sps)}] {q}")
    fail += 1
else:
    print("  (none = good)")

print("")
print("--- Laughter in non-canon quotes ---")
if laugh_hits:
    for f, q in laugh_hits[:5]:
        print(f"  {f}: {q}")
    fail += 1
else:
    print("  (none = good)")

print("")
print("--- Identity anchor present ---")
anchor = any('I am Eris Morn' in open(f, encoding='utf-8', errors='ignore').read() for f in files)
if anchor:
    print("  'I am Eris Morn' anchor found")
else:
    print("  MISSING: identity anchor")
    fail += 1

print("")
print(f"Consistency issues found: {fail}")
sys.exit(1 if fail else 0)
PYEOF
RC=$?
echo "=== VOICE CONSISTENCY CHECK COMPLETE ==="
exit $RC
