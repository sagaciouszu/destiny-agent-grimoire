#!/bin/bash
ARCHIVE="${ARCHIVE:-$(cd "$(dirname "$0")/.." && pwd)}"
WORKSPACE="${WORKSPACE:-$(bash "$(dirname "$0")/resolve-workspace.sh" "$0")}"

echo "=== DRIFTER ARCHIVE VALIDATION ==="
echo ""

[ -n "$WORKSPACE" ] && [ -d "$WORKSPACE" ] || { echo "FATAL: workspace unresolved (WORKSPACE=$WORKSPACE) - set WORKSPACE or run from the agent repo"; exit 1; }

BOOKS=$(ls "$ARCHIVE/source/books"/*.md 2>/dev/null | wc -l)
TRANSCRIPTS=$(ls "$ARCHIVE/source/transcripts"/*.md 2>/dev/null | grep -v 'index.md' | wc -l)
echo "Books: $BOOKS"
echo "Transcripts: $TRANSCRIPTS"
echo "Workspace .md files: $(find "$WORKSPACE" -name '*.md' | wc -l)"
echo ""

echo "--- Consolidated Entry Point ---"
for f in INDEX.md drifter-core.md; do
    if [ -f "$WORKSPACE/$f" ]; then
        echo "$f: EXISTS ($(wc -l < "$WORKSPACE/$f") lines)"
    else
        echo "$f: MISSING"
    fi
done
echo ""

echo "--- Module Directories ---"
for d in core world voice; do
    if [ -d "$WORKSPACE/$d" ]; then
        echo "$d/: EXISTS ($(ls "$WORKSPACE/$d" | wc -l) files)"
    else
        echo "$d/: MISSING"
    fi
done
echo ""

echo "--- Lore Symlink ---"
if [ -L "$WORKSPACE/lore" ]; then
    echo "lore -> $(readlink "$WORKSPACE/lore")"
else
    echo "lore: NOT A SYMLINK"
fi
echo ""

echo "--- Broken Markdown Links in Workspace ---"
python3 - "$WORKSPACE" << 'PY'
import os, re, glob, sys
ws = sys.argv[1]
files = []
for root,_,fs in os.walk(ws):
    if '/lore' in root or '/.git' in root:
        continue
    for f in fs:
        if f.endswith('.md'):
            files.append(os.path.join(root,f))
refs=set()
for f in files:
    for line in open(f,encoding='utf-8',errors='ignore'):
        for m in re.finditer(r'`([A-Za-z0-9_./-]+\.md)`',line):
            refs.add(m.group(1))
missing=[r for r in sorted(refs) if not os.path.exists(os.path.join(ws,r))]
print("total refs:",len(refs),"missing:",len(missing))
for m in missing: print("  MISSING:",m)
PY
echo ""

echo "--- Unverified Quotes ---"
python3 - "$WORKSPACE" "$ARCHIVE" << 'PY'
import re, glob, os, sys
ws, archive = sys.argv[1], sys.argv[2]
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
    if '/lore' in root or '/.git' in root:
        continue
    for f in fs:
        if f.endswith('.md'): files.append(os.path.join(root,f))
allq=set()
for f in files:
    in_fence=False
    txt=open(f,encoding='utf-8',errors='ignore').read()
    txt=re.sub(r'\A---\n.*?\n---\n','',txt,count=1,flags=re.S)
    for line in txt.splitlines():
        st=line.strip()
        if st.startswith(chr(96)*3) or st.startswith('~~~'):
            in_fence=not in_fence
            continue
        if in_fence: continue
        prose=re.sub(r'`[^`]*`','',line)
        for m in re.finditer(r'"([^"]+)"',prose):
            q=m.group(1).strip()
            if len(q)>6: allq.add(q)
unv=[q for q in allq if not (any(norm(q) in cn or cn in norm(q) for cn in canon_norm) or norm(q) in corpus_norm)]
print("unverified quotes:",len(unv))
for u in unv[:10]:
    print("  ", u)
PY
echo ""

echo "--- Master Index ---"
if [ -f "$WORKSPACE/INDEX.md" ]; then
    echo "INDEX.md: EXISTS ($(wc -l < "$WORKSPACE/INDEX.md") lines)"
else
    echo "INDEX.md: MISSING"
fi

echo ""
echo "=== VALIDATION COMPLETE ==="
