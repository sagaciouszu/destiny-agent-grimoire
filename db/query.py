#!/usr/bin/env python3
"""Agent query interface for the Destiny Grimoire database.

Designed for LLM agents: small bounded outputs, snippet-first search, JSON mode,
and quote verification. Every command exits non-zero on failure.

Usage:
  query.py search "<term>" [--type books|transcripts|grimoire|interactions|items|records]
                           [--activity NAME] [--season N|NAME] [--event NAME]
                           [--expansion NAME] [--entity NAME] [--limit N] [--json] [--full]
  query.py entity "<name>" [--kind char|power|faction|place] [--include-unreviewed] [--limit N] [--json]
  query.py character "<name>" [--about <term>] [--limit N] [--all] [--json]
  query.py item "<slug>" [--json]
  query.py verify "<quote>" [--speaker NAME] [--exact] [--json]
  query.py verify-many "<q1>" "<q2>" ... [--speaker NAME] [--exact] [--json]
  query.py character-info "<name>" [--json]
  query.py list books|characters|speakers|records|activities|seasons|events [--limit N] [--offset N] [--json]
  query.py book "<slug or title>" [--limit N] [--offset N] [--full] [--json]
  query.py transcript "<slug or title>" [--speaker NAME] [--limit N] [--offset N] [--full] [--json]
  query.py find-item "<title>" [--limit N] [--offset N] [--json]
  query.py record "<slug or title>" [--json]
  query.py activity "<slug or name>" [--limit N] [--json]
  query.py event "<slug or name>" [--json]
  query.py lore "<hash or title>" [--json]
  query.py seal "<name or hash>" [--json]
  query.py seals [--json]
  query.py coverage [--json]
  query.py stats [--json]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import api  # noqa: E402

TYPE_TO_SOURCE = api.TYPE_TO_SOURCE


def emit(rows, as_json, human_fn):
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=None, separators=(',', ':')))
    else:
        human_fn(rows)


def cmd_search(args):
    query = ' '.join(args.query)
    out, total = api.search(query, type=args.type, limit=args.limit, full=args.full,
                     offset=args.offset, rank=args.rank, activity=args.activity,
                     season=args.season, event=args.event, expansion=args.expansion,
                     class_tag=args.class_tag, timeline=args.timeline, lang=args.lang,
                     entity=args.entity, with_total=True)
    # --json callers still get the rows; the total is only printed for humans.
    if args.json:
        total = None
    if args.full:
        emit(out, args.json, lambda rs: [print(f"[{r['source']}] {r['title']}: {r['text'][:200]}") for r in rs])
    else:
        emit(out, args.json, lambda rs: [print(f"[{r['source']}] {r['title']}: {r['snippet']}") for r in rs])
    if not args.json:
        print(f'\n{len(out)} results of {total}')
    return 0 if out else 1


def cmd_entity(args):
    res = api.entity(args.name, limit=args.limit, kind=args.kind,
                     include_unreviewed=args.include_unreviewed)
    out = res['results']
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
        return 0 if out else 1
    if not out:
        print(f'Entity not found: {args.name}', file=sys.stderr)
        return 1
    top = out[0]
    if top['fuzzy']:
        print(f'No exact match for "{args.name}". Fuzzy candidates (score <= 0.5):')
        for r in out:
            print(f"  - {r['canonical']} ({r['kind']}, alias {r['alias']!r}, "
                  f"score {r['score']}, confidence {r['confidence']})")
        return 1
    e = res['entity']
    print(f"=== {e['canonical']} ({e['kind']}, confidence {e['confidence']}) ===")
    print('Aliases: ' + ', '.join(f"{a['alias']} (weight {a['weight']:.2f}"
                                  + (', ctx)' if a['requires_ctx'] else ')')
                                  for a in res['aliases']))
    counts = res['counts']
    if counts:
        print('Documents: ' + str(res['total_documents']) + ' ' +
              '(' + ', '.join(f'{k}: {v}' for k, v in sorted(counts.items())) + ')')
    else:
        print('Documents: 0')
    for rel in res['relations']:
        if rel['direction'] == 'out':
            print(f"Relation: {rel['relation']} -> {rel['target']} ({rel['target_kind']})")
        else:
            print(f"Relation: {rel['source']} ({rel['source_kind']}) -{rel['relation']}-> this entity")
    if res['documents']:
        print('Top documents:')
        for d in res['documents']:
            print(f"  - {d['kind']} {d['ref']} (weight {d['weight']:.2f}, {d['match']})")
    if len(out) > 1:
        print('Also matched: ' + ', '.join(sorted({r['canonical'] for r in out})))
    return 0


def cmd_character(args):
    res = api.character(args.name, about=args.about, all_lines=args.all, limit=args.limit,
                        offset=args.offset, canon_only=args.canon_only,
                        class_tag=args.class_tag, tiers=args.tier,
                        exclude_tiers=args.exclude_tier)
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


def cmd_verify_many(args):
    res = api.verify_many(args.quotes, speaker=args.speaker, exact=args.exact)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
    else:
        for r in res['results']:
            print(('VERIFIED: ' if r['verified'] else 'NOT FOUND: ') + f'"{r["quote"]}"')
        print(f"\n{res['verified']} of {res['total']} verified")
    return 0 if res['verified'] == res['total'] else 1


def cmd_character_info(args):
    res = api.character_info(args.name)
    if res is None:
        print(f'Character not found: {args.name}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
    else:
        print(f"=== {res['name']} ({res['slug']}) ===")
        print(f"Curated quotes: {res['quotes']} | spoken lines: {res['spoken_lines']}")
        print(f"Sources: {res['sources']}")
        print(f"Aliases: {', '.join(res['aliases']) or 'none'}")
    return 0


def cmd_verify(args):
    quote = ' '.join(args.quote)
    res = api.verify(quote, speaker=args.speaker, exact=args.exact)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
    elif res['verified']:
        label = ' (exact)' if res['exact'] else ''
        print(f'VERIFIED{label}: "{res["quote"]}"')
        for h in res['matches']:
            sp = f" | speaker: {h['speaker']}" if h['speaker'] else ''
            ex = ' | exact' if h['exact'] else ''
            print(f"  [{h['source']}] {h['slug']}{sp}{ex}")
    else:
        print(f'NOT FOUND: "{res["quote"]}"')
    return 0 if res['verified'] else 1


def cmd_list(args):
    kind = args.kind.replace('-', '_')
    out = api.listing(kind, limit=args.limit, offset=args.offset)
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


def cmd_book(args):
    res = api.book(args.ref, limit=args.limit, offset=args.offset, full=args.full)
    if res is None:
        print(f'Book not found: {args.ref}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
    else:
        b = res['book']
        print(f"=== {b['title']} ===")
        print(f"Slug: {b['slug']} | entries: {res['total']}")
        for e in res['entries']:
            print(f"\n## {e['title']}")
            print(e['body'])
        print(f"\nShowing {len(res['entries'])} of {res['total']} (offset {res['offset']})")
    return 0 if res['entries'] else 1


def cmd_transcript(args):
    res = api.transcript(args.ref, speaker=args.speaker, limit=args.limit,
                         offset=args.offset, full=args.full, include_stage=args.include_stage,
                         canon_only=args.canon_only, section=args.section,
                         class_tag=args.class_tag, tiers=args.tier,
                         exclude_tiers=args.exclude_tier)
    if res is None:
        print(f'Transcript not found: {args.ref}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
    else:
        t = res['transcript']
        print(f"=== {t['title']} ===")
        tax = res.get('taxonomy') or {}
        if tax:
            bits = [tax.get('activity_name') or tax.get('activity_slug') or tax.get('activity_type'),
                    tax.get('season_slug'), tax.get('event_slug'),
                    tax.get('expansion_slug'), tax.get('confidence')]
            print('Taxonomy: ' + ' | '.join(str(b) for b in bits if b))
        if t.get('source_tier'):
            print('Source tier: ' + t['source_tier'])
        if res.get('tier_match') is False:
            print('Tier filter excluded this transcript.')
        for line in res['lines']:
            print(f"[{line['speaker']}] {line['text']}")
        print(f"\nShowing {len(res['lines'])} of {res['total']} (offset {res['offset']})")
    return 0 if res['lines'] else 1


def cmd_find_item(args):
    res = api.find_item(args.query, limit=args.limit, offset=args.offset)
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
    else:
        for r in res['rows']:
            print(f"{r['slug']} | {r['title']} | {r['item_type']}")
        print(f"\n{len(res['rows'])} rows of {res['total']} (offset {res['offset']})")
    return 0 if res['rows'] else 1


def cmd_record(args):
    row = api.record(args.ref)
    if row is None:
        print(f'Record not found: {args.ref}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(row, ensure_ascii=False, separators=(',', ':')))
    else:
        print(f"=== {row['title']} ===")
        print(f"Slug: {row['slug']} | release: {row['release']}")
        print(f"\n{row['body']}")
    return 0


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


def cmd_activity(args):
    res = api.activity(args.ref, limit=args.limit, offset=args.offset)
    if res is None:
        print(f'Activity not found: {args.ref}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
        return 0
    print(f"=== {res['name']} ({res['slug']}) ===")
    print(f"Type: {res['activity_type']} | season: {res['season_slug'] or 'unknown'} | "
          f"expansion: {res['expansion_slug'] or 'unknown'} | vaulted: {bool(res['vaulted'])}")
    print(f"Coverage: {res['coverage']['transcripts']} transcripts, {res['coverage']['lines']} lines")
    if res['speakers']:
        print('Speakers: ' + ', '.join(f"{s['speaker']} ({s['lines']})" for s in res['speakers'][:8]))
    for t in res['transcripts']:
        print(f"  - {t['title']} [{t['confidence']}]")
    return 0 if res['transcripts'] else 1


def cmd_event(args):
    res = api.event(args.ref)
    if res is None:
        print(f'Event not found: {args.ref}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
        return 0
    print(f"=== {res['name']} ({res['slug']}) ===")
    print(f"Type: {res['event_type']} | vaulted: {bool(res['vaulted'])} | "
          f"years: {res['first_year']}-{res['last_year']}")
    print('Occurrences: ' + ', '.join(str(o['year']) for o in res['occurrences']))
    print(f"Transcripts: {len(res['transcripts'])}")
    for t in res['transcripts']:
        print(f"  - {t['title']} [{t['confidence']}]")
    return 0 if res['transcripts'] else 1


def cmd_coverage(args):
    res = api.coverage()
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
        return 0
    print('=== Activities ===')
    for a in res['activities']:
        print(f"  {a['slug']:<28} {a['activity_type']:<14} "
              f"{a['transcripts']:>3} transcripts {a['lines']:>6} lines  {a['coverage_status']}")
    print('\n=== Seasons ===')
    for s in res['seasons']:
        print(f"  {s['season_number']:>2} {s['slug']:<26} {s['transcripts']:>3} transcripts "
              f"{s['lines']:>6} lines  {s['coverage_status']}")
    print('\n=== Events ===')
    for e in res['events']:
        print(f"  {e['slug']:<24} {e['transcripts']:>3} transcripts {e['lines']:>6} lines "
              f"{e['occurrences']:>2} occurrences  {e['coverage_status']}")
    print('\n=== Gaps ===')
    for k, v in res['gaps'].items():
        print(f'  {k}: {len(v)}')
    if res.get('notes'):
        print('\n=== Coverage notes ===')
        for n in res['notes']:
            print(f"  {n['entity_type']}:{n['slug']:<24} {n['status']:<24} {n['evidence']}")
    return 0


def cmd_seals(args):
    rows = api.seals()
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
        return 0
    for r in rows:
        print(f"{r['name']} | {r['records']} records | {r['hash']}")
    return 0


def cmd_seal(args):
    res = api.seal(args.ref)
    if res is None:
        print(f'Seal not found: {args.ref}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
        return 0
    print(f"=== {res['name']} ({res['hash']}) ===")
    if res['description']:
        print(res['description'])
    for r in res['records']:
        print(f"  - {r['name']}: {r['description'][:120]}")
    print(f"\n{len(res['records'])} records")
    return 0


def cmd_lore(args):
    res = api.lore(args.ref)
    if res is None:
        print(f'Lore entry not found: {args.ref}', file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(res, ensure_ascii=False, separators=(',', ':')))
        return 0
    print(f"=== {res['title']} ({res['hash']}) ===")
    if res['subtitle']:
        print(res['subtitle'])
    if res['items']:
        print('Items: ' + ', '.join(res['items'][:10]))
    if res['is_duplicate']:
        print('Duplicate of: ' + (res['duplicate_of'] or 'existing canon'))
    print()
    print(res['body'])
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description='Query the Destiny Grimoire database')
    sub = parser.add_subparsers(dest='cmd')

    s = sub.add_parser('search', help='Full-text search (snippet by default)')
    s.add_argument('query', nargs='+', help='search words (quoting optional)')
    s.add_argument('--type', choices=list(TYPE_TO_SOURCE.keys()))
    s.add_argument('--activity', help='only content from this activity')
    s.add_argument('--season', help='season number, slug or name')
    s.add_argument('--event', help='rotating event slug or name')
    s.add_argument('--expansion', help='expansion slug or name')
    s.add_argument('--class', dest='class_tag', choices=['hunter','titan','warlock'])
    s.add_argument('--timeline', help='in-universe story chapter slug, e.g. the_dark_age')
    s.add_argument('--lang', help="document language code, e.g. 'en' (all rows are 'en' today; later caption drops add languages)")
    s.add_argument('--entity', help='restrict to documents this entity is linked to (e.g. "Savathûn")')
    s.add_argument('--limit', type=int, default=10)
    s.add_argument('--offset', type=int, default=0)
    s.add_argument('--json', action='store_true')
    s.add_argument('--full', action='store_true', help='full text instead of snippets')
    s.add_argument('--rank', dest='rank', action='store_true', default=True,
                   help='order by FTS relevance (default)')
    s.add_argument('--no-rank', dest='rank', action='store_false',
                   help='keep insertion order')
    s.set_defaults(func=cmd_search)

    en = sub.add_parser('entity', help='Entity web: aliases, documents, relations (fuzzy-flagged candidates)')
    en.add_argument('name')
    en.add_argument('--kind', choices=list(api._ENTITY_KINDS))
    en.add_argument('--include-unreviewed', action='store_true',
                    help='include reviewed=0 aliases in resolution')
    en.add_argument('--limit', type=int, default=10)
    en.add_argument('--json', action='store_true')
    en.set_defaults(func=cmd_entity)

    c = sub.add_parser('character', help='Character lines')
    c.add_argument('name')
    c.add_argument('--about', help='only lines mentioning this term')
    c.add_argument('--all', action='store_true', help='all transcript lines, not just curated quotes')
    c.add_argument('--canon-only', action='store_true', help='exclude optional/variant lines')
    c.add_argument('--tier', action='append', metavar='TIER',
                   help='only this source tier (repeatable or comma-separated)')
    c.add_argument('--exclude-tier', action='append', metavar='TIER',
                   help='exclude this source tier, for example game_caption')
    c.add_argument('--class', dest='class_tag', choices=['hunter','titan','warlock'])
    c.add_argument('--limit', type=int, default=20)
    c.add_argument('--offset', type=int, default=0)
    c.add_argument('--json', action='store_true')
    c.set_defaults(func=cmd_character)

    i = sub.add_parser('item', help='Item details')
    i.add_argument('slug')
    i.add_argument('--json', action='store_true')
    i.set_defaults(func=cmd_item)

    v = sub.add_parser('verify', help='Check a quote against canon (exit 1 if not found)')
    v.add_argument('quote', nargs='+', help='quote text (quoting optional)')
    v.add_argument('--speaker', help='require this speaker attribution')
    v.add_argument('--exact', action='store_true', help='require a full canonical line, not a fragment')
    v.add_argument('--json', action='store_true')
    v.set_defaults(func=cmd_verify)

    l = sub.add_parser('list', help='Cheap discovery listings')
    l.add_argument('kind', choices=['books', 'characters', 'speakers', 'canon-speakers',
                                   'records', 'activities', 'seasons', 'events', 'lore', 'seals'])
    l.add_argument('--limit', type=int, default=50)
    l.add_argument('--offset', type=int, default=0)
    l.add_argument('--json', action='store_true')
    l.set_defaults(func=cmd_list)

    bk = sub.add_parser('book', help='Read a book and its entries')
    bk.add_argument('ref')
    bk.add_argument('--limit', type=int, default=20)
    bk.add_argument('--offset', type=int, default=0)
    bk.add_argument('--full', action='store_true')
    bk.add_argument('--json', action='store_true')
    bk.set_defaults(func=cmd_book)

    tr = sub.add_parser('transcript', help='Read a transcript and its lines')
    tr.add_argument('ref')
    tr.add_argument('--speaker')
    tr.add_argument('--limit', type=int, default=50)
    tr.add_argument('--offset', type=int, default=0)
    tr.add_argument('--full', action='store_true')
    tr.add_argument('--include-stage', action='store_true')
    tr.add_argument('--canon-only', action='store_true', help='exclude optional/variant lines')
    tr.add_argument('--tier', action='append', metavar='TIER',
                    help='only this transcript source tier (repeatable or comma-separated)')
    tr.add_argument('--exclude-tier', action='append', metavar='TIER',
                    help='exclude this transcript source tier, for example game_caption')
    tr.add_argument('--section', help='only lines from this section/location')
    tr.add_argument('--class', dest='class_tag', choices=['hunter','titan','warlock'])
    tr.add_argument('--json', action='store_true')
    tr.set_defaults(func=cmd_transcript)

    fi = sub.add_parser('find-item', help='Find items by title or slug')
    fi.add_argument('query')
    fi.add_argument('--limit', type=int, default=10)
    fi.add_argument('--offset', type=int, default=0)
    fi.add_argument('--json', action='store_true')
    fi.set_defaults(func=cmd_find_item)

    rc = sub.add_parser('record', help='Read a triumph or seal')
    rc.add_argument('ref')
    rc.add_argument('--json', action='store_true')
    rc.set_defaults(func=cmd_record)

    vm = sub.add_parser('verify-many', help='Verify up to 20 quotes at once')
    vm.add_argument('quotes', nargs='+')
    vm.add_argument('--speaker')
    vm.add_argument('--exact', action='store_true')
    vm.add_argument('--json', action='store_true')
    vm.set_defaults(func=cmd_verify_many)

    ci = sub.add_parser('character-info', help='Character metadata and line counts')
    ci.add_argument('name')
    ci.add_argument('--json', action='store_true')
    ci.set_defaults(func=cmd_character_info)

    ac = sub.add_parser('activity', help='Activity details and coverage')
    ac.add_argument('ref')
    ac.add_argument('--limit', type=int, default=50)
    ac.add_argument('--offset', type=int, default=0)
    ac.add_argument('--json', action='store_true')
    ac.set_defaults(func=cmd_activity)

    ev = sub.add_parser('event', help='Rotating event details and occurrences')
    ev.add_argument('ref')
    ev.add_argument('--json', action='store_true')
    ev.set_defaults(func=cmd_event)

    sl = sub.add_parser('seal', help='Read a seal and its triumph records')
    sl.add_argument('ref')
    sl.add_argument('--json', action='store_true')
    sl.set_defaults(func=cmd_seal)

    sls = sub.add_parser('seals', help='List seals with record counts')
    sls.add_argument('--json', action='store_true')
    sls.set_defaults(func=cmd_seals)

    lo = sub.add_parser('lore', help='Read a manifest lore entry')
    lo.add_argument('ref')
    lo.add_argument('--json', action='store_true')
    lo.set_defaults(func=cmd_lore)

    cv = sub.add_parser('coverage', help='Activity/season/event coverage summary')
    cv.add_argument('--json', action='store_true')
    cv.set_defaults(func=cmd_coverage)

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
