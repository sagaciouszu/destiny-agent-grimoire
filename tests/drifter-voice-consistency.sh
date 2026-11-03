#!/bin/bash
# Drifter Voice Consistency Check
# Scans all Drifter-attributed quotes for non-Drifter speech patterns.
# Usage: ./drifter-voice-consistency.sh

WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"
echo "=== DRIFTER VOICE CONSISTENCY CHECK ==="
echo ""

# Check for "haha" instead of "heh"
echo "--- 'haha' instead of 'heh' ---"
grep -rn "haha" "$WORKSPACE" 2>/dev/null | grep -v "Naw, haha" | head -5
echo "(none if empty = good)"
echo ""

# Check for "yes" instead of "yeah" in Drifter quotes
echo "--- 'yes' instead of 'yeah' ---"
grep -rn '"[^"]*[^"]yes[^"]*"' "$WORKSPACE" 2>/dev/null | grep -iv "yesterday\|yes," | head -5
echo "(manual review needed)"
echo ""

# Check for "no" instead of "nah" in short Drifter quotes
echo "--- 'no.' instead of 'nah.' ---"
grep -rn '"No\."' "$WORKSPACE" 2>/dev/null | head -5
echo "(none if empty = good)"
echo ""

# Check for "I am" instead of "I'm" in Drifter quotes
echo "--- 'I am' instead of 'I'm' ---"
grep -rn '"[^"]*I am [^"]*"' "$WORKSPACE" 2>/dev/null | head -5
echo "(manual review needed)"
echo ""

# Check for "do not" instead of "don't"
echo "--- 'do not' instead of 'don't' ---"
grep -rn '"[^"]*do not [^"]*"' "$WORKSPACE" 2>/dev/null | head -5
echo "(manual review needed)"
echo ""

# Cross-character attribution: quoted lines that match a named non-Drifter
# speaker with no Drifter match are other characters' words in Drifter files.
DB="${DB:-$WORKSPACE/lore/db/grimoire.db}"
[ -f "$DB" ] || DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
echo "--- Cross-character attribution (quote spoken by someone else?) ---"
if [ -f "$DB" ]; then
python3 - "$DB" "$WORKSPACE" << 'PYEOF2'
import os, re, sqlite3, sys
db, ws = sys.argv[1], sys.argv[2]
def norm(s):
    s = s.lower().replace('\u2026','...').replace('\u2019',"'").replace('\u2014','-').replace('\u2013','-')
    return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]+',' ',s)).strip()
conn = sqlite3.connect(db)
pairs = [(sp.lower(), ln) for sp, ln in conn.execute(
    "SELECT speaker, norm_line FROM transcript_lines WHERE norm_line != ''")
    if sp not in ('Cutscene', 'Narration')]
conn.close()
corpus = {}
for sp, ln in pairs:
    corpus.setdefault(sp, []).append(ln)
big = {sp: ' ' + ' '.join(parts) + ' ' for sp, parts in corpus.items()}
# Narrative/worldbuilding docs quote other characters by design (section
# context); the attribution claim check applies to voice-carrying files only.
NARRATIVE = {
    'core/arcs.md', 'core/threats-locations.md', 'core/quick-lookup.md',
    'core/lore-gating.md', 'core/lie-taxonomy.md', 'core/contradiction-log.md',
    'core/guardrails.md',   # example dialogues, incl. reported speech
    'world/nine.md',        # worldbuilding quotes the Emissary by design
}
files = []
for root, _, fs in os.walk(ws):
    if '/.git' in root or '/lore' in root:
        continue
    for f in fs:
        if not f.endswith('.md'):
            continue
        rel = os.path.relpath(os.path.join(root, f), ws)
        if rel.replace(os.sep, '/') in NARRATIVE:
            continue
        files.append(os.path.join(root, f))
mis = []
for f in files:
    in_fence = False
    heading = ''
    body = open(f, encoding='utf-8', errors='ignore').read()
    body = re.sub(r'\A---\n.*?\n---\n', '', body, count=1, flags=re.S)
    for line in body.splitlines():
        st = line.strip()
        if st.startswith('#'):
            heading = st.lower()
            continue
        if st.startswith('```') or st.startswith('~~~'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        prose = re.sub(r'`[^`]*`', '', line)
        if re.search(r'"\s*/\s*"', prose):
            continue  # dialogue exchange bullet: other speakers are context, not claims
        for m in re.finditer(r'"([^"]{10,})"', prose):
            q = m.group(1).strip()
            if re.search(r'\(about\s*$', prose[:m.start()]):
                continue  # parenthetical reference to someone else's line, not a claim
            nq = norm(q)
            if len(nq) < 15 or ' ' not in q:
                continue
            pad = ' ' + nq + ' '
            matches = [sp for sp, b in big.items() if pad in b]
            if matches and not any('drifter' in sp for sp in matches):
                # The source line may report or impersonate Drifter ("Ghost
                # attempting Drifter impression", "they said", quotes-in-quotes).
                if any('drifter' in ln for sp, ln in pairs if sp in matches and pad in ln):
                    continue
                # Contextual attribution: the line names the speaker
                # (e.g. "You keep the Emissary's warning ..."), so it is
                # correctly framed, not a claim.
                if any(sp.split()[0] in line.lower() for sp in matches):
                    continue
                # Section-level contextual attribution ("From Cayde's Stash ...")
                if any(sp.split()[0] in heading for sp in matches):
                    continue
                mis.append((os.path.relpath(f, ws), q[:70], sorted(matches)[:3]))
for f, q, sps in mis[:10]:
    print(f"  {f}: [{', '.join(sps)}] {q}")
print(f"  non-Drifter quotes: {len(mis)}")
PYEOF2
else
    echo "  SKIP: database not found"
fi
echo ""

echo "=== VOICE CONSISTENCY CHECK COMPLETE ==="
