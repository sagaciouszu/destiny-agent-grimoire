#!/usr/bin/env python3
"""Snapshot the Ishtar Collective timeline into source/ishtar-timeline.json.

The Ishtar timeline (https://www.ishtar-collective.net/timeline) is the
community's curated in-universe chronology: 52 eras, each with events that
link to source entries. The build consumes the snapshot offline; this script
only regenerates it (on demand, like the other network utilities).

Usage:
    python3 scripts/ishtar-timeline.py --fetch          # network refresh
    python3 scripts/ishtar-timeline.py --from FILE      # parse a saved copy
    python3 scripts/ishtar-timeline.py --report db/grimoire.db

--report compares the snapshot against the database timeline column:
coverage per table, and transcripts whose chapter disagrees with Ishtar's
era (candidate scene-in-past overrides for review - Ishtar tags about-time).
Exit 0 always; it is a report, not a gate.
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'source', 'ishtar-timeline.json')
URL = 'https://www.ishtar-collective.net/timeline'

# Ishtar era -> timeline_chapters slug (23-chapter vocabulary).
# Eras deliberately unmapped fall back to the database's own derivation and
# are listed by --report: into-the-light, rite-of-the-nine, ash-and-iron are
# too new/ambiguous to fold confidently.
ERA_CHAPTER = {
    'pre-history': 'pre_history',
    'ancient-past': 'ancient_past',
    'pre-golden-age': 'pre_golden_age',
    'golden-age': 'golden_age',
    'the-collapse': 'the_collapse',
    'the-dark-age': 'the_dark_age',
    'the-city-age': 'the_city_age',
    'destiny': 'the_rise_of_the_guardian',
    'the-dark-below': 'the_dark_below',
    'house-of-wolves': 'house_of_wolves',
    'the-taken-king': 'the_taken_war',
    'rise-of-iron': 'the_siva_crisis',
    'age-of-triumph': 'the_siva_crisis',
    'the-red-war': 'the_red_war',
    'curse-of-osiris': 'the_curse_of_osiris',
    'warmind': 'the_warmind_crisis',
    'forsaken': 'the_sack_of_the_dreaming_city',
    'season-of-the-forge': 'the_sack_of_the_dreaming_city',
    'season-of-the-drifter': 'the_sack_of_the_dreaming_city',
    'season-of-opulence': 'the_sack_of_the_dreaming_city',
    'shadowkeep': 'the_nightmares_return',
    'season-of-undying': 'the_nightmares_return',
    'season-of-dawn': 'the_nightmares_return',
    'season-of-the-worthy': 'the_nightmares_return',
    'season-of-arrivals': 'the_nightmares_return',
    'beyond-light': 'the_rise_of_stasis',
    'season-of-the-hunt': 'the_rise_of_stasis',
    'season-of-the-chosen': 'the_rise_of_stasis',
    'season-of-the-splicer': 'the_rise_of_stasis',
    'season-of-the-lost': 'the_rise_of_stasis',
    'the-witch-queen': 'the_witch_queen',
    'season-of-the-risen': 'the_witch_queen',
    'season-of-the-haunted': 'the_witch_queen',
    'season-of-plunder': 'the_witch_queen',
    'season-of-the-seraph': 'the_witch_queen',
    'lightfall': 'the_lightfall',
    'season-of-defiance': 'the_lightfall',
    'season-of-the-deep': 'the_lightfall',
    'season-of-the-witch': 'the_lightfall',
    'season-of-the-wish': 'the_lightfall',
    'the-final-shape': 'the_final_shape',
    'echoes': 'the_final_shape',
    'revenant': 'the_final_shape',
    'heresy': 'the_final_shape',
    'edge-of-fate': 'the_edge_of_fate',
}

LINK = re.compile(r'\]\((/(?:transcripts|cards|entries|records|items|categories)/[^)\s#]+)\)')
HREF = re.compile(r'href="(/(?:transcripts|cards|entries|records|items|categories)/[^"\s#]+)"')
ERA = re.compile(r'^#{2,3}\s+\[([^\]]+)\]\(#era-([^)\s]+)', re.M)


def parse(text):
    """Split the timeline page into eras with their source paths."""
    eras = []
    matches = list(ERA.finditer(text))
    for i, m in enumerate(matches):
        title, slug = m.group(1).strip(), m.group(2)
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end]
        paths = dict.fromkeys(LINK.findall(body) + HREF.findall(body))
        if paths:
            eras.append({'slug': slug, 'title': title,
                         'chapter': ERA_CHAPTER.get(slug), 'paths': list(paths)})
    return eras


def snapshot(text, origin):
    return {
        'source': URL,
        'origin': origin,
        'fetched_at': datetime.date.today().isoformat(),
        'eras': parse(text),
    }


def save(data):
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write('\n')
    total = sum(len(e['paths']) for e in data['eras'])
    print(f'{OUT}: {len(data["eras"])} eras, {total} source links')


def report(db):
    data = json.load(open(OUT, encoding='utf-8'))
    era_chapter = {e['slug']: ERA_CHAPTER.get(e['slug']) for e in data['eras']}
    path_chapter = {}
    for era in data['eras']:
        chapter = ERA_CHAPTER.get(era['slug'])
        for path in era['paths']:
            path_chapter.setdefault(path, (era['slug'], chapter))
    unmapped = [e['slug'] for e in data['eras'] if e['slug'] not in ERA_CHAPTER]
    print(f'eras: {len(data["eras"])}, mapped: {len(ERA_CHAPTER)}, unmapped: {unmapped}')
    conn = sqlite3.connect(f'file:{os.path.abspath(db)}?mode=ro', uri=True)
    for table in ('books', 'records', 'items', 'grimoire_cards', 'transcripts'):
        rows = conn.execute(
            f"SELECT slug, source_url, timeline FROM {table} "
            "WHERE source_url IS NOT NULL AND source_url != ''").fetchall()
        hit = 0
        for _slug, url, _tl in rows:
            path = '/' + '/'.join((url or '').split('/')[3:])
            if path in path_chapter:
                hit += 1
        print(f'{table}: {hit}/{len(rows)} on the Ishtar timeline')
    print('\ntranscript disagreements (Ishtar era vs when-spoken chapter):')
    seen = 0
    for slug, url, tl in conn.execute(
            "SELECT slug, source_url, timeline FROM transcripts "
            "WHERE source_url LIKE '%ishtar-collective.net%' ORDER BY slug"):
        path = '/' + '/'.join((url or '').split('/')[3:])
        entry = path_chapter.get(path)
        if not entry:
            continue
        era_slug, chapter = entry
        if chapter and chapter != tl:
            seen += 1
            if seen <= 40:
                print(f'  {slug}: db={tl or "-"} ishtar={era_slug} -> {chapter}')
    print(f'  ... {seen} disagreements total (Ishtar is about-time; review '
          f'before curating overrides - do not bulk-apply)')
    conn.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--fetch', action='store_true', help='download the timeline')
    group.add_argument('--from', dest='source_file', help='parse a saved copy')
    group.add_argument('--report', metavar='DB', help='compare snapshot vs database')
    args = ap.parse_args()
    if args.fetch:
        with urllib.request.urlopen(URL, timeout=60) as resp:
            text = resp.read().decode('utf-8', 'replace')
        save(snapshot(text, URL))
    elif args.source_file:
        text = open(args.source_file, encoding='utf-8', errors='replace').read()
        save(snapshot(text, 'saved:' + os.path.basename(args.source_file)))
    else:
        report(args.report)


if __name__ == '__main__':
    sys.exit(main())
