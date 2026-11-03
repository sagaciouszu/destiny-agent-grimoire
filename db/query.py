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
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import api  # noqa: E402

norm = api.norm
TYPE_TO_SOURCE = api.TYPE_TO_SOURCE


def emit(rows, as_json, human_fn):
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=None, separators=(',', ':')))
    else:
        human_fn(rows)


def cmd_search(args):
    out = api.search(args.query, type=args.type, limit=args.limit, full=args.full)
    if args.full:
        emit(out, args.json, lambda rs: [print(f"[{r['source']}] {r['title']}: {r['text'][:200]}") for r in rs])
    else:
        emit(out, args.json, lambda rs: [print(f"[{r['source']}] {r['title']}: {r['snip']}") for r in rs])
    if not args.json:
        print(f'\n{len(out)} results')
    return 0 if out else 1


def cmd_character(args):
    res = api.character(args.name, about=args.about, all_lines=args.all, limit=args.limit)
    if res is None:
        print(f'Character not found: {args.name}', file=sys.stderr)
        return 1
    out = res['rows']
    if args.json:
        print(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    else:
        print(res['header'])
        for r in out:
            src = f" ({r['source_slug']})" if r['source_slug'] else ''
            print(f'  - "{r["text"]}"{src}')
        print(f'\n{len(out)} lines')
    return 0 if out else 1


def cmd_item(args):
    row = api.item(args.slug)
    if not row:
        print(f'Item not found: {args.slug}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(row, ensure_ascii=False, separators=(',', ':')))
    else:
        print(f"=== {row['title']} ===")
        print(f"Type: {row['item_type']}")
        print(f"Release: {row['release']}")
        print(f"Source: {row['source_url']}")
        print(f"\n{row['text']}")
    return 0


def cmd_verify(args):
    res = api.verify(args.quote)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
    elif res['verified']:
        print(f'VERIFIED: "{args.quote}"')
        for h in res['matches']:
            sp = f" | speaker: {h['speaker']}" if h['speaker'] else ''
            print(f"  [{h['source']}] {h['slug']}{sp}")
    else:
        print(f'NOT FOUND: "{args.quote}"')
    return 0 if res['verified'] else 1


def cmd_list(args):
    out = api.listing(args.kind, limit=args.limit)
    if args.json:
        print(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
    else:
        if out:
            cols = list(out[0].keys())
            print(' | '.join(cols))
            for r in out:
                print(' | '.join(str(r[c]) for c in cols))
        print(f'\n{len(out)} rows')
    return 0 if out else 1


def cmd_stats(args):
    res = api.stats()
    counts = res['counts']
    if args.json:
        print(json.dumps(counts, separators=(',', ':')))
        return 0
    print('=== Destiny Grimoire Database Stats ===')
    for t, c in counts.items():
        print(f'  {t}: {c}')
    print('\n=== Top item types ===')
    for r in res['top_item_types']:
        print(f"  {r['item_type']}: {r['count']}")
    print('\n=== Top speakers ===')
    for r in res['top_speakers']:
        print(f"  {r['speaker']}: {r['count']}")
    return 0


def main(argv=None):
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

    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except FileNotFoundError as e:
        print(f'FAIL: {e}', file=sys.stderr)
        return 1
    except ValueError as e:
        print(f'FAIL: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
