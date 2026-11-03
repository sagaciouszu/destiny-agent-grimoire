#!/usr/bin/env python3
"""Audit item provenance and type coverage.

Run: python3 tests/item-audit.py
Exit 1 on duplicate slugs, empty titles, malformed URLs, or missing types.
"""
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
DB = os.path.join(os.path.dirname(HERE), 'db', 'grimoire.db')
conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
q = lambda sql: conn.execute(sql).fetchone()[0]

checks = []
checks.append(('duplicate slugs', q('SELECT COUNT(*)-COUNT(DISTINCT slug) FROM items') == 0))
checks.append(('empty titles', q("SELECT COUNT(*) FROM items WHERE title='' OR title IS NULL") == 0))

bad_url = q("SELECT COUNT(*) FROM items WHERE source_url != '' AND source_url NOT LIKE 'https://www.ishtar-collective.net/%'")
checks.append(('malformed source URLs', bad_url == 0))
checks.append(('unresolved text rows', q("SELECT COUNT(*) FROM items WHERE text IS NULL") == 0))

print('item audit')
failed = 0
for name, ok in checks:
    print(f"  {'✓' if ok else '✗'} {name}")
    failed += 0 if ok else 1
print(f"  info: items={q('SELECT COUNT(*) FROM items')} "
      f"stat_only={q("SELECT COUNT(*) FROM items WHERE text=''")} "
      f"no_type={q("SELECT COUNT(*) FROM items WHERE item_type=''")} "
      f"no_release={q("SELECT COUNT(*) FROM items WHERE release=''")}")
conn.close()
print(f"\nFailed: {failed}")
sys.exit(1 if failed else 0)
