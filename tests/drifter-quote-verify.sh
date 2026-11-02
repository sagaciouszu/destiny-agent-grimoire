#!/bin/bash
# Drifter Quote Verifier
# Checks all quoted strings in agent files against canonical transcripts.
# Usage: ./drifter-quote-verify.sh
# Exit code: 0 if all quotes verified, 1 if unverified quotes found.

ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORKSPACE="${WORKSPACE:-$(cd "$(dirname "$0")/../../how-to-drift-for-agents" && pwd)}"

python3 - "$ARCHIVE" "$WORKSPACE" << 'PY'
import re, glob, os, sys
archive, ws = sys.argv[1], sys.argv[2]
canon=[]
for p in glob.glob(archive+'/source/transcripts/*.md'):
    for line in open(p,encoding='utf-8',errors='ignore'):
        m=re.match(r'^\*(?:The )?Drifter:\*\s*(.*)$',line.strip())
        if m: canon.append(m.group(1).strip())
def norm(s):
    s=s.lower().replace('\u2026','...').replace('\u2019',"'").replace('\u2014','-').replace('\u2013','-')
    s=re.sub(r'[^a-z0-9 ]+',' ',s); s=re.sub(r'\s+',' ',s).strip(); return s
canon_norm=[norm(q) for q in canon]
corpus=''
for p in glob.glob(archive+'/source/books/*.md')+glob.glob(archive+'/source/transcripts/*.md'):
    corpus += '\n'+open(p,encoding='utf-8',errors='ignore').read()
corpus_norm=norm(corpus)
files=[]
for root,_,fs in os.walk(ws):
    for f in fs:
        if f.endswith('.md'): files.append(os.path.join(root,f))
unv=[]
for f in files:
    for line in open(f,encoding='utf-8',errors='ignore'):
        for m in re.finditer(r'"([^"]+)"',line):
            q=m.group(1).strip()
            if len(q)<=6: continue
            nq=norm(q)
            in_trans = any(nq in cn or cn in nq for cn in canon_norm)
            in_corpus = nq in corpus_norm
            if not in_trans and not in_corpus:
                unv.append((f,q))
print("Files scanned:", len(files))
print("Quotes checked:", sum(1 for f in files for l in open(f) for m in re.finditer(r'"([^"]+)"',l) if len(m.group(1).strip())>6))
print("Unverified quotes:", len(unv))
for f,q in unv[:20]:
    print(f"  {f}: {q[:60]}")
if unv:
    sys.exit(1)
else:
    print("PASS: All quotes verified.")
    sys.exit(0)
PY
