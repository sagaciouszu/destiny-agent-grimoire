#!/usr/bin/env python3
"""Apply VO-attribution evidence to archive/data/captions.jsonl — Option A.

Tagging rules (provenance never guessed):

1. SPEAKER, per line, only from per-line evidence:
   - lines already carrying an attribution in captions.jsonl (kept as-is);
   - dialogue-node defs / vendor desks / Liu Feng sandbox (hard build-side links);
   - fresh containment vs the live canon: dialogue-form both sides, fragment
     ratio >= 0.5 vs the longer string, unique speaker among all matches;
   - twin propagation: same normalised text inherits the same speaker.
   The SR-table activity tag is NOT per-line speaker evidence; it never assigns
   a speaker (UI/quest prose in those tables is not voiced).

2. ACTIVITY facet, per SR table (the whole table belongs to the tag): set on
   the record's activity + confidence='derived' when the facet key resolves to
   a taxonomy slug. Provenance: SR tag on the table. This is the entire value
   of the tag for the corpus; facets never gatespeakers.

3. Twins propagate speaker AND facet by normalised text.

Modes:
  --dry-run   report only, write nothing (default)
  --apply     write archive/data/captions.jsonl (backup at backups/ inside repo)
"""
import json, os, re, sqlite3, sys, collections, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL = os.path.join(ROOT, 'archive', 'data', 'captions.jsonl')
DB = os.path.join(ROOT, 'db', 'grimoire.db')
VO_DB = '/opt/vault/d2extraction/votest/vo.db'

sys.path.insert(0, os.path.join(ROOT, 'db'))
from taxonomy import CAPTION_ACTIVITY_SLUGS  # noqa: E402

MODE = '--apply' if '--apply' in sys.argv else '--dry-run'

# ---- normalization (mirrors db/migrate.py) ----
def norm(s):
    s = s.lower()
    s = s.replace('…', '...').replace('’', "'").replace('—', '-').replace('–', '-')
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()

HARD = {'dialogue_node', 'line_prefix', 'ishtar_containment'}

# ============ 1) vo.db evidence (text-keyed, hard evidence only) ============
vo = sqlite3.connect(VO_DB)
vo_speaker = {}
for nt, spk, ss in vo.execute("SELECT norm_text, speaker, speaker_source FROM vo_lines"):
    if not spk or ss not in HARD:
        continue
    key = norm(nt)
    if key:
        vo_speaker.setdefault(key, (spk, ss))
# table-keyed activity facets from the SR tag — gameplay_caption tier only.
# The investment-mirror tables carry item flavor with crucible/gambit tags
# too; those are inventory text, never VO, keeping them out of facets.
table_activity = collections.defaultdict(collections.Counter)
for pkg, entry, act in vo.execute("SELECT source_pkg, source_entry, activity FROM vo_lines WHERE content_tier='gameplay_caption' AND activity IS NOT NULL"):
    table_activity[(pkg, entry)][act] += 1
vo.close()
print(f'vo.db: hard-evidence texts={len(vo_speaker)}  tables with activity tag={len(table_activity)}')

# ============ 2) live canon lines for fresh containment ============
db = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
canon = []
for spk, ln in db.execute("""
    SELECT tl.speaker, tl.norm_line
    FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id
    WHERE t.source_tier != 'game_caption' AND tl.is_stage_dir=0 AND tl.norm_line != ''
"""):
    canon.append((spk or '', ln))
canon_by_token = collections.defaultdict(list)
STOP = frozenset('the a an of to and in is it be that for on with as are was at from your you have not all his her their one do does did but can'.split())
for spk, ln in canon:
    for tok in set(ln.split()):
        if tok not in STOP:
            canon_by_token[tok].append((spk, ln))
print(f'live canon lines available: {len(canon)}')

# ============ 3) load jsonl ============
recs = [json.loads(raw) for raw in open(JSONL, encoding='utf-8')]
print(f'captions.jsonl records: {len(recs)}, lines: {sum(len(r.get("lines", [])) for r in recs)}')

before = collections.Counter()
for r in recs:
    for ln in r['lines']:
        if (ln.get('speaker') or r.get('speaker') or 'Cutscene') != 'Cutscene':
            before[ln.get('speaker_source') or r.get('speaker_source') or 'legacy'] += 1
print('lines attributed today:', sum(before.values()), dict(before))

applied = collections.Counter()
kept_archived = 0
applied_facets = collections.Counter()
facet_conflicts = []
unresolved_facet_keys = collections.Counter()
# twin pool: norm_text -> set of speakers from all attributions (preexisting + hard evidence)
twin_src = collections.defaultdict(set)
for r in recs:
    for l in r['lines']:
        spk = l.get('speaker') or r.get('speaker') or 'Cutscene'
        if spk != 'Cutscene':
            twin_src[norm(l.get('text') or '')].add(spk)

def gate_containment(nl):
    if len(nl) < 25:
        return None
    toks = [t for t in nl.split() if t not in STOP]
    if not toks:
        return None
    counts = collections.Counter()
    for t in toks:
        for spk, ln in canon_by_token.get(t, [])[:4000]:
            counts[(spk, ln)] += 1
    speakers = set()
    matched = False
    for (s, l), c in counts.items():
        if not s or s in ('Cutscene', 'Narration'):
            continue
        if nl in l or l in nl:
            ratio = min(len(nl), len(l)) / max(len(nl), len(l))
            if ratio >= 0.5:
                matched = True
                speakers.add(s)
    if matched and len(speakers) == 1:
        return next(iter(speakers)), 'ishtar_containment'
    return None

# Pass 2: speaker attributions + facets from table tags
for r in recs:
    pkg, entry = None, None
    m = re.match(r'^pkg:([^#]+)#(\d+)$', r.get('source_url') or '')
    if m:
        pkg, entry = m.group(1), int(m.group(2))
    # facet from the table tag
    if pkg and (pkg, entry) in table_activity:
        act, _ = table_activity[(pkg, entry)].most_common(1)[0]
        if len(table_activity[(pkg, entry)]) > 1:
            facet_conflicts.append((pkg, entry, dict(table_activity[(pkg, entry)])))
        if act in CAPTION_ACTIVITY_SLUGS:
            r['activity'], r['confidence'] = act, 'derived'
            applied_facets[act] += 1
        else:
            unresolved_facet_keys[act] += 1
    for l in r['lines']:
        nl = norm(l.get('text') or '')
        cur = l.get('speaker') or r.get('speaker') or 'Cutscene'
        cur_src = l.get('speaker_source') or r.get('speaker_source') or ''
        ent = vo_speaker.get(nl)
        spk, src = None, None
        if ent:
            spk, src = ent
        if not spk:
            hit = gate_containment(nl)
            if hit:
                spk, src = hit
        if spk and spk != cur:
            if cur == 'Cutscene' and not cur_src:
                l['speaker'] = spk                 # per-line evidence only
                l['speaker_source'] = src
                twin_src[nl].add(spk)
                applied[src] += 1
            else:
                kept_archived += 1
        elif cur != 'Cutscene':
            applied[cur_src or 'preexisting'] += 1

# Pass 3: twin propagation — texts with consensus speaker only
WINNER = {k: next(iter(v)) for k, v in twin_src.items() if len(v) == 1}
twin_applied = 0
for k, v in sorted(twin_src.items()):
    if len(v) > 1:
        applied['twin_conflict_skipped'] += 1
        print(f'  twin conflict skipped: {k!r} -> {sorted(v)}')
for r in recs:
    for l in r['lines']:
        if (l.get('speaker') or r.get('speaker') or 'Cutscene') != 'Cutscene':
            continue
        spk = WINNER.get(norm(l.get('text') or ''))
        if spk:
            l['speaker'] = spk
            twin_applied += 1
applied['twin_propagation'] += twin_applied

# ============ report ============
print('\nSUMMARY:')
print(f'  mode: {MODE}')
print(f'  attributions applied: {sum(applied.values())}')
for k, v in applied.most_common():
    print(f'    {k}: {v}')
print(f'  kept archived: {kept_archived}')
print(f'  derived facet records: {dict(applied_facets)}')
if facet_conflicts:
    print(f'  facet conflicts (took majority): {facet_conflicts[:5]}')
if unresolved_facet_keys:
    print(f'  unresolved facet keys: {dict(unresolved_facet_keys)}')
lines_after = sum(1 for r in recs for l in r['lines'] if (l.get('speaker') or r.get('speaker') or 'Cutscene') != 'Cutscene')
print(f'  lines attributed after: {lines_after} / 11624')

if MODE == '--apply':
    import shutil
    for suffix in ('.bak', '.post-option-a.bak'):
        if not os.path.exists(JSONL + suffix):
            shutil.copy2(JSONL, JSONL + suffix)
    with open(JSONL, 'w', encoding='utf-8') as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('\nwrote ' + JSONL)
else:
    print('\ndry-run only')
