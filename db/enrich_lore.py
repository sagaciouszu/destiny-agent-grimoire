#!/usr/bin/env python3
"""Additive lore-entry enrichment from the Bungie manifest.

Run after `db/migrate.py`:

    python3 db/enrich_lore.py

Reads archive/data/manifest/lore_entries.jsonl (local, gitignored), fills the
`lore_entries` and `lore_entry_items` tables, and indexes non-duplicate entries
in `fts` and `verify_fts` as source `lore_entry`.

Existing canon is never modified. Entries whose body already exists in
book_entries or items are marked `is_duplicate=1` and kept out of the search
indexes so they do not double up.
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from migrate import DB_PATH as DEFAULT_DB, norm_text  # noqa: E402

DB_PATH = os.environ.get('GRIMOIRE_DB') or DEFAULT_DB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGING = os.path.join(ROOT, 'archive', 'data', 'manifest', 'lore_entries.jsonl')

SCHEMA = """
CREATE TABLE IF NOT EXISTS lore_entries (
    id INTEGER PRIMARY KEY,
    hash INTEGER UNIQUE NOT NULL,
    title TEXT,
    subtitle TEXT,
    body TEXT,
    norm_body TEXT,
    source TEXT DEFAULT 'bungie_manifest',
    source_url TEXT,
    is_duplicate INTEGER DEFAULT 0,
    duplicate_of TEXT
);
CREATE INDEX IF NOT EXISTS idx_lore_norm ON lore_entries(norm_body);
CREATE TABLE IF NOT EXISTS lore_entry_items (
    lore_hash INTEGER NOT NULL,
    item_title TEXT NOT NULL,
    PRIMARY KEY (lore_hash, item_title)
);
CREATE INDEX IF NOT EXISTS idx_lore_items_title ON lore_entry_items(item_title);
"""


def main():
    if not os.path.exists(STAGING):
        raise SystemExit(f'missing {STAGING}; run scripts/build-lore-staging.py')
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    # Idempotent refresh: clear previous enrichment only.
    conn.execute("DELETE FROM fts WHERE source='lore_entry'")
    conn.execute("DELETE FROM verify_fts WHERE source='lore_entry'")
    conn.execute('DELETE FROM lore_entry_items')
    conn.execute('DELETE FROM lore_entries')

    book_norm = {r[0] for r in conn.execute(
        'SELECT norm_text FROM book_entries WHERE norm_text != ""')}
    item_norm = {r[0] for r in conn.execute(
        'SELECT norm_text FROM items WHERE norm_text != ""')}
    other_norm = {r[0] for r in conn.execute(
        'SELECT norm_body FROM grimoire_cards WHERE norm_body != ""')}
    other_norm |= {r[0] for r in conn.execute(
        'SELECT norm_body FROM records WHERE norm_body != ""')}
    other_norm |= {r[0] for r in conn.execute(
        'SELECT norm_text FROM interactions WHERE norm_text != ""')}

    rows = []
    for line in open(STAGING, encoding='utf-8'):
        try:
            d = json.loads(line)
        except Exception:
            continue
        body = (d.get('body') or '').strip()
        if not body:
            continue
        nb = norm_text(body)
        dup = None
        if nb in book_norm:
            dup = 'book'
        elif nb in item_norm:
            dup = 'item'
        elif nb in other_norm:
            dup = 'other'
        rows.append((d['hash'], d.get('title') or '', d.get('subtitle') or '',
                     body, nb, dup, d.get('item_titles') or []))

    for h, title, subtitle, body, nb, dup, titles in rows:
        conn.execute(
            'INSERT INTO lore_entries '
            '(hash,title,subtitle,body,norm_body,source,source_url,is_duplicate,duplicate_of) '
            'VALUES (?,?,?,?,?,?,?,?,?)',
            (h, title, subtitle, body, nb, 'bungie_manifest',
             f'https://www.bungie.net/Platform/Destiny2/Manifest/DestinyLoreDefinition/{h}/',
             1 if dup else 0, dup or ''))
        for t in titles:
            conn.execute('INSERT OR IGNORE INTO lore_entry_items (lore_hash,item_title) VALUES (?,?)',
                         (h, t))

    fts_id = conn.execute('SELECT COALESCE(MAX(rowid),0) FROM fts').fetchone()[0]
    v_id = 0
    for h, title, subtitle, body, nb, dup, titles in rows:
        if dup:
            continue
        fts_id += 1
        conn.execute(
            'INSERT INTO fts (rowid,title,text,speaker,body,source,source_slug) '
            'VALUES (?,?,?,?,?,?,?)',
            (fts_id, title, body, '', '', 'lore_entry', f'lore-{h}'))
        conn.execute(
            'INSERT INTO verify_fts (norm,source,slug,speaker) VALUES (?,?,?,?)',
            (nb, 'lore_entry', f'lore-{h}', ''))
        v_id += 1

    unique = len(rows) - sum(1 for r in rows if r[5])
    conn.execute("INSERT OR REPLACE INTO meta (key,value) VALUES ('lore_entries',?)", (str(len(rows)),))
    conn.execute("INSERT OR REPLACE INTO meta (key,value) VALUES ('lore_entries_indexed',?)", (str(unique),))
    conn.execute("INSERT OR REPLACE INTO meta (key,value) VALUES ('lore_entry_items',?)",
                 (str(conn.execute('SELECT COUNT(*) FROM lore_entry_items').fetchone()[0]),))
    conn.commit()
    conn.execute('PRAGMA journal_mode=DELETE')
    conn.execute('VACUUM')
    conn.close()
    print(f'lore entries: {len(rows)} total, {unique} indexed, '
          f'{len(rows)-unique} duplicates skipped')


if __name__ == '__main__':
    main()
