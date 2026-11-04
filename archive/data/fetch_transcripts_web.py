#!/usr/bin/env python3
"""Fetch all Ishtar Collective transcript pages (slug list in transcript-missing.txt).

Writes one JSON object per page to archive/data/transcripts_web.jsonl:
  slug, title, source_url, lines: [{speaker, text}]  (speaker '' = narration)
"""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = 'https://www.ishtar-collective.net/transcripts/'
HERE = os.path.dirname(os.path.abspath(__file__))

def fetch(slug):
    url = BASE + slug
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) grimoire-scraper/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode('utf-8', 'ignore')
    m = re.search(r'<title>([^<]+)</title>', html)
    title = ''
    if m:
        title = re.sub(r'\s*&mdash;.*$', '', m.group(1)).strip()
        title = title.replace('&amp;', '&').replace('&#39;', "'")
    # Related-content browser and the forum link follow the transcript body.
    # Cut them before parsing so they never become "narration".
    for marker in ('<p class="discuss"', '<div class="document-browser"'):
        idx = html.find(marker)
        if idx != -1:
            html = html[:idx]
    cm = re.search(r'<div class="entry-content">(.*?)</div>', html, re.S)
    body = cm.group(1) if cm else html
    lines = []
    for p in re.findall(r'<p[^>]*>(.*?)</p>', body, re.S):
        txt = re.sub(r'<[^>]+>', '', p).strip()
        txt = re.sub(r'\s+', ' ', txt)
        if not txt:
            continue
        sm = re.match(r'^([A-Z][A-Za-z0-9 .&\'\u2019-]{2,40}):\s*(.+)$', txt)
        if sm and sm.group(1).lower() not in {'note', 'sources'}:
            lines.append({'speaker': sm.group(1).strip(), 'text': sm.group(2).strip()})
        else:
            lines.append({'speaker': '', 'text': txt})
    return {'slug': slug, 'title': title, 'source_url': url, 'lines': lines}

def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh', action='store_true',
                        help='re-fetch every page and rewrite the JSONL')
    args = parser.parse_args()
    slugs = [s.strip() for s in open(os.path.join(HERE, 'transcript-missing.txt')) if s.strip()]
    out = os.path.join(HERE, 'transcripts_web.jsonl')
    done = set()
    if os.path.exists(out) and not args.refresh:
        for ln in open(out):
            try:
                done.add(json.loads(ln)['slug'])
            except Exception:
                pass
    todo = [s for s in slugs if s not in done]
    print(f'{len(slugs)} slugs, {len(done)} done, {len(todo)} to fetch')
    errs = 0
    with open(out, 'w' if args.refresh else 'a') as f, ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(fetch, s): s for s in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            s = futs[fut]
            try:
                d = fut.result()
                f.write(json.dumps(d, ensure_ascii=False) + '\n')
            except Exception as e:
                errs += 1
                print(f'ERR {s}: {e}', file=sys.stderr)
            if i % 100 == 0:
                print(f'...{i}/{len(todo)}')
    print(f'done, errors: {errs}')

if __name__ == '__main__':
    main()
