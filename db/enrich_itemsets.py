#!/usr/bin/env python3
"""Additive item-set classification from the Bungie manifest.

Run after `db/migrate.py`:

    python3 db/enrich_itemsets.py [--apply]

Without --apply it reports the yield only. With --apply it fills
`item_classification` for matching items that are still `unknown`.

Only curated, high-confidence set mappings are used. Conflicting or uncertain
sets are left alone.
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from migrate import DB_PATH as DEFAULT_DB  # noqa: E402

DB_PATH = os.environ.get('GRIMOIRE_DB') or DEFAULT_DB
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, 'archive', 'data', 'manifest')

# set name -> (season_slug, event_slug, expansion_slug)
SET_MAP = {
    'Iron Panoply Set': (None, 'iron-banner', None),
    'Iron Battalion Set': (None, 'iron-banner', None),
    'Great Hunt': ('season-4', None, 'forsaken'),
    "Legacy's Oath": ('season-of-the-hunt', None, 'beyond-light'),
    "Atheon's Memory": ('season-of-the-splicer', None, 'the-witch-queen'),
    "Oryx's Memory": ('season-of-plunder', None, 'the-witch-queen'),
    "Nezarec's Nightmare": ('season-of-defiance', None, 'lightfall'),
    "Crota's Memory": ('season-of-the-witch', None, 'lightfall'),
    'Resonant Fury': ('season-of-the-risen', None, 'the-witch-queen'),
    'Kentarch 3': ('season-of-the-haunted', None, 'the-witch-queen'),
    "Techeun's Regalia": ('season-of-the-lost', None, 'beyond-light'),
    'Deep Explorer': ('season-of-the-deep', None, 'lightfall'),
    'Seventh Seraph': ('season-of-the-seraph', None, 'the-witch-queen'),
    'Crystocrene': (None, None, 'beyond-light'),
    'First Ascent': (None, None, 'beyond-light'),
    'Reverie Dawn': ('season-4', None, 'forsaken'),
    'Dreambane': ('season-of-the-undying', None, 'shadowkeep'),
    'Wildwood': (None, None, 'destiny-2'),
    'Exodus Down': (None, None, 'destiny-2'),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS item_sets (
    hash INTEGER PRIMARY KEY,
    name TEXT,
    season_slug TEXT,
    event_slug TEXT,
    expansion_slug TEXT,
    evidence TEXT
);
CREATE TABLE IF NOT EXISTS item_set_members (
    set_hash INTEGER NOT NULL,
    item_hash INTEGER NOT NULL,
    item_title TEXT,
    item_id INTEGER,
    matched INTEGER DEFAULT 0,
    PRIMARY KEY (set_hash, item_hash)
);
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    sets = json.load(open(os.path.join(MAN, 'DestinyEquipableItemSetDefinition.json'), encoding='utf-8'))
    items = json.load(open(os.path.join(MAN, 'DestinyInventoryItemDefinition.json'), encoding='utf-8'))
    names = {}
    for h, d in items.items():
        n = (d.get('displayProperties') or {}).get('name')
        if n:
            names[int(h)] = n

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.execute('DELETE FROM item_sets')
    conn.execute('DELETE FROM item_set_members')
    matched_total = 0
    set_count = 0
    for d in sets.values():
        name = (d.get('displayProperties') or {}).get('name') or ''
        if name not in SET_MAP:
            continue
        season, event, expansion = SET_MAP[name]
        set_hash = int(d['hash'])
        conn.execute('INSERT INTO item_sets (hash,name,season_slug,event_slug,expansion_slug,evidence) '
                     'VALUES (?,?,?,?,?,?)',
                     (set_hash, name, season, event, expansion, 'curated_set_map'))
        set_count += 1
        member_ids = []
        for item_hash in d.get('setItems', []):
            title = names.get(int(item_hash), '')
            item_ids = [r[0] for r in conn.execute('SELECT id FROM items WHERE title=?', (title,)).fetchall()]
            if item_ids:
                matched_total += 1
            for item_id in item_ids:
                member_ids.append(item_id)
            conn.execute('INSERT INTO item_set_members '
                         '(set_hash,item_hash,item_title,item_id,matched) VALUES (?,?,?,?,?)',
                         (set_hash, item_hash, title, item_ids[0] if item_ids else None,
                          1 if item_ids else 0))
        if args.apply and member_ids:
            q = ','.join('?' * len(member_ids))
            conn.execute(
                f'UPDATE item_classification SET season_slug=?, event_slug=?, expansion_slug=?, '
                f'confidence="derived", evidence=? WHERE item_id IN ({q}) AND confidence="unknown"',
                [season, event, expansion, f'item_set:{name}'] + member_ids)
    if args.apply:
        conn.commit()
    print(f'sets mapped: {set_count}, member titles resolved: {matched_total}, '
          f'apply={args.apply}')
    conn.close()


if __name__ == '__main__':
    main()
