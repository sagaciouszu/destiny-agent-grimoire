#!/usr/bin/env python3
"""Sync documentation count claims to the live database.

Counts (transcripts, transcript lines, FTS rows, per-character lines) move
every time scrape data is ingested; docs drift silently. This tool rewrites
every known claim pattern from db/grimoire.db in one pass across the archive
and every agent repository listed in series/agents.json. CHANGELOG.md is exempt
(historical sections stay frozen); hand-edit its in-flight release section
instead.

Usage: python3 tests/sync-doc-counts.py [--check]
  --check  report what would change, write nothing (exit 1 if stale)
"""
import json
import os
import re
import sqlite3
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
GRIMOIRE = os.path.dirname(HERE)
WORK = os.path.dirname(GRIMOIRE)
sys.path.insert(0, HERE)
import _roster
AGENT_REPOS = _roster.repos()

conn = sqlite3.connect(os.path.join(GRIMOIRE, 'db', 'grimoire.db'))
q = lambda sql: conn.execute(sql).fetchone()[0]
C = {
    'transcripts': q('SELECT COUNT(*) FROM transcripts'),
    'lines': q('SELECT COUNT(*) FROM transcript_lines'),
    'fts': q('SELECT COUNT(*) FROM fts'),
    'eris': q("SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t ON t.id = tl.transcript_id "
              "WHERE speaker = 'Eris Morn' AND is_stage_dir=0 AND t.source_tier != 'game_caption'"),
    'drifter': q("SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id "
                  "WHERE tl.speaker LIKE '%Drifter%' AND COALESCE(t.source_tier,'') != 'game_caption'"),
    'drifter_exact': q("SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id "
                       "WHERE tl.speaker = 'Drifter' AND COALESCE(t.source_tier,'') != 'game_caption'"),
    'character_lines': q('SELECT COUNT(*) FROM character_lines'),
    'books': q('SELECT COUNT(*) FROM books'),
    'book_entries': q('SELECT COUNT(*) FROM book_entries'),
    'cards': q('SELECT COUNT(*) FROM grimoire_cards'),
    'interactions': q('SELECT COUNT(*) FROM interactions'),
    'items': q('SELECT COUNT(*) FROM items'),
    'records': q('SELECT COUNT(*) FROM records'),
    'characters': q('SELECT COUNT(*) FROM characters'),
    'speakers': q('SELECT COUNT(*) FROM v_speakers'),
    'entities': q('SELECT COUNT(*) FROM entities'),
    'entity_aliases': q('SELECT COUNT(*) FROM entity_aliases'),
    'entity_links': q('SELECT COUNT(*) FROM entity_links'),
    'entity_relations': q('SELECT COUNT(*) FROM entity_relations'),
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
    (r'\| `entities` \| \d+', '| `entities` | {entities}'),
    (r'\| `entity_aliases` \| \d+', '| `entity_aliases` | {entity_aliases}'),
    (r'\| `entity_links` \| \d+', '| `entity_links` | {entity_links}'),
    (r'\| `entity_relations` \| \d+', '| `entity_relations` | {entity_relations}'),
    (r'\d+ entity to document links', '{entity_links} entity to document links'),
    (r'\d+ rows: entity to document links', '{entity_links} rows: entity to document links'),
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
# plain prose ("110 books, 2422 transcripts, ..."): rewrite ANY `<number> <noun>`
# to the current DB count for that noun, unconditionally. This is a doc-sync:
# the counts in these files are always the live numbers. Numbers keep the
# style the source used (thousands separators are preserved).
SHARED_PROSE = [
    # (regex with named `num` group, C key) — `num` captures the number and
    # the noun is a lookahead, so the match is the number only.
    (r'(?<![\d,])(?P<num>\d{1,3}(?:,\d{3})+|\d{3,5})(?=\s+transcripts\b)', 'transcripts'),
    (r'(?<![\d,])(?P<num>\d{1,3}(?:,\d{3})+|\d{3,5})(?=\s+dialogue\s+lines\b)', 'lines'),
    (r'(?<![\d,])(?P<num>\d{1,3}(?:,\d{3})+|\d{3,5})(?=\s+grimoire\s+cards\b)', 'cards'),
    (r'(?<![\d,])(?P<num>\d{1,3}(?:,\d{3})+|\d{3,5})(?=\s+interactions\b)', 'interactions'),
    # NOTE(doc-sync): unconditionally rewrites `<digits> records` to the live
    # records-table count (69 today). It will match any digit-shaped phrase —
    # 'triumph 31 records', 'she has 5 records to review' — not only claims
    # about the database. The current corpus contains zero such cases (grep
    # clean); do NOT land any unless it is a count claim (verified by running
    # sync-doc-counts.py --check and reading the resulting diff).
    (r'(?<![\d,])(?P<num>\d{1,3}(?:,\d{3})+|\d{3,5})(?=\s+records\b)', 'records'),
    (r'(?<![\d,])(?P<num>\d{1,3}(?:,\d{3})+|\d{3,5})(?=\s+items\b)', 'items'),
    (r'(?<![\d,])(?P<num>\d{1,3}(?:,\d{3})+|\d{3,5})(?=\s+entries\s+within\s+books\b)', 'book_entries'),
    (r'(?<![\d,])\((?P<num>\d{1,3}(?:,\d{3})+|\d{3,4})(?=\s+lines\))', 'character_lines'),
]


_PROSE_KEYS = {'transcripts', 'lines', 'cards', 'interactions', 'records',
               'items', 'book_entries', 'character_lines'}


def _count(key, num_text):
    value = C[key]
    return '{:,}'.format(value) if ',' in num_text else str(value)

# Legacy prose shapes kept for the two agents that used them before the
# registry existed. They stay until each agent owns its count-claim patterns
# (P1 template work); new agents get the generic shapes below.
LEGACY_PATS = {
    'eris': [
        (r'\b\d{3,4} canonical Eris', '{eris} canonical Eris'),
        (r'\(\d{3,4} Eris Morn lines\)', '({eris} Eris Morn lines)'),
        (r'\(\d{3,4} canonical Eris transcript lines\)',
         '({eris} canonical Eris transcript lines)'),
    ],
    'drifter': [
        (r'All \d+ Drifter quotes', 'All {drifter} Drifter quotes'),
        (r'canonical transcripts \(\d+ Drifter lines\)',
         'canonical transcripts ({drifter} Drifter lines)'),
        (r'\b\d{3,4} Drifter transcript lines in the database',
         '{drifter_exact} Drifter transcript lines in the database'),
        (r'\b\d{3,4} verified Drifter quotes', '{drifter} verified Drifter quotes'),
    ],
}


def persona_patterns(ident):
    """Generic count-claim shapes for an agent with no legacy patterns."""
    row = _roster.entry(ident) or {}
    name = row.get('name') or ident
    path = os.path.join(AGENT_REPOS.get(ident, ''), 'persona.json')
    if not os.path.isfile(path):
        return []
    canon = json.load(open(path, encoding='utf-8')).get('canon_lines')
    if canon is None:
        return []
    esc = re.escape(name)
    return [
        # Rewrite only the line count; the per-agent transcript count after
        # "across" is a different measure and must not become the DB total.
        (r'\d[\d,]*(?=\s+lines across\s+\d[\d,]*\s+transcripts)',
         str(canon)),
        (r'\|\s*Canonical lines\s*\|\s*\d[\d,]*\s*\|',
         '| Canonical lines | ' + str(canon) + ' |'),
        (r'\(\d[\d,]*\s+' + esc + r'\s+lines?\)',
         '(' + str(canon) + ' ' + name + ' lines)'),
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
SKILL = os.path.join(GRIMOIRE, 'skills', 'destiny-grimoire', 'SKILL.md')
DB_PATH = os.path.join(GRIMOIRE, 'db', 'grimoire.db')


def _count_live(conn, label):
    """Live row count for a table/view label, or None when it is no object."""
    object_name = (label.split('`')[1] if '`' in label else label).strip()
    try:
        return conn.execute(
            'SELECT COUNT(*) FROM "{}"'.format(object_name)).fetchone()[0]
    except sqlite3.Error:
        return None


def sync_skill_counts(text, db_path):
    """Rewrite the SKILL.md 'Data covering' tables from the live database.

    The skill ships to agents as the drop-in reference; a stale row count there
    misleads every consumer. Both tables (canon + taxonomy) are covered, and
    labels that are not live objects are left untouched.
    """
    head, sep, rest = text.partition('## Data covering\n\n')
    if not sep:
        return text
    end = rest.find('\n## ')
    section, tail = (rest, '') if end == -1 else (rest[:end], rest[end:])
    conn = sqlite3.connect('file:{}?mode=ro'.format(db_path), uri=True)
    out = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) == 3 and cells[1].isdigit():
            count = _count_live(conn, cells[0])
            if count is not None:
                line = '| {} | {} | {} |'.format(cells[0], count, cells[2])
        out.append(line)
    conn.close()
    return head + sep + '\n'.join(out) + '\n' + tail


FILES = []
for pat in [os.path.join(GRIMOIRE, '*.md'), os.path.join(GRIMOIRE, 'db', '*.md'),
            os.path.join(GRIMOIRE, 'skills', 'destiny-grimoire', '*.md'),
            os.path.join(GRIMOIRE, 'compendium', '*.md'),
            os.path.join(GRIMOIRE, 'docs', 'wiki', '*.md'),
            os.path.join(GRIMOIRE, 'docs', '*.md')]:
    FILES.extend(glob.glob(pat))
for repo in AGENT_REPOS.values():
    if not os.path.isdir(repo):
        continue
    for sub in ('', 'core', 'reference'):
        FILES.extend(glob.glob(os.path.join(repo, sub, '*.md')))

CHECK = '--check' in sys.argv
changes = []
for path in sorted(set(FILES)):
    if os.path.basename(path) in ('CHANGELOG.md', 'RELEASE.md'):
        continue
    # The unconditional prose rewrite is safe in the archive, where a bare
    # "<n> transcripts" always means the whole DB. Agent docs carry per-persona
    # measures (for example "456 lines across 33 transcripts"), so they only
    # get the explicit shapes above.
    pats = list(SHARED)
    if path.startswith(GRIMOIRE + os.sep):
        pats += list(SHARED_PROSE)
    for ident, repo in AGENT_REPOS.items():
        if path.startswith(repo + os.sep):
            pats += LEGACY_PATS.get(ident) or persona_patterns(ident)
            break
    s = open(path, encoding='utf-8').read()
    orig = s
    # Regions fenced by <!-- doc-sync:ignore --> ... <!-- /doc-sync:ignore -->
    # are passed through untouched: they carry hand-authored, context-dependent
    # counts (e.g. 'Destiny 1 visible: 123 transcripts...' is scoped to D1).
    segments = re.split(r'(<!--\s*doc-sync:ignore\s*-->.*?<!--\s*/doc-sync:ignore\s*-->)', s, flags=re.S)
    kept = []
    for seg in segments:
        if seg.startswith('<!--'):
            kept.append(seg)
            continue
        for rx, arg in pats:
            if isinstance(arg, str) and arg in _PROSE_KEYS:
                seg = re.sub(rx, lambda m: ('(' if m.group(0).startswith('(') else '') + _count(arg, m.group('num')), seg)
            else:
                seg = re.sub(rx, lambda m: arg.format(**C), seg)
        kept.append(seg)
    s = ''.join(kept)
    if path == README:
        s = sync_inside_table(s, DB_PATH)
    elif path == SKILL:
        s = sync_skill_counts(s, DB_PATH)
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
