#!/usr/bin/env python3
"""Agent query interface for the Destiny Grimoire database.

Usage:
  python3 db/query.py search "<keyword>" [--type books|transcripts|grimoire|interactions|items|records] [--limit N]
  python3 db/query.py character "<name>" [--limit N]
  python3 db/query.py item "<slug>" 
  python3 db/query.py stats
"""
import sqlite3, sys, os, argparse

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grimoire.db')

def get_conn():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def cmd_search(args):
    conn = get_conn()
    q = args.query
    type_filter = args.type
    limit = args.limit
    if type_filter:
        # map type to table
        table_map = {
            'books': 'book_entries', 'transcripts': 'transcript_lines',
            'grimoire': 'grimoire_cards', 'interactions': 'interactions',
            'items': 'items', 'records': 'records'
        }
        tbl = table_map.get(type_filter, 'fts')
        rows = conn.execute(
            f"SELECT rowid, title, speaker, text FROM fts WHERE fts MATCH ? AND rowid IN (SELECT rowid FROM {tbl}) LIMIT ?",
            (q, limit)).fetchall()
    else:
        rows = conn.execute(
            "SELECT rowid, title, speaker, text FROM fts WHERE fts MATCH ? LIMIT ?",
            (q, limit)).fetchall()
    for r in rows:
        sp = f" [{r['speaker']}]" if r['speaker'] else ''
        print(f"[{r['rowid']}] {r['title']}{sp}: {r['text'][:200]}")
    print(f"\n{len(rows)} results")
    conn.close()

def cmd_character(args):
    conn = get_conn()
    name = args.name
    # Find character
    ch = conn.execute("SELECT id, name, slug FROM characters WHERE name LIKE ? OR slug LIKE ?",
                      (f'%{name}%', f'%{name.lower().replace(" ","-")}%')).fetchone()
    if not ch:
        print(f"Character not found: {name}")
        conn.close()
        return
    print(f"=== {ch['name']} ({ch['slug']}) ===")
    lines = conn.execute(
        "SELECT cl.text, cl.source_type, cl.source_slug FROM character_lines cl WHERE cl.character_id = ? LIMIT ?",
        (ch['id'], args.limit)).fetchall()
    for l in lines:
        print(f"  - \"{l['text']}\" ({l['source_slug']})")
    print(f"\n{len(lines)} lines")
    conn.close()

def cmd_item(args):
    conn = get_conn()
    row = conn.execute("SELECT * FROM items WHERE slug = ?", (args.slug,)).fetchone()
    if not row:
        print(f"Item not found: {args.slug}")
        conn.close()
        return
    print(f"=== {row['title']} ===")
    print(f"Type: {row['item_type']}")
    print(f"Release: {row['release']}")
    print(f"Source: {row['source_url']}")
    print(f"\n{row['text']}")
    conn.close()

def cmd_stats(args):
    conn = get_conn()
    print("=== Destiny Grimoire Database Stats ===")
    for t in ['books','book_entries','transcripts','transcript_lines','grimoire_cards',
              'interactions','items','records','characters','character_lines','fts']:
        c = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        print(f"  {t}: {c}")
    print("\n=== Top item types ===")
    for r in conn.execute("SELECT item_type, COUNT(*) FROM items WHERE item_type != '' GROUP BY item_type ORDER BY 2 DESC LIMIT 10").fetchall():
        print(f"  {r[0]}: {r[1]}")
    print("\n=== Top speakers ===")
    for r in conn.execute("SELECT speaker, COUNT(*) FROM transcript_lines WHERE speaker != '' GROUP BY speaker ORDER BY 2 DESC LIMIT 10").fetchall():
        print(f"  {r[0]}: {r[1]}")
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Query the Destiny Grimoire database')
    sub = parser.add_subparsers(dest='cmd')
    
    s = sub.add_parser('search', help='Full-text search')
    s.add_argument('query')
    s.add_argument('--type', choices=['books','transcripts','grimoire','interactions','items','records'])
    s.add_argument('--limit', type=int, default=10)
    s.set_defaults(func=cmd_search)
    
    c = sub.add_parser('character', help='Character lines')
    c.add_argument('name')
    c.add_argument('--limit', type=int, default=20)
    c.set_defaults(func=cmd_character)
    
    i = sub.add_parser('item', help='Item details')
    i.add_argument('slug')
    i.set_defaults(func=cmd_item)
    
    st = sub.add_parser('stats', help='Database statistics')
    st.set_defaults(func=cmd_stats)
    
    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
    else:
        args.func(args)
