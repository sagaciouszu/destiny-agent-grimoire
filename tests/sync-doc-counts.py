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
    'character_lines': q('SELECT COUNT(*) FROM character_lines'),
    'books': q('SELECT COUNT(*) FROM books'),
    'book_entries': q('SELECT COUNT(*) FROM book_entries'),
    'cards': q('SELECT COUNT(*) FROM grimoire_cards'),
    'interactions': q('SELECT COUNT(*) FROM interactions'),
    'items': q('SELECT COUNT(*) FROM items'),
    'records': q('SELECT COUNT(*) FROM records'),
    'characters': q('SELECT COUNT(*) FROM characters'),
    'speakers': q('SELECT COUNT(*) FROM v_speakers'),
    'aliases': q('SELECT COUNT(*) FROM speaker_aliases'),
    'verify': q('SELECT COUNT(*) FROM verify_fts'),
    'item_titles': q('SELECT COUNT(*) FROM item_title_fts'),
}
conn.close()

# Patterns shared by every repo (counts only; no character-specific claims)
SHARED = [
    (r'\| transcripts \| \d+', '| transcripts | {transcripts}'),
    (r'\| `transcripts` \| \d+', '| `transcripts` | {transcripts}'),
    (r'\| transcript_lines \| \d+', '| transcript_lines | {lines}'),
    (r'\| fts \| \d+', '| fts | {fts}'),
    (r'\| `fts` \| \d+', '| `fts` | {fts}'),
    (r'\| character_lines \| \d+', '| character_lines | {character_lines}'),
    (r'\| `character_lines` \| \d+', '| `character_lines` | {character_lines}'),
    (r'\| books \| \d+', '| books | {books}'),
    (r'\| `books` \| \d+', '| `books` | {books}'),
    (r'\| book_entries \| \d+', '| book_entries | {book_entries}'),
    (r'\| `book_entries` \| \d+', '| `book_entries` | {book_entries}'),
    (r'\| grimoire_cards \| \d+', '| grimoire_cards | {cards}'),
    (r'\| `grimoire_cards` \| \d+', '| `grimoire_cards` | {cards}'),
    (r'\| interactions \| \d+', '| interactions | {interactions}'),
    (r'\| `interactions` \| \d+', '| `interactions` | {interactions}'),
    (r'\| items \| \d+', '| items | {items}'),
    (r'\| `items` \| \d+', '| `items` | {items}'),
    (r'\| records \| \d+', '| records | {records}'),
    (r'\| `records` \| \d+', '| `records` | {records}'),
    (r'\| `characters` \| \d+', '| `characters` | {characters}'),
    (r'\| `transcript_lines` \| \d+', '| `transcript_lines` | {lines}'),
    (r'\| `v_speakers` \(view\) \| \d+', '| `v_speakers` (view) | {speakers}'),
    (r'\| `speaker_aliases` \| \d+', '| `speaker_aliases` | {aliases}'),
    (r'\| `verify_fts` \(index\) \| \d+', '| `verify_fts` (index) | {verify}'),
    (r'\| `item_title_fts` \(index\) \| \d+', '| `item_title_fts` (index) | {item_titles}'),
    (r'\d+ characters \(\d+ canon lines\)', '{characters} characters ({character_lines} canon lines)'),
    (r'\d+ characters \(\d+ lines\)', '{characters} characters ({character_lines} lines)'),
    (r'\| `characters` \| \d+', '| `characters` | {characters}'),
    (r'\| characters \| \d+', '| characters | {characters}'),
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
    (r'\b\d{3,4} canonical Eris', '{eris} canonical Eris'),
    (r'\(\d{3,4} Eris Morn lines\)', '({eris} Eris Morn lines)'),
    (r'\(\d{3,4} canonical Eris transcript lines\)', '({eris} canonical Eris transcript lines)'),
]
DRIFTER_PATS = [
    (r'All \d+ Drifter quotes', 'All {drifter} Drifter quotes'),
    (r'canonical transcripts \(\d+ Drifter lines\)', 'canonical transcripts ({drifter} Drifter lines)'),
    (r'\b\d{3,4} Drifter transcript lines in the database', '{drifter_exact} Drifter transcript lines in the database'),
    (r'\b\d{3,4} verified Drifter quotes', '{drifter} verified Drifter quotes'),
]

def sync_inside_table(text, db_path):
    """Regenerate the README 'What is inside' table, total row included.

    Every Rows cell is read from the database (tables, views and indexes alike)
    and the final **Total** row is the sum of the column, so the tally can
    never drift from the data it counts.
    """
    head, sep, rest = text.partition('## What is inside\n\n')
    if not sep:
        return text
    m = re.match(r'(\| Table \| Rows \| Purpose \|\n(?:\|[^\n]*\n)+)', rest)
    if not m:
        return text
    rows, total = [], 0
    conn = sqlite3.connect('file:{}?mode=ro'.format(db_path), uri=True)
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) != 3 or not cells[1].isdigit():
            rows.append(line)          # header, separators, unknown shapes
            continue
        name, purpose = cells[0], cells[2]
        if name.startswith('**Total**'):
            continue                   # re-appended below, always last
        object_name = name.split('`')[1] if '`' in name else name
        try:
            count = conn.execute(
                'SELECT COUNT(*) FROM "{}"'.format(object_name)).fetchone()[0]
        except sqlite3.Error:
            conn.close()
            raise SystemExit('FATAL: README table row has no live object: '
                             + object_name)
        total += count
        rows.append('| {} | {} | {} |'.format(name, count, purpose))
    conn.close()
    rows.append('| **Total** | {} | Rows across every table, view and index '
                'above |'.format(total))
    return head + sep + '\n'.join(rows) + '\n' + rest[m.end():]


README = os.path.join(GRIMOIRE, 'README.md')
DB_PATH = os.path.join(GRIMOIRE, 'db', 'grimoire.db')

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
    if path == README:
        s = sync_inside_table(s, DB_PATH)
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
