#!/usr/bin/env python3
"""Sync documentation count claims to the live database.

Counts (transcripts, transcript lines, FTS rows, per-character lines) move
every time scrape data is ingested; docs drift silently. This tool rewrites
every known claim pattern from db/grimoire.db in one pass across all three
repositories. CHANGELOG.md is exempt (historical sections stay frozen); hand-
edit its in-flight release section instead.

Usage: python3 tests/sync-doc-counts.py [--check]
  --check  report what would change, write nothing (exit 1 if stale)
"""
import os
import re
import sqlite3
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
GRIMOIRE = os.path.dirname(HERE)
WORK = os.path.dirname(GRIMOIRE)
ERIS = os.path.join(WORK, 'eris-morn')
DRIFTER = os.path.join(WORK, 'how-to-drift-for-agents')

conn = sqlite3.connect(os.path.join(GRIMOIRE, 'db', 'grimoire.db'))
q = lambda sql: conn.execute(sql).fetchone()[0]
C = {
    'transcripts': q('SELECT COUNT(*) FROM transcripts'),
    'lines': q('SELECT COUNT(*) FROM transcript_lines'),
    'fts': q('SELECT COUNT(*) FROM fts'),
    'eris': q("SELECT COUNT(*) FROM transcript_lines WHERE speaker LIKE '%Eris%' AND is_stage_dir=0"),
    'drifter': q("SELECT COUNT(*) FROM transcript_lines WHERE speaker LIKE '%Drifter%'"),
    'drifter_exact': q("SELECT COUNT(*) FROM transcript_lines WHERE speaker = 'Drifter'"),
}
conn.close()

# Patterns shared by every repo (counts only; no character-specific claims)
SHARED = [
    (r'\| transcripts \| \d+', '| transcripts | {transcripts}'),
    (r'\| `transcripts` \| \d+', '| `transcripts` | {transcripts}'),
    (r'\| transcript_lines \| \d+', '| transcript_lines | {lines}'),
    (r'\| fts \| \d+', '| fts | {fts}'),
    (r'\d{3,5} transcript headers', '{transcripts} transcript headers'),
    (r'\d{3,5} transcripts \(\d{4,6} dialogue lines', '{transcripts} transcripts ({lines} dialogue lines'),
    (r'\d{3,5} transcripts \(\d{4,6} lines\)', '{transcripts} transcripts ({lines} lines)'),
    (r'110 books, \d{3,5} transcripts', '110 books, {transcripts} transcripts'),
    (r'\d{3,5} transcripts, 110 books', '{transcripts} transcripts, 110 books'),
    (r'\(\d{4,6} dialogue lines,', '({lines} dialogue lines,'),
    (r'\(\d{4,6} dialogue lines\)', '({lines} dialogue lines)'),
    (r'searches all \d{3,5}', 'searches all {transcripts}'),
]
ERIS_PATS = [
    (r'quotes-\d+%20verified', 'quotes-{eris}%20verified'),
    (r'\b\d{3,4} canonical Eris', '{eris} canonical Eris'),
    (r'\(\d{3,4} Eris Morn lines\)', '({eris} Eris Morn lines)'),
    (r'\(\d{3,4} canonical Eris transcript lines\)', '({eris} canonical Eris transcript lines)'),
]
DRIFTER_PATS = [
    (r'quotes-\d+%20verified', 'quotes-{drifter}%20verified'),
    (r'All \d+ Drifter quotes', 'All {drifter} Drifter quotes'),
    (r'canonical transcripts \(\d+ Drifter lines\)', 'canonical transcripts ({drifter} Drifter lines)'),
    (r'\b\d{3,4} Drifter transcript lines in the database', '{drifter_exact} Drifter transcript lines in the database'),
    (r'\b\d{3,4} verified Drifter quotes', '{drifter} verified Drifter quotes'),
]

FILES = []
for pat in [os.path.join(GRIMOIRE, '*.md'), os.path.join(GRIMOIRE, 'db', '*.md'),
            os.path.join(GRIMOIRE, 'skills', 'destiny-grimoire', '*.md'),
            os.path.join(GRIMOIRE, 'compendium', '*.md'),
            os.path.join(DRIFTER, '*.md'), os.path.join(DRIFTER, 'core', '*.md'),
            os.path.join(DRIFTER, 'reference', '*.md'),
            os.path.join(ERIS, '*.md'), os.path.join(ERIS, 'core', '*.md'),
            os.path.join(ERIS, 'reference', '*.md')]:
    FILES.extend(glob.glob(pat))

CHECK = '--check' in sys.argv
changes = []
for path in sorted(set(FILES)):
    if os.path.basename(path) == 'CHANGELOG.md':
        continue
    pats = list(SHARED)
    if path.startswith(DRIFTER + os.sep):
        pats += DRIFTER_PATS
    elif path.startswith(ERIS + os.sep):
        pats += ERIS_PATS
    s = open(path, encoding='utf-8').read()
    orig = s
    for rx, tpl in pats:
        s = re.sub(rx, lambda m: tpl.format(**C), s)
    if s != orig:
        changes.append(path)
        if not CHECK:
            open(path, 'w', encoding='utf-8').write(s)

print('DB counts:', C)
if changes:
    print(('WOULD UPDATE: ' if CHECK else 'UPDATED: ') + str(len(changes)) + ' files')
    for c in changes:
        print('  ', os.path.relpath(c, WORK))
else:
    print('all documentation counts already in sync')
sys.exit(1 if (CHECK and changes) else 0)
