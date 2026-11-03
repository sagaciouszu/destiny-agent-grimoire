#!/usr/bin/env python3
"""Cross-validate the database against committed sources.

Run: python3 tests/db-source-crosscheck.py
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, 'db', 'grimoire.db')
PASS = FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f'  ✓ {name}')
        PASS += 1
    except Exception as e:
        print(f'  ✗ {name}: {type(e).__name__}: {e}')
        FAIL += 1


def files(d):
    return {f[:-3] for f in os.listdir(os.path.join(ROOT, 'source', d)) if f.endswith('.md')}


def slugs(conn, table):
    return {r[0] for r in conn.execute(f'SELECT slug FROM {table}')}


conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
print('database/source cross-check')

def book_names():
    # book slugs are stored as book-<source filename>
    return {s.removeprefix('book-') for s in slugs(conn, 'books')}

check('books match source/books',
      lambda: (_ for _ in ()).throw(
          AssertionError(f'missing files: {sorted(book_names() - files("books"))[:5]}'))
      if book_names() != files('books') else None)
for table, folder in (('grimoire_cards', 'cards'), ('records', 'records')):
    check(f'{table} slugs match source/{folder}',
          lambda t=table, f=folder: (_ for _ in ()).throw(
              AssertionError(f'missing files: {sorted(slugs(conn, t) - files(f))[:5]}'))
          if slugs(conn, t) != files(f) else None)

def transcript_files():
    return files('transcripts') - {'index'}

check('transcript source files all exist in DB',
      lambda: (_ for _ in ()).throw(
          AssertionError(f'missing in DB: {sorted(transcript_files() - slugs(conn, "transcripts"))[:5]}'))
      if not transcript_files() <= slugs(conn, 'transcripts') else None)

check('DB transcript count exceeds source files (web/cutscenes)',
      lambda: (_ for _ in ()).throw(AssertionError('no web/cutscene transcripts'))
      if conn.execute('SELECT COUNT(*) FROM transcripts').fetchone()[0] <= len(transcript_files()) else None)

check('every character has a compendium file',
      lambda: (_ for _ in ()).throw(AssertionError('missing compendium files'))
      if any(not os.path.exists(os.path.join(ROOT, 'compendium', 'characters', f'{s}.md'))
             for s in slugs(conn, 'characters')) else None)

def urls():
    rows = conn.execute("SELECT slug, source_url FROM grimoire_cards").fetchall()
    bad = [s for s, u in rows if not u or not re.match(r'^https://www\.ishtar-collective\.net/', u)]
    assert not bad, f'bad card URLs: {bad[:5]}'

check('card provenance URLs are canonical', urls)

def transcript_urls():
    rows = conn.execute("SELECT slug, source_url FROM transcripts").fetchall()
    bad = [s for s, u in rows if u and not re.match(r'^https?://', u)]
    assert not bad, f'bad transcript URLs: {bad[:5]}'

check('transcript URLs are well formed', transcript_urls)

def counts():
    books = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    entries = conn.execute('SELECT COUNT(*) FROM book_entries').fetchone()[0]
    cards = conn.execute('SELECT COUNT(*) FROM grimoire_cards').fetchone()[0]
    records = conn.execute('SELECT COUNT(*) FROM records').fetchone()[0]
    assert books == 110 and entries == 1158 and cards == 2889 and records == 71, (books, entries, cards, records)

check('documented content counts hold', counts)

def indexes():
    assert conn.execute('SELECT COUNT(*) FROM verify_fts').fetchone()[0] == 120731
    expected = conn.execute(
        "SELECT (SELECT COUNT(*) FROM transcript_lines)+(SELECT COUNT(*) FROM book_entries)"
        "+(SELECT COUNT(*) FROM grimoire_cards)+(SELECT COUNT(*) FROM interactions)"
        "+(SELECT COUNT(*) FROM items WHERE text!='')+(SELECT COUNT(*) FROM records)").fetchone()[0]
    assert conn.execute('SELECT COUNT(*) FROM fts').fetchone()[0] == expected

check('search and verification indexes are complete', indexes)

conn.close()
print(f'\nPassed: {PASS} | Failed: {FAIL}')
sys.exit(1 if FAIL else 0)
