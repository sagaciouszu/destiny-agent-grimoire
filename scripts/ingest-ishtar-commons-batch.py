#!/usr/bin/env python3
"""Convert crawled Ishtar Commons topics into grimoire transcript markdown.

Reads archive/data/commons/topics/*.json (local, gitignored), parses the
official transcript syntax (++ sections, Speaker: lines, ** actions,
// OPTIONAL blocks), deduplicates against the live database, and writes only
net-new content to source/transcripts/commons-*.md.

Usage:
    python3 scripts/ingest-ishtar-commons-batch.py [--min-lines 2] [--dry-run]
"""
import argparse
import glob
import html
import json
import os
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'db'))
import taxonomy  # noqa: E402
from migrate import norm_text  # noqa: E402

RAW = os.path.join(ROOT, 'archive', 'data', 'commons')
OUT = os.path.join(ROOT, 'source', 'transcripts')
DB = os.path.join(ROOT, 'db', 'grimoire.db')
META = {'Name', 'URL', 'Video URL', 'Playlist URL', 'Recorded', 'Transcript', 'Source'}
TIER = {'validated': 1, 'published': 2, 'proofed': 3}
SKIP_TITLE = re.compile(
    r'transcript guide|transcript guidelines|about the ghost scan|'
    r'how to help us create|help us transcribe|format tips', re.I)


def cooked_text(cooked):
    text = cooked or ''
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<h[1-6][^>]*>', '\n++ ', text)
    text = re.sub(r'</h[1-6]>', '\n', text)
    text = re.sub(r'</t[dh]>', '\n', text)
    text = re.sub(r'</tr>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'</li>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text)


SPEAKER_NAME = r"([A-Z][A-Za-z0-9'’\-]+(?:\s+[A-Z][A-Za-z0-9'’\-]+){0,3})"
SPEAKER_RE = re.compile(r"(?<![A-Za-z0-9])" + SPEAKER_NAME + r":\s+")


def expand_speakers(line):
    """Split a table cell that packs several 'Speaker: line' runs together."""
    marks = list(SPEAKER_RE.finditer(line))
    if len(marks) <= 1:
        return [line]
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(line)
        out.append(f'{m.group(1)}: {line[m.end():end].strip()}')
    return out


def slugify(value):
    value = (value or '').lower().replace('&', ' and ')
    value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
    return value[:70] or 'transcript'


def parse_topic(topic):
    """Return blocks: (section, optional, [(speaker, text)]) and metadata."""
    lines = [x.strip() for x in cooked_text(topic.get('cooked')).splitlines() if x.strip()]
    meta = {}
    section = ''
    optional = 0
    blocks = []
    current = (section, optional)
    for line in lines:
        if line.startswith('Name:'):
            meta['name'] = line.split(':', 1)[1].strip()
            continue
        if line.startswith('Recorded:'):
            meta['recorded'] = line.split(':', 1)[1].strip()
            continue
        if line.startswith(('URL:', 'Video URL:', 'Playlist URL:', 'Transcript:', 'Source:')):
            continue
        if line.startswith('++'):
            section = re.sub(r'^[+\s]+', '', line).strip()
            current = (section, optional)
            continue
        if line.startswith('// OPTIONAL'):
            optional += 1
            current = (section, optional)
            continue
        if line == '}' and optional:
            optional -= 1
            current = (section, optional)
            continue
        if line.startswith('//'):
            continue
        if line.startswith('**'):
            action = line.lstrip('*').strip()
            if len(action) >= 3:
                key = (section, optional)
                if not blocks or blocks[-1][:2] != key:
                    blocks.append((section, optional, []))
                blocks[-1][2].append(('Narration', f'[{action}]'))
            continue
        for part in expand_speakers(line):
            m = re.match(r"^" + SPEAKER_NAME + r":\s+(.+)$", part)
            if m:
                speaker, spoken = m.group(1).strip(), m.group(2).strip()
                if speaker in META:
                    continue
                speaker = speaker.rstrip(':')
            else:
                if len(part) < 4:
                    continue
                speaker, spoken = 'Narration', part
            key = (section, optional)
            if not blocks or blocks[-1][:2] != key:
                blocks.append((section, optional, []))
            blocks[-1][2].append((speaker, spoken))
    return meta, blocks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--min-lines', type=int, default=2)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = sqlite3.connect(DB)
    existing = {r[0] for r in conn.execute(
        'SELECT norm_line FROM transcript_lines WHERE norm_line != ""')}
    conn.close()

    topics = []
    for line in open(os.path.join(RAW, 'topics.jsonl'), encoding='utf-8'):
        try:
            topics.append(json.loads(line))
        except Exception:
            pass
    topics.sort(key=lambda t: min([TIER.get(x, 5) for x in (t.get('tags') or [])] or [5]))

    report = {'topics': len(topics), 'written': 0, 'skipped': 0,
              'unique_lines': 0, 'duplicate_lines': 0, 'by_tag': {}, 'files': []}
    batch_seen = set()
    # Incremental runs: treat already-written commons files as seen.
    for prior in glob.glob(os.path.join(OUT, 'commons-*.md')):
        for line in open(prior, encoding='utf-8', errors='ignore'):
            st = line.strip()
            m = re.match(r'^\*([^*]+):\*\s+(.+)$', st)
            if m:
                batch_seen.add(norm_text(m.group(2)))
            elif st and not st.startswith(('-', '#', '<!--', '*')):
                batch_seen.add(norm_text(st))
    for topic in topics:
        tid = topic['id']
        path = os.path.join(RAW, 'topics', f'{tid}.json')
        if not os.path.exists(path):
            continue
        raw = json.load(open(path, encoding='utf-8'))
        tags = raw.get('tags') or topic.get('tags') or []
        for tag in tags:
            report['by_tag'][tag] = report['by_tag'].get(tag, 0) + 1
        if 'errors-found' in tags or 'ready-for-review' in tags:
            report['skipped'] += 1
            continue
        if SKIP_TITLE.search(raw.get('title') or ''):
            report['skipped'] += 1
            continue
        meta, blocks = parse_topic(raw)
        title = raw.get('title') or meta.get('name') or f'Commons topic {tid}'
        rows = []
        dups = 0
        for section, optional, entries in blocks:
            kept = []
            for speaker, text in entries:
                n = norm_text(text)
                if not n:
                    continue
                if n in existing or n in batch_seen:
                    dups += 1
                    continue
                batch_seen.add(n)
                kept.append((speaker, text))
            if kept:
                rows.append((section, optional, kept))
        unique = sum(len(k) for _, _, k in rows)
        unique_dialogue = sum(1 for _, _, k in rows for s, _ in k if s != 'Narration')
        report['duplicate_lines'] += dups
        if unique_dialogue == 0 or unique < args.min_lines:
            report['skipped'] += 1
            continue
        speakers = sorted({s for _, _, k in rows for s, _ in k if s != 'Narration'})
        release = meta.get('recorded') or (raw.get('created_at') or '')[:10]
        classified = taxonomy.classify(slug='', title=title, release=release, arc='')
        arc = classified.get('activity_slug') or classified.get('season_slug') or ''
        tier = next((t for t in ('validated', 'published', 'proofed') if t in tags),
                    'ishtar_commons')
        body = [f'# {title}', '',
                f'- Release: {release}',
                f'- Characters: {", ".join(speakers)}',
                f'- Arc: {arc}',
                f'- Tier: {tier}',
                f'- Source: https://commons.ishtar-collective.net/t/{tid}', '']
        for section, optional, entries in rows:
            if section:
                body.append(f'## {section}')
            if optional:
                body.append('<!-- optional -->')
            for speaker, text in entries:
                body.append(f'*{speaker}:* {text}' if speaker != 'Narration' else text)
            if optional:
                body.append('<!-- /optional -->')
            body.append('')
        out_slug = f'commons-{tid}-{slugify(title)}'
        if not args.dry_run:
            open(os.path.join(OUT, out_slug + '.md'), 'w', encoding='utf-8').write('\n'.join(body))
        report['written'] += 1
        report['unique_lines'] += unique
        report['files'].append({'id': tid, 'slug': out_slug, 'title': title,
                                'tags': tags, 'unique': unique,
                                'dialogue': unique_dialogue, 'duplicates': dups})
        print(f"+ {out_slug}: {unique_dialogue} dialogue / {unique} lines / {dups} dup "
              f"[{','.join(tags) or 'untagged'}]")

    json.dump(report, open(os.path.join(RAW, 'ingest-report.json'), 'w'), indent=2)
    print(f"\nwritten {report['written']} topics, {report['unique_lines']} unique lines, "
          f"{report['duplicate_lines']} duplicates, {report['skipped']} skipped")


if __name__ == '__main__':
    main()
