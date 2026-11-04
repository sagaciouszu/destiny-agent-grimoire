#!/usr/bin/env python3
"""Capture the authoritative "Added In" release for every Ishtar transcript.

Ishtar transcript pages carry a sidebar release link:

    <div class="section-title">Added In</div>
    ... href="/releases/the-taken-king">The Taken King</a>

That release is better evidence than the recording date, especially for
Destiny 1 content. This script writes a small slug -> release map next to the
scraped transcripts so `db/migrate.py` can classify explicitly.

Usage:
    python3 archive/data/fetch_transcript_releases.py [--refresh] [--limit N]
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = 'https://www.ishtar-collective.net/transcripts/'
HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, 'transcripts_web.jsonl')
OUT = os.path.join(HERE, 'transcript-releases.json')
DISPLAY = {
    'destiny': 'Destiny 1',
    'destiny-2': 'Destiny 2',
    'destiny-2-beta': 'Destiny 2',
    'the-taken-king-april-update': 'The Taken King',
    'heresy': 'Episode: Heresy',
    'revenant': 'Episode: Revenant',
    'echoes': 'Episode: Echoes',
}
RELEASE_RE = re.compile(
    r'<div class="section-title">Added In</div>.*?'
    r'href="/releases/([^"]+)"[^>]*>([^<]+)</a>', re.S)


def fetch(slug):
    url = BASE + slug
    req = urllib.request.Request(
        url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) grimoire-scraper/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode('utf-8', 'ignore')
    m = RELEASE_RE.search(html)
    if not m:
        return slug, None
    release_slug, release = m.group(1).strip(), m.group(2).strip()
    return slug, {
        'release_slug': release_slug,
        'release': DISPLAY.get(release_slug, release),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true',
                        help='re-fetch slugs already present in the map')
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    slugs = []
    for line in open(SOURCE, encoding='utf-8'):
        try:
            slugs.append(json.loads(line)['slug'])
        except Exception:
            pass
    slugs = list(dict.fromkeys(slugs))
    existing = {}
    if os.path.exists(OUT) and not args.refresh:
        existing = json.load(open(OUT, encoding='utf-8'))
    todo = [s for s in slugs if s not in existing]
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(slugs)} transcripts, {len(existing)} known, {len(todo)} to fetch')

    errors = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch, s): s for s in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            slug = futs[fut]
            try:
                key, value = fut.result()
            except Exception as exc:  # noqa: BLE001
                errors += 1
                print(f'ERR {slug}: {exc}', file=sys.stderr)
                continue
            if value:
                existing[key] = value
            if i % 100 == 0:
                print(f'...{i}/{len(todo)}')
    with open(OUT, 'w', encoding='utf-8') as fh:
        json.dump(dict(sorted(existing.items())), fh, indent=2, ensure_ascii=False)
        fh.write('\n')
    missing = [s for s in slugs if s not in existing]
    print(f'wrote {len(existing)} releases, {errors} errors, {len(missing)} without release')
    for slug in missing[:10]:
        print(f'  no release: {slug}')


if __name__ == '__main__':
    main()
