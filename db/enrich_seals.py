#!/usr/bin/env python3
"""Additive seal/triumph tree from the Bungie manifest.

Run after `db/migrate.py`:

    python3 db/enrich_seals.py

Builds `seals` (71 seal presentation nodes) and `seal_records` (their triumph
records). Does not touch the curated `records` table.
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from migrate import DB_PATH as DEFAULT_DB  # noqa: E402

DB_PATH = os.environ.get('GRIMOIRE_DB') or DEFAULT_DB
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, 'archive', 'data', 'manifest')

SCHEMA = """
CREATE TABLE IF NOT EXISTS seals (
    hash INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT,
    completion_record_hash INTEGER,
    node_type INTEGER
);
CREATE TABLE IF NOT EXISTS seal_records (
    seal_hash INTEGER NOT NULL,
    record_hash INTEGER NOT NULL,
    name TEXT,
    description TEXT,
    lore_hash INTEGER,
    PRIMARY KEY (seal_hash, record_hash)
);
CREATE INDEX IF NOT EXISTS idx_seal_records_seal ON seal_records(seal_hash);
"""


def main():
    nodes = json.load(open(os.path.join(MAN, 'DestinyPresentationNodeDefinition.json'), encoding='utf-8'))
    records = json.load(open(os.path.join(MAN, 'DestinyRecordDefinition.json'), encoding='utf-8'))
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.execute('DELETE FROM seal_records')
    conn.execute('DELETE FROM seals')

    seals = 0
    rows = 0
    for node in nodes.values():
        if node.get('nodeType') != 3 or not node.get('completionRecordHash'):
            continue
        name = (node.get('displayProperties') or {}).get('name') or ''
        desc = (node.get('displayProperties') or {}).get('description') or ''
        if not name:
            continue
        conn.execute('INSERT OR REPLACE INTO seals (hash,name,description,completion_record_hash,node_type) '
                     'VALUES (?,?,?,?,?)',
                     (node['hash'], name, desc, node['completionRecordHash'], node['nodeType']))
        seals += 1
        for child in (node.get('children') or {}).get('records', []):
            rh = child.get('recordHash')
            rec = records.get(str(rh)) if rh else None
            if not rec:
                continue
            conn.execute('INSERT OR REPLACE INTO seal_records '
                         '(seal_hash,record_hash,name,description,lore_hash) VALUES (?,?,?,?,?)',
                         (node['hash'], rh,
                          (rec.get('displayProperties') or {}).get('name') or '',
                          (rec.get('displayProperties') or {}).get('description') or '',
                          rec.get('loreHash')))
            rows += 1
    conn.execute("INSERT OR REPLACE INTO meta (key,value) VALUES ('seals',?)", (str(seals),))
    conn.execute("INSERT OR REPLACE INTO meta (key,value) VALUES ('seal_records',?)", (str(rows),))
    conn.commit()
    conn.execute('PRAGMA journal_mode=DELETE')
    conn.execute('VACUUM')
    conn.close()
    print(f'seals: {seals}, seal records: {rows}')


if __name__ == '__main__':
    main()
