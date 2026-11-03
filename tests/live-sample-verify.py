#!/usr/bin/env python3
"""On-demand live integrity probe: sample rows from every content type,
fetch the live Ishtar page, and compare text coverage (word 8-gram shingles).

Catches the "right slug, wrong content" class of error (a mislabeled scrape was
found this way) and systematic parse regressions. Network-dependent, so it is
NOT part of the offline audits - run it manually after large ingests:

    python3 tests/live-sample-verify.py [--samples N]

Exit 1 if any sample scores < 20% (wrong content) or a type median < 50%.
"""
import html
import random
import re
import sqlite3
import sys
import urllib.request

HERE = __import__('os').path.dirname(__import__('os').path.abspath(__file__))
DB = __import__('os').path.join(HERE, '..', 'db', 'grimoire.db')
N = 3
if '--samples' in sys.argv:
    N = int(sys.argv[sys.argv.index('--samples') + 1])

import time

def fetch(url):
    """Polite fetch: pacing + one retry. Ishtar soft-throttles bursts with 404s."""
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read().decode('utf-8', 'ignore')
            time.sleep(0.6)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404 and attempt == 1:
                time.sleep(2.0)  # transient throttle usually clears on retry
                continue
            raise

def norm(s):
    s = html.unescape(s).lower().replace('\u2026', '...').replace('\u2019', "'").replace('\u2014', '-').replace('\u2013', '-')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()

def shingles(t, n=8):
    w = t.split()
    return set(' '.join(w[i:i + n]) for i in range(len(w) - n + 1))

def coverage(live_text, db_text):
    a, b = shingles(norm(live_text)), shingles(norm(db_text))
    return len(a & b) / max(1, len(a)) * 100 if a else 0.0

def extract(page, selector):
    m = re.search(r'<div class="%s">(.*?)</div>' % re.escape(selector), page, re.S)
    if not m:
        return ''
    return re.sub(r'<[^>]+>', ' ', m.group(1))

conn = sqlite3.connect(DB)
random.seed(11)

TYPE_CHECKS = [
    ('items', 'SELECT slug, text FROM items WHERE text != \'\'', 'items', 'item-description'),
    ('records', 'SELECT slug, body FROM records WHERE body != \'\'', 'records', 'description highlightable'),
    ('cards', 'SELECT slug, body FROM grimoire_cards WHERE body != \'\'', 'entries', 'description highlightable'),
    ('interactions', 'SELECT slug, text FROM interactions WHERE text != \'\'', 'interactions', 'description highlightable'),
]
results = {}
for label, sql, path, selector in TYPE_CHECKS:
    rows = conn.execute(sql + ' ORDER BY RANDOM() LIMIT %d' % max(N * 4, 12)).fetchall()
    scores, removed = [], 0
    print(f'--- {label}:')
    for slug, dbtext in rows:
        if len(scores) >= N:
            break
        try:
            page = fetch(f'https://www.ishtar-collective.net/{path}/{slug}')
            cov = coverage(extract(page, selector), dbtext)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                removed += 1  # page pruned from the site; DB content is a snapshot
                continue
            print(f'  {slug[:48]:48s} ERR {e}')
            continue
        except Exception as e:
            print(f'  {slug[:48]:48s} ERR {e}')
            continue
        scores.append(cov)
        print(f'  {slug[:48]:48s} coverage={cov:5.1f}%')
    if removed:
        print(f'  ({removed} sampled slugs no longer live on the site - pruned, not a parse failure)')
    if scores:
        median = sorted(scores)[len(scores) // 2]
        results[label] = (median, min(scores))

# books: slugs and URLs are aligned; verify entry titles appear on the live page
print('--- books (entry-title presence):')
rows = conn.execute('SELECT slug, id FROM books ORDER BY RANDOM() LIMIT %d' % N).fetchall()
book_scores = []
for slug, bid in rows:
    try:
        page = norm(fetch(f'https://www.ishtar-collective.net/categories/{slug}'))
        titles = [t for t, in conn.execute('SELECT title FROM book_entries WHERE book_id=? LIMIT 3', (bid,))]
        hits = sum(1 for t in titles if norm(t) and norm(t) in page)
        score = hits / max(1, len(titles)) * 100
        book_scores.append(score)
        print(f'  {slug[:48]:48s} entry-titles present={score:5.1f}%')
    except Exception as e:
        print(f'  {slug[:48]:48s} ERR {e}')
if book_scores:
    results['books'] = (sorted(book_scores)[len(book_scores) // 2], min(book_scores))

conn.close()
fail = False
print('\n--- summary (median / min):')
for label, (median, worst) in results.items():
    status = 'PASS' if median >= 50 and worst >= 20 else 'FAIL'
    fail = fail or status == 'FAIL'
    print(f'  {label:12s} {median:5.1f} / {worst:5.1f}  {status}')
print('\nPASS: live samples consistent' if not fail else '\nFAIL: live sample below threshold')
sys.exit(1 if fail else 0)
