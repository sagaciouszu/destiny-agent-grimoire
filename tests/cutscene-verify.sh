#!/bin/bash
# Cutscene Caption Verification
# Validates YouTube cutscene captions against canonical Ishtar transcripts.
# NOTE: every source video carries only auto-generated captions (no manual
# tracks exist for these compilations), so these gates are the quality bar.
# and interactions using word 8-gram shingles (segmentation-independent).
# Checks: scale, encoding sanity, cross-source corroboration, per-video
# overlap, cross-video consistency (D1 pair), speaker attribution.
# Usage: ./tests/cutscene-verify.sh

DB="${DB:-$(cd "$(dirname "$0")/.." && pwd)/db/grimoire.db}"
[ -f "$DB" ] || { echo "FAIL: database not found at $DB - bootstrap: ./setup.sh, or python3 db/migrate.py (see README)"; exit 1; }

echo "=== CUTSCENE CAPTION VERIFICATION ==="
echo ""

python3 - "$DB" << 'PYEOF'
import sqlite3, re, sys
from collections import defaultdict

conn = sqlite3.connect(sys.argv[1])

def norm(s):
    s = s.lower().replace('\u2026','...').replace('\u2019',"'").replace('\u2014','-').replace('\u2013','-')
    return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9 ]+',' ',s)).strip()

def shingles(texts, n=8):
    sh = set()
    for t in texts:
        w = t.split()
        for i in range(len(w)-n+1):
            sh.add(' '.join(w[i:i+n]))
    return sh

results = []
def check(label, ok, detail):
    results.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}: {label} ({detail})")

# Load cutscene content
vid_text = defaultdict(list)
all_cut_lines = 0
garbage = 0
for slug, line in conn.execute("""
    SELECT t.slug, tl.line FROM transcript_lines tl
    JOIN transcripts t ON t.id=tl.transcript_id
    WHERE t.slug LIKE 'cutscene-%' AND tl.is_stage_dir=0"""):
    all_cut_lines += 1
    if re.search(r'[^\x09\x0a\x20-\x7e\u00a0-\uffff]', line) or '\ufffd' in line or line.count('?') > 3:
        garbage += 1
    if len(line) >= 15:
        vid_text[slug].append(norm(line))

n_videos = len(vid_text)
check("scale: videos and lines", n_videos >= 20 and all_cut_lines >= 30000,
      f"{n_videos} videos, {all_cut_lines} lines")

check("encoding sanity", all_cut_lines > 0 and garbage / all_cut_lines <= 0.001,
      f"{garbage}/{all_cut_lines} suspect lines")

# Canonical corpus (non-cutscene transcripts + interactions)
canon = [norm(l) for l, in conn.execute("""
    SELECT tl.line FROM transcript_lines tl
    JOIN transcripts t ON t.id=tl.transcript_id
    WHERE t.slug NOT LIKE 'cutscene-%' AND tl.is_stage_dir=0 AND LENGTH(tl.line) >= 15
    AND COALESCE(t.source_tier, '') != 'game_caption'""")]
canon += [norm(t) for t, in conn.execute("SELECT text FROM interactions WHERE text != ''")]
canon_sh = shingles(canon)

vid_sh = {s: shingles(t) for s, t in vid_text.items()}
union = set().union(*vid_sh.values())
shared = canon_sh & union
pct = len(shared) / len(canon_sh) * 100
check("cross-source corroboration", pct >= 10.0,
      f"{len(shared)}/{len(canon_sh)} canonical 8-grams found in captions ({pct:.1f}%)")

per = {s: len(v & canon_sh) for s, v in vid_sh.items()}
corroborated = sum(1 for n in per.values() if n >= 50)
low = sum(1 for n in per.values() if n < 50)
check("per-video corroboration", corroborated >= max(3, int(n_videos * 0.8)),
      f"{corroborated}/{n_videos} videos share >=50 canonical 8-grams (min {min(per.values())})")

# Cross-video consistency: the two independent D1 transcriptions must agree
d1 = [s for s in vid_sh if 'destiny-1' in s]
if len(d1) == 2:
    inter = len(vid_sh[d1[0]] & vid_sh[d1[1]])
    check("cross-video consistency (D1 pair)", inter >= 50, f"{inter} shared 8-grams")
else:
    check("cross-video consistency (D1 pair)", False, f"expected 2 D1 videos, found {len(d1)}")

# Speaker attribution: cutscene lines matched to known speakers
attributed = conn.execute("""
    SELECT COUNT(*) FROM transcript_lines tl
    JOIN transcripts t ON t.id=tl.transcript_id
    WHERE t.slug LIKE 'cutscene-%' AND tl.speaker NOT IN ('Cutscene','Narration')""").fetchone()[0]
check("speaker attribution", attributed >= 300, f"{attributed} lines attributed")

conn.close()
print("")
print(f"Passed: {sum(results)}/{len(results)}")
sys.exit(0 if all(results) else 1)
PYEOF
RC=$?
echo ""
echo "=== CUTSCENE VERIFICATION COMPLETE ==="
exit $RC
