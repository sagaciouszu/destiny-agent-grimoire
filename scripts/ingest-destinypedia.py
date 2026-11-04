#!/usr/bin/env python3
"""Ingest a verbatim transcript from Destinypedia into source/transcripts/.

Usage:
    python3 scripts/ingest-destinypedia.py \
        --page "The_Menagerie" --slug menagerie \
        --title "The Menagerie — Transcript" \
        --release "Season of Opulence (2019.06.04)" \
        --arc "Season of Opulence / The Menagerie"

Reads the MediaWiki wikitext API, takes the `Transcript` section, and converts
`*'''Speaker''': line` rows into the grimoire format (`*Speaker:* line`).
Stage directions and mechanics callouts are dropped. Every "or alternatively"
variant is kept; class-exclusive variants are not deduplicated.

Output is written to source/transcripts/<slug>.md and picked up by
`db/migrate.py` on the next build.
"""
import argparse
import json
import os
import re
import subprocess
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'source', 'transcripts')
API = 'https://www.destinypedia.com/api.php'


def fetch(page):
    url = (f'{API}?action=parse&page={urllib.parse.quote(page)}'
           '&prop=wikitext&format=json&formatversion=2')
    raw = subprocess.run(
        ['curl', '-sL', '--max-time', '60', '-A', 'Mozilla/5.0', url],
        capture_output=True, text=True).stdout
    data = json.loads(raw)
    if 'parse' not in data:
        raise SystemExit(f'page not found or not readable: {page}')
    return data['parse']['wikitext']


def clean(text):
    text = re.sub(r'\[\[([^\]|]+)\|([^\]]+)\]\]', r'\2', text)
    text = re.sub(r'\[\[([^\]]+)\]\]', r'\1', text)
    text = re.sub(r'\[https?://[^\]]+\s+([^\]]+)\]', r'\1', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace("'''", '').replace("''", '')
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
    return re.sub(r'\s+', ' ', text).strip()


def transcript_section(wikitext):
    m = re.search(r'^(=+)\s*Transcript\s*\1\s*$', wikitext, re.M)
    if not m:
        return ''
    level = len(m.group(1))
    rest = wikitext[m.end():]
    stop = re.search(r'^={1,%d}\s*[^=].*?=+\s*$' % level, rest, re.M)
    return rest[:stop.start()] if stop else rest


def extract(wikitext):
    rows, seen = [], set()
    for raw in transcript_section(wikitext).splitlines():
        m = re.match(r"^\*\s*'''(?P<sp>.+?)'''\s*:?\s*(?P<line>.+)$", raw.strip())
        if not m:
            continue
        speaker = clean(m.group('sp')).rstrip(':').lstrip(':').strip()
        line = clean(m.group('line')).lstrip(':').strip()
        if not speaker or not line:
            continue
        if line.lower().startswith(('according to', 'see also')):
            continue
        key = (speaker, line)
        if key in seen:
            continue
        seen.add(key)
        rows.append((speaker, line))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--page', required=True, help='Destinypedia page title')
    parser.add_argument('--slug', required=True, help='output transcript slug')
    parser.add_argument('--title', required=True)
    parser.add_argument('--release', default='')
    parser.add_argument('--arc', default='')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    rows = extract(fetch(args.page))
    if not rows:
        raise SystemExit(f'no dialogue rows found in Transcript section of {args.page}')
    speakers = sorted({speaker for speaker, _ in rows})
    body = (f'# {args.title}\n\n'
            f'- Release: {args.release}\n'
            f'- Characters: {", ".join(speakers)}\n'
            f'- Arc: {args.arc}\n'
            f'- Source: https://www.destinypedia.com/{args.page}\n\n'
            + '\n\n'.join(f'*{speaker}:* {line}' for speaker, line in rows) + '\n')
    path = os.path.join(OUT_DIR, f'{args.slug}.md')
    if args.dry_run:
        print(body)
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    open(path, 'w', encoding='utf-8').write(body)
    print(f'wrote {path}: {len(rows)} lines, {len(speakers)} speakers')


if __name__ == '__main__':
    main()
