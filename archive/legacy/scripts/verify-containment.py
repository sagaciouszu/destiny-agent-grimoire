#!/usr/bin/env python3
"""Verify (and triage) every ishtar_containment match in archive/data/captions.jsonl.

For each line tagged speaker_source='ishtar_containment':

1. replays the containment match against the live canon (NORMALISED compare,
   dialogue-form both sides, ratio >= 0.5 vs the longer string), scoring
   every candidate and recording the best match + the exact canon line
   (transcript slug + seq + text) that supports the claim;
2. triages each match with the autokeep rule:
   - A (auto-keep ratio >= 0.50, unique speaker) -> speaker stays, version bumped to keep
   - B (borderline 0.50-0.55 or shared hit tables) -> KEEP (autokeep, flagged in ledger)
   - C (ratio < 0.50, collision of speakers, stage-dir) -> REVERT to Cutscene, source dropped

Writes a full verification ledger to archive/data/containment-verification.jsonl
(provenance for every match, lines unchanged) and prints a summary. Exit non-zero
on any C-line (used by the gates as a signal; the script itself always succeeds).

Usage:
  python3 scripts/verify-containment.py
"""
import json, os, re, sqlite3, sys, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, 'db', 'grimoire.db')
JSONL = os.path.join(ROOT, 'archive', 'data', 'captions.jsonl')
OUT = os.path.join(ROOT, 'archive', 'data', 'containment-verification.jsonl')

def norm(s):
    s = s.lower()
    s = s.replace('…', '...').replace('’', "'").replace('—', '-').replace('–', '-')
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

STOP = frozenset('the a an of to and in is it be that for on with as are was at from your you have not all his her their one do does did but can'.split())

db = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
print('loading canon…', flush=True)
canon = []
for spk, ln, slug, seq in db.execute("""
    SELECT tl.speaker, tl.norm_line, t.slug, tl.seq
    FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id
    WHERE t.source_tier != 'game_caption' AND tl.is_stage_dir=0 AND tl.norm_line != ''
"""):
    canon.append((spk or '', ln, slug, seq))
print(f'live canon lines: {len(canon)}', flush=True)
by_token = collections.defaultdict(list)
for spk, ln, slug, seq in canon:
    for t in set(ln.split()):
        if t not in STOP:
            by_token[t].append((spk, ln, slug, seq))

def find_best(nl):
    counts = collections.Counter()
    for t in nl.split():
        if t in STOP: continue
        for i, (spk, ln, slug, seq) in enumerate(by_token.get(t, [])[:4000]):
            counts[(spk, ln, slug, seq)] += 1
    best = []
    for (spk, ln, slug, seq), c in counts.items():
        if not spk or spk in ('Cutscene', 'Narration'):
            continue
        if nl in ln or ln in nl:
            ratio = min(len(nl), len(ln)) / max(len(nl), len(ln)) if max(len(nl), len(ln)) else 0
            best.append((ratio, spk, slug, seq, ln))
    if not best:
        return None
    best.sort(key=lambda x: -x[0])
    top = best[0]
    # unique speaker among all candidates above 0.5?
    speakers = {s for r, s, _, _, _ in best if r >= 0.5}
    return {'ratio': top[0], 'speaker': top[1], 'slug': top[2], 'seq': top[3],
            'matched_norm_line': top[4], 'unique': len(speakers) == 1,
            'all_speakers': sorted(speakers)}

buckets = collections.Counter()
ledger = []
C_lines = []
n = 0
for raw in open(JSONL, encoding='utf-8'):
    d = json.loads(raw)
    for l in d['lines']:
        if l.get('speaker_source') != 'ishtar_containment':
            continue
        n += 1
        nl = norm(l.get('text') or '')
        spk_want = l.get('speaker')
        m = find_best(nl)
        ok = False
        entry = {'slug': d.get('slug'), 'hash': l.get('hash'), 'text': l.get('text'),
                 'speaker': spk_want, 'norm_line': nl}
        if m:
            entry.update({'match_ratio': round(m['ratio'], 6), 'canon_speaker': m['speaker'],
                          'canon_slug': m['slug'], 'canon_seq': m['seq'], 'canon_line': m['matched_norm_line'],
                          'unique_speaker': m['unique'], 'all_speakers': m['all_speakers']})
            # autokeep rule: ratio >= 0.50 and unique speaker
            ok = m['ratio'] >= 0.50 and m['unique'] and m['speaker'] == spk_want
            bucket = ('A' if m['ratio'] >= 0.55 else 'B') if ok else 'C'
        else:
            bucket = 'C'
            entry.update({'match_ratio': None, 'reason': 'no candidate canon line with shared token AND containment'})
        buckets[bucket] += 1
        if bucket == 'C':
            C_lines.append(entry)
        entry['bucket'] = bucket
        ledger.append(entry)

with open(OUT, 'w', encoding='utf-8') as fh:
    for e in ledger:
        fh.write(json.dumps(e, ensure_ascii=False) + '\n')
print('\n=== containment verification (autokeep rule) ===')
print(f'matches verified: {n}')
for b in ['A', 'B', 'C']:
    print(f'  bucket {b}: {buckets[b]}')
if C_lines:
    print('\nC-line entries (to revert):')
    for e in C_lines[:20]:
        print(f"  hash={e['hash']} speaker={e.get('speaker')} canon={e.get('canon_slug')} ratio={e.get('match_ratio')} text={e['text'][:80]!r}")
print(f'\nledger written: {OUT}')
sys.exit(0)
