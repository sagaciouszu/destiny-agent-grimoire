#!/usr/bin/env python3
"""Crawl Ishtar Commons transcript categories into a local staging area.

Raw forum JSON stays local (archive/data/commons/ is gitignored). Curated
transcript markdown is produced later by the ingest step.

Usage:
    python3 scripts/crawl-ishtar-commons.py [--category 7 --category 10]
                                            [--delay 0.25] [--limit N]
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'archive', 'data', 'commons')
BASE = 'https://commons.ishtar-collective.net'


def get_json(url, retries=3):
    for attempt in range(retries):
        raw = subprocess.run(
            ['curl', '-sL', '--max-time', '60', '-A', 'Mozilla/5.0', url],
            capture_output=True, text=True).stdout
        try:
            return json.loads(raw)
        except Exception:
            if attempt + 1 < retries:
                time.sleep(1 + attempt)
    return None


def list_category(category, delay, start_page=0):
    topics = {}
    empty = 0
    for page in range(start_page, 60):
        d = get_json(f'{BASE}/c/{category}.json?page={page}')
        if not d:
            break
        batch = d.get('topic_list', {}).get('topics', [])
        if not batch:
            empty += 1
            if empty >= 3:
                break
            time.sleep(2)
            continue
        empty = 0
        new = 0
        for t in batch:
            if t['id'] in topics:
                continue
            topics[t['id']] = {
                'id': t['id'],
                'title': t.get('title'),
                'slug': t.get('slug'),
                'category_id': t.get('category_id'),
                'tags': t.get('tags') or [],
                'posts_count': t.get('posts_count'),
                'created_at': t.get('created_at'),
                'last_posted_at': t.get('last_posted_at'),
            }
            new += 1
        print(f'category {category} page {page}: +{new}', flush=True)
        if not new:
            empty += 1
            if empty >= 3:
                break
        time.sleep(delay)
    return topics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--category', type=int, action='append', default=None)
    parser.add_argument('--delay', type=float, default=0.25)
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--start-page', type=int, default=0)
    args = parser.parse_args()
    categories = args.category or [7, 10]
    os.makedirs(os.path.join(OUT, 'topics'), exist_ok=True)

    topics = {}
    existing_path = os.path.join(OUT, 'topics.jsonl')
    if os.path.exists(existing_path):
        for line in open(existing_path, encoding='utf-8'):
            try:
                t = json.loads(line)
                topics[t['id']] = t
            except Exception:
                pass
    for category in categories:
        topics.update(list_category(category, args.delay, args.start_page))
    if args.limit:
        topics = dict(list(topics.items())[:args.limit])

    with open(os.path.join(OUT, 'topics.jsonl'), 'w', encoding='utf-8') as fh:
        for t in topics.values():
            fh.write(json.dumps(t, ensure_ascii=False) + '\n')
    print(f'discovered {len(topics)} topics', flush=True)

    done = 0
    for t in topics.values():
        path = os.path.join(OUT, 'topics', f"{t['id']}.json")
        if os.path.exists(path):
            continue
        d = get_json(f"{BASE}/t/{t['id']}.json")
        if not d:
            print(f"skip {t['id']} (no data)", flush=True)
            continue
        posts = d.get('post_stream', {}).get('posts', [])
        record = {
            'id': t['id'],
            'title': d.get('title') or t['title'],
            'tags': d.get('tags') or t['tags'],
            'category_id': d.get('category_id') or t['category_id'],
            'created_at': d.get('created_at'),
            'posts_count': d.get('posts_count'),
            'cooked': posts[0].get('cooked', '') if posts else '',
        }
        json.dump(record, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
        done += 1
        if done % 25 == 0:
            print(f'fetched {done}/{len(topics)}', flush=True)
        time.sleep(args.delay)
    print(f'crawl complete: {done} new topics', flush=True)


if __name__ == '__main__':
    sys.exit(main())
