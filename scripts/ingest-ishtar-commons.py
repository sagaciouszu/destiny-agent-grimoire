#!/usr/bin/env python3
"""Ingest a transcript from Ishtar Commons (the community Discourse forum).

Usage:
    python3 scripts/ingest-ishtar-commons.py \
        --topic 3955 --slug override \
        --title "Override — Transcript" \
        --release "Season of the Splicer (2021.05.11)" \
        --arc "Season of the Splicer / Override"

Fetches the forum topic JSON, reads the first post, and converts
`Speaker: line` rows into grimoire transcript markdown. Metadata lines
(Name, URL, Recorded, ...) and stage directions are skipped. Exact duplicates
across the supplied topics are removed once.
"""
import argparse
import html
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'source', 'transcripts')
META = {'Name', 'URL', 'Recorded', 'Transcript', 'Playlist URL', 'Video URL', 'Source'}


def topic_rows(topic_id):
    url = f'https://commons.ishtar-collective.net/t/{topic_id}.json'
    raw = subprocess.run(
        ['curl', '-sL', '--max-time', '60', '-A', 'Mozilla/5.0', url],
        capture_output=True, text=True).stdout
    data = json.loads(raw)
    cooked = data['post_stream']['posts'][0]['cooked']
    text = re.sub(r'<br\s*/?>', '\n', cooked)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    rows = []
    for line in (x.strip() for x in text.splitlines() if x.strip()):
        m = re.match(r"^([A-Z][A-Za-z0-9'’ .\-]{1,40}):\s+(.+)$", line)
        if not m:
            continue
        speaker, spoken = m.group(1).strip(), m.group(2).strip()
        if speaker in META:
            continue
        rows.append((speaker, spoken))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--topic', type=int, action='append', required=True,
                        help='Discourse topic id; repeat for multi-week transcripts')
    parser.add_argument('--slug', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--release', default='')
    parser.add_argument('--arc', default='')
    parser.add_argument('--tier', default='ishtar_commons')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    rows, seen = [], set()
    for topic_id in args.topic:
        for row in topic_rows(topic_id):
            if row in seen:
                continue
            seen.add(row)
            rows.append(row)
    if not rows:
        raise SystemExit('no dialogue rows found')
    speakers = sorted({speaker for speaker, _ in rows})
    body = (f'# {args.title}\n\n'
            f'- Release: {args.release}\n'
            f'- Characters: {", ".join(speakers)}\n'
            f'- Arc: {args.arc}\n'
            f'- Tier: {args.tier}\n'
            f'- Source: https://commons.ishtar-collective.net/t/{args.topic[0]}\n\n'
            + '\n\n'.join(f'*{speaker}:* {line}' for speaker, line in rows) + '\n')
    if args.dry_run:
        print(body)
        return
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f'{args.slug}.md')
    open(path, 'w', encoding='utf-8').write(body)
    print(f'wrote {path}: {len(rows)} lines, {len(speakers)} speakers')


if __name__ == '__main__':
    main()
