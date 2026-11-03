#!/usr/bin/env python3
"""Agent query interface for the Destiny Grimoire database.

Designed for LLM agents: small bounded outputs, snippet-first search, JSON mode,
and quote verification. Every command exits non-zero on failure.

Usage:
  query.py search "<term>" [--type books|transcripts|grimoire|interactions|items|records]
                           [--limit N] [--json] [--full]
  query.py character "<name>" [--about <term>] [--limit N] [--all] [--json]
  query.py item "<slug>" [--json]
  query.py verify "<quote>" [--json]
  query.py list books|characters|speakers|records [--limit N] [--json]
  query.py stats [--json]
"""
import argparse
import json
import os
import re
import sqlite3
import sys

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grimoire.db')
TYPE_TO_SOURCE = {
    'books': 'book_entry', 'transcripts': 'transcript_line', 'grimoire': 'grimoire_card',
    'interactions': 'interaction', 'items': 'item', 'records': 'record',
}


def norm(s):
    s = s.lower().replace('\u2026', '...').replace('\u2019', "'").replace('\u2014', '-').replace('\u2013', '-')
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def get_conn():
    if not os.path.exists(DB):
        sys.stderr.write('FAIL: database not found at %s - bootstrap: ./setup.sh, or python3 db/migrate.py (see README)\n' % DB)
        sys.exit(1)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def emit(rows, as_json, human_fn):
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=None, separators=(',', ':')))
    else:
        human_fn(rows)


def cmd_search(args):
    conn = get_conn()
    where = 'fts MATCH ?'
    params = [args.query]
    if args.type:
        where += ' AND source = ?'
        params.append(TYPE_TO_SOURCE[args.type])
    params.append(args.limit)
    if args.full:
        cols = 'title, speaker, text, source'
        rows = conn.execute(f'SELECT {cols} FROM fts WHERE {where} LIMIT ?', params).fetchall()
        out = [dict(r) for r in rows]
        emit(out, args.json, lambda rs: [print(f"[{r['source']}] {r['title']}: {r['text'][:200]}") for r in rs])
    else:
        # snippet: bounded context around the match, token-efficient by default
        cols = "title, speaker, source, snippet(fts, 1, '[', ']', '…', 10) AS snip"
        rows = conn.execute(f'SELECT {cols} FROM fts WHERE {where} LIMIT ?', params).fetchall()
        out = [dict(r) for r in rows]
        emit(out, args.json, lambda rs: [print(f"[{r['source']}] {r['title']}: {r['snip']}") for r in rs])
    if not args.json:
        print(f'\n{len(out)} results')
    conn.close()
    return 0 if out else 1


def cmd_character(args):
    conn = get_conn()
    name = args.name
    ch = conn.execute("SELECT id, name, slug FROM characters WHERE name LIKE ? OR slug LIKE ?",
                      (f'%{name}%', f'%{name.lower().replace(" ", "-")}%')).fetchone()
    pattern = f'%{args.about.lower()}%' if args.about else None
    if args.all:
        # every canonical transcript line by this speaker (richer than curated quotes)
        speaker_like = f'%{name}%'
        if pattern:
            rows = conn.execute(
                "SELECT line AS text, speaker, '' AS source_slug FROM transcript_lines "
                "WHERE speaker LIKE ? AND is_stage_dir=0 AND LOWER(line) LIKE ? LIMIT ?",
                (speaker_like, pattern, args.limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT line AS text, speaker, '' AS source_slug FROM transcript_lines "
                "WHERE speaker LIKE ? AND is_stage_dir=0 LIMIT ?",
                (speaker_like, args.limit)).fetchall()
        header = f'=== {name} (transcript lines) ==='
    else:
        if not ch:
            print(f'Character not found: {name}', file=sys.stderr)
            conn.close()
            return 1
        header = f"=== {ch['name']} ({ch['slug']}) ==="
        if pattern:
            rows = conn.execute(
                "SELECT text, '' AS speaker, source_slug FROM character_lines "
                "WHERE character_id = ? AND LOWER(text) LIKE ? LIMIT ?",
                (ch['id'], pattern, args.limit)).fetchall()
        else:
            rows = conn.execute(
                "SELECT text, '' AS speaker, source_slug FROM character_lines WHERE character_id = ? LIMIT ?",
                (ch['id'], args.limit)).fetchall()
    out = [dict(r) for r in rows]
    if args.json:
        print(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    else:
        print(header)
        for r in out:
            src = f" ({r['source_slug']})" if r['source_slug'] else ''
            print(f'  - "{r["text"]}"{src}')
        print(f'\n{len(out)} lines')
    conn.close()
    return 0 if out else 1


def cmd_item(args):
    conn = get_conn()
    row = conn.execute('SELECT * FROM items WHERE slug = ?', (args.slug,)).fetchone()
    if not row:
        print(f'Item not found: {args.slug}', file=sys.stderr)
        conn.close()
        return 1
    if args.json:
        print(json.dumps(dict(row), ensure_ascii=False, separators=(',', ':')))
    else:
        print(f"=== {row['title']} ===")
        print(f"Type: {row['item_type']}")
        print(f"Release: {row['release']}")
        print(f"Source: {row['source_url']}")
        print(f"\n{row['text']}")
    conn.close()
    return 0


def cmd_verify(args):
    """Check whether a quoted string exists in canon. Returns speaker/source."""
    conn = get_conn()
    nq = norm(args.quote)
    if not nq:
        print('Empty quote', file=sys.stderr)
        conn.close()
        return 1
    hits = []
    # transcript lines carry no slug; provenance comes from the parent transcript
    rows = conn.execute(
        "SELECT t.slug, tl.speaker FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id "
        "WHERE tl.norm_line LIKE ? LIMIT 3", (f'%{nq}%',)).fetchall()
    for r in rows:
        hits.append({'source': 'transcript', 'slug': r[0], 'speaker': r[1]})
    # book entries carry no slug; provenance comes from the parent book
    rows = conn.execute(
        "SELECT b.slug FROM book_entries e JOIN books b ON b.id = e.book_id "
        "WHERE e.norm_text LIKE ? LIMIT 3", (f'%{nq}%',)).fetchall()
    for r in rows:
        hits.append({'source': 'book', 'slug': r[0], 'speaker': ''})
    plain = [
        ('grimoire_cards', 'norm_body', 'grimoire_card'),
        ('interactions', 'norm_text', 'interaction'),
        ('items', 'norm_text', 'item'),
        ('records', 'norm_body', 'record'),
    ]
    for tbl, nrm, source in plain:
        if tbl == 'interactions':
            rows = conn.execute(f'SELECT slug, speaker FROM {tbl} WHERE {nrm} LIKE ? LIMIT 3', (f'%{nq}%',)).fetchall()
            for r in rows:
                hits.append({'source': source, 'slug': r[0], 'speaker': r[1]})
        else:
            rows = conn.execute(f'SELECT slug FROM {tbl} WHERE {nrm} LIKE ? LIMIT 3', (f'%{nq}%',)).fetchall()
            for r in rows:
                hits.append({'source': source, 'slug': r[0], 'speaker': ''})
    conn.close()
    # dedupe identical provenance rows (same slug can repeat lines)
    seen, uniq = set(), []
    for h in hits:
        key = (h['source'], h['slug'], h['speaker'])
        if key not in seen:
            seen.add(key)
            uniq.append(h)
    hits = uniq
    if args.json:
        print(json.dumps({'quote': args.quote, 'verified': bool(hits), 'matches': hits},
                         ensure_ascii=False, separators=(',', ':')))
    else:
        if hits:
            print(f'VERIFIED: "{args.quote}"')
            for h in hits:
                sp = f" | speaker: {h['speaker']}" if h['speaker'] else ''
                print(f"  [{h['source']}] {h['slug']}{sp}")
        else:
            print(f'NOT FOUND: "{args.quote}"')
    return 0 if hits else 1


def cmd_list(args):
    conn = get_conn()
    if args.kind == 'books':
        rows = conn.execute('SELECT slug, title, entry_count FROM books ORDER BY title LIMIT ?', (args.limit,)).fetchall()
    elif args.kind == 'characters':
        rows = conn.execute('SELECT slug, name FROM characters ORDER BY name LIMIT ?', (args.limit,)).fetchall()
    elif args.kind == 'speakers':
        rows = conn.execute("SELECT speaker, COUNT(*) AS lines FROM transcript_lines WHERE speaker NOT IN ('Narration','Cutscene') GROUP BY speaker ORDER BY 2 DESC LIMIT ?", (args.limit,)).fetchall()
    else:
        rows = conn.execute('SELECT slug, title FROM records ORDER BY title LIMIT ?', (args.limit,)).fetchall()
    out = [dict(r) for r in rows]
    if args.json:
        print(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    else:
        if out:
            cols = list(out[0].keys())
            print(' | '.join(cols))
            for r in out:
                print(' | '.join(str(r[c]) for c in cols))
        print(f'\n{len(out)} rows')
    conn.close()
    return 0 if out else 1


def cmd_stats(args):
    conn = get_conn()
    counts = {}
    for t in ['books', 'book_entries', 'transcripts', 'transcript_lines', 'grimoire_cards',
              'interactions', 'items', 'records', 'characters', 'character_lines', 'fts']:
        counts[t] = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
    if args.json:
        print(json.dumps(counts, separators=(',', ':')))
        conn.close()
        return 0
    print('=== Destiny Grimoire Database Stats ===')
    for t, c in counts.items():
        print(f'  {t}: {c}')
    print('\n=== Top item types ===')
    for r in conn.execute("SELECT item_type, COUNT(*) FROM items WHERE item_type != '' GROUP BY item_type ORDER BY 2 DESC LIMIT 10").fetchall():
        print(f'  {r[0]}: {r[1]}')
    print('\n=== Top speakers ===')
    for r in conn.execute("SELECT speaker, COUNT(*) FROM transcript_lines WHERE speaker != '' GROUP BY speaker ORDER BY 2 DESC LIMIT 10").fetchall():
        print(f'  {r[0]}: {r[1]}')
    conn.close()
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Query the Destiny Grimoire database')
    sub = parser.add_subparsers(dest='cmd')

    s = sub.add_parser('search', help='Full-text search (snippet by default)')
    s.add_argument('query')
    s.add_argument('--type', choices=list(TYPE_TO_SOURCE.keys()))
    s.add_argument('--limit', type=int, default=10)
    s.add_argument('--json', action='store_true')
    s.add_argument('--full', action='store_true', help='full text instead of snippets')
    s.set_defaults(func=cmd_search)

    c = sub.add_parser('character', help='Character lines')
    c.add_argument('name')
    c.add_argument('--about', help='only lines mentioning this term')
    c.add_argument('--all', action='store_true', help='all transcript lines, not just curated quotes')
    c.add_argument('--limit', type=int, default=20)
    c.add_argument('--json', action='store_true')
    c.set_defaults(func=cmd_character)

    i = sub.add_parser('item', help='Item details')
    i.add_argument('slug')
    i.add_argument('--json', action='store_true')
    i.set_defaults(func=cmd_item)

    v = sub.add_parser('verify', help='Check a quote against canon (exit 1 if not found)')
    v.add_argument('quote')
    v.add_argument('--json', action='store_true')
    v.set_defaults(func=cmd_verify)

    l = sub.add_parser('list', help='Cheap discovery listings')
    l.add_argument('kind', choices=['books', 'characters', 'speakers', 'records'])
    l.add_argument('--limit', type=int, default=50)
    l.add_argument('--json', action='store_true')
    l.set_defaults(func=cmd_list)

    st = sub.add_parser('stats', help='Database statistics')
    st.add_argument('--json', action='store_true')
    st.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(0)
    sys.exit(args.func(args))
