#!/bin/bash
# Drifter Quote Verifier (SQLite-backed, fast)
# Checks all quoted strings in agent files against the grimoire database.
# All checks use the DB's normalized text columns. Runs in <5 seconds.

DB="$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db"
WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"
[ -f "$DB" ] || { echo "FAIL: database not found at $DB - bootstrap: ./setup.sh, or python3 db/migrate.py (see README)"; exit 1; }

python3 - "$DB" "$WORKSPACE" << 'PYEOF'
import re, os, sys, sqlite3
db, ws = sys.argv[1], sys.argv[2]

def norm(s):
    s = s.lower().replace('\u2026','...').replace('\u2019',"'").replace('\u2014','-').replace('\u2013','-')
    s = re.sub(r'[^a-z0-g ]+',' ',s)
    s = re.sub(r'[^a-z0-9 ]+',' ',s); s = re.sub(r'\s+',' ',s).strip()
    return s

conn = sqlite3.connect(db)
# Canonical Drifter transcript lines (with speaker variants)
canon_norm = set()
for r in conn.execute("SELECT line FROM transcript_lines WHERE speaker LIKE '%Drifter%'"):
    if r[0]:
        cn = norm(r[0])
        canon_norm.add(cn)
        # Add sentence fragments: split the RAW line first (norm strips periods)
        for sentence in re.split(r'(?<=[.!?])\s+', r[0]):
            cs = norm(sentence)
            if len(cs) > 8:
                canon_norm.add(cs)

# Build corpus: collect per-table norm_text columns + known titles
tables = [
    ('book_entries', 'norm_text'),
    ('transcript_lines', 'norm_line'),
    ('grimoire_cards', 'norm_body'),
    ('interactions', 'norm_text'),
    ('items', 'norm_text'),
    ('records', 'norm_body'),
]
corpus_parts = []
# Titles: transcript titles and book titles count as valid references
title_norms = set()
for r in conn.execute("SELECT title FROM transcripts"):
    if r[0]:
        title_norms.add(norm(r[0]))
for r in conn.execute("SELECT title FROM books"):
    if r[0]:
        title_norms.add(norm(r[0]))
for tbl, col in tables:
    for r in conn.execute(f"SELECT {col} FROM {tbl} WHERE {col} != ''"):
        corpus_parts.append(r[0])
# Also add combined corpus (all joined, one giant norm corpus)
big_corpus = norm(' '.join(corpus_parts))
conn.close()

files = []
for root, _, fs in os.walk(ws):
    for f in fs:
        if f.endswith('.md'): files.append(os.path.join(root, f))

unv = []
total = 0
for f in files:
    in_fence = False
    txt = open(f, encoding='utf-8', errors='ignore').read()
    txt = re.sub(r'\A---\n.*?\n---\n', '', txt, count=1, flags=re.S)
    for line in txt.splitlines():
        st = line.strip()
        if st.startswith('```') or st.startswith('~~~'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        prose = re.sub(r'`[^`]*`', '', line)
        for m in re.finditer(r'"([^"]+)"', prose):
            q = m.group(1).strip()
            if len(q) <= 6: continue
            total += 1
            nq = norm(q)
            # 1. Exact canon substring match
            if any(nq in cn or cn in nq for cn in canon_norm):
                continue
            # 2. Transcript/book title reference
            if any(nq in tn or tn in nq for tn in title_norms):
                continue
            # 2b. Corpus substring match via big combined corpus
            if nq in big_corpus:
                continue
            # 2c. Sentence-level match (dropped attributions): split RAW quote first
            raw_sents = [s for s in re.split(r'(?<=[.!?])\s+', q) if len(s.strip()) >= 10]
            if raw_sents:
                norm_sents = [norm(s) for s in raw_sents]
                norm_sents = [s for s in norm_sents if len(s) >= 15]
                if norm_sents:
                    s_hits = sum(1 for s in norm_sents if s in big_corpus)
                    if s_hits / len(norm_sents) >= 0.6:
                        continue
            # 3. Corpus word-level substring per-table
            if any(nq in cp for cp in corpus_parts):
                continue
            unv.append((os.path.relpath(f, ws), q))

print("Files scanned:", len(files))
print("Quotes checked:", total)
print("Unverified quotes:", len(unv))
for f, q in unv[:20]:
    print(f"  {f}: {q[:60]}")
if unv:
    sys.exit(1)
else:
    print("PASS: All quotes verified.")
    sys.exit(0)
PYEOF
