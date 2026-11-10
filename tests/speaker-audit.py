#!/usr/bin/env python3
"""Pass 3: suspicious-speaker sweep.

Web paragraph parsing can leak artifacts into the speaker column (already
caught: Category, Quest, Ghost Scan). This lists rare speakers with sample
lines so they can be classified: parse noise (reclassify to Narration) vs
genuine minor characters (keep).

Report-only (exit 0) unless a known-noise pattern reappears.
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.environ.get('DB') or os.path.join(ROOT, 'db', 'grimoire.db')
if not os.path.exists(DB):
    print(f'FAIL: database not found at {DB} - bootstrap: ./setup.sh, or python3 db/migrate.py (see README)')
    sys.exit(1)

KNOWN_NOISE = re.compile(
    r'^(Category|Quest|Ghost Scan|Sources|Note|Transcript|References|Related|Content|Share|Dialogue Option|Cutscene (begins|starts) at)\b', re.I)
# Genuine frequent speakers we never want listed even if rare in a fresh DB
KEEP_HINT = re.compile(r'^(Eris|Drifter|Zavala|Ikora|Cayde|Crow|Savath|Oryx|Crow|Ana|Sloane|Saint|Osiris|Mara|Petra|Variks|Shaxx|Ikora)$', re.I)

conn = sqlite3.connect(DB)
rows = conn.execute("""
    SELECT tl.speaker, COUNT(*), MIN(tl.line), tl.is_stage_dir
    FROM transcript_lines tl
    JOIN transcripts t ON t.id = tl.transcript_id
    WHERE tl.speaker NOT IN ('Narration', 'Cutscene')
      AND COALESCE(t.source_tier, '') != 'game_caption'
    GROUP BY tl.speaker
    ORDER BY COUNT(*), tl.speaker
""").fetchall()
try:
    canon_view = conn.execute('SELECT speaker FROM v_canon_speakers').fetchall()
except sqlite3.OperationalError:
    print('FAIL: v_canon_speakers missing; rebuild the database (schema 1.10.0)')
    sys.exit(1)
conn.close()

canon = {r[0] for r in canon_view}
observed = {r[0] for r in rows}
if len(canon) < 50:
    print(f'FAIL: v_canon_speakers has only {len(canon)} rows')
    sys.exit(1)
if not canon <= observed:
    print(f'FAIL: {len(canon - observed)} canon view speakers lack a canon line')
    sys.exit(1)

rare = [r for r in rows if r[1] <= 2 and not KEEP_HINT.match(r[0])]
noise = [r for r in rare if KNOWN_NOISE.match(r[0]) or re.search(r'[:\[\]{}|]', r[0]) or len(r[0]) > 40]
other_rare = [r for r in rare if r not in noise]

print(f'speakers total: {len(rows)} | rare (<=2 lines): {len(rare)}')
print(f'\nKNOWN-NOISE patterns (reclassify to Narration in migrate): {len(noise)}')
for sp, n, sample, _ in noise:
    print(f'  x{n}  {sp!r}  e.g. {sample[:70]!r}')
print(f'\nRare but plausible minor speakers (keep): {len(other_rare)}')
for sp, n, sample, _ in other_rare[:25]:
    print(f'  x{n}  {sp!r}  e.g. {sample[:70]!r}')
if len(other_rare) > 25:
    print(f'  ... and {len(other_rare) - 25} more')

if noise:
    print(f'\nACTION: add to migrate.py junk-speaker filter ({len(noise)} patterns)')
    sys.exit(2)
print('\nNo known-noise patterns present.')
