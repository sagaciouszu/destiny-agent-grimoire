#!/usr/bin/env python3
"""Build a slim agent database: lore text without item/card bulk.

Keeps books, transcripts, interactions, records, characters and both
verification indexes. Drops items, grimoire cards and their indexes.

Usage: python3 db/build-slim.py [output]   (default: db/grimoire-slim.db)
"""
import os
import shutil
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'grimoire.db')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'grimoire-slim.db')

if not os.path.exists(SRC):
    sys.exit('source database missing; run python3 db/migrate.py')
shutil.copyfile(SRC, OUT)
conn = sqlite3.connect(OUT)
conn.execute("DELETE FROM fts WHERE source IN ('item', 'grimoire_card')")
conn.execute("DELETE FROM verify_fts WHERE source IN ('item', 'grimoire_card')")
conn.execute('DROP TABLE IF EXISTS item_title_fts')
conn.execute('DELETE FROM items')
conn.execute('DELETE FROM grimoire_cards')
conn.commit()
conn.execute('PRAGMA journal_mode=DELETE')
conn.execute('VACUUM')
counts = {t: conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
          for t in ('books', 'book_entries', 'transcripts', 'transcript_lines',
                    'interactions', 'records', 'characters', 'character_lines', 'fts', 'verify_fts')}
conn.close()
print(f'wrote {OUT} ({os.path.getsize(OUT) / 1048576:.0f} MB)')
print(' '.join(f'{k}={v}' for k, v in counts.items()))
