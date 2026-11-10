#!/usr/bin/env python3
"""Pass 1: overlap content check between curated markdown transcripts and the
raw web scrape for slugs present in both sources.

migrate.py loads the curated markdown and SKIPS the web version of shared
slugs (markdown carries Release/Characters/Arc metadata). This verifies that
the skipped web content agrees with what actually shipped, using word 8-gram
shingles (segmentation-independent).

Exit codes:
  0 = all shared slugs agree (review list may be non-empty)
  1 = a shared slug has near-zero overlap = wrong content under the same slug
      (or the overlap set itself is suspiciously small)

Coverage < 60% is printed as REVIEW: the curated markdown may be lossy vs the
web scrape (candidates for combining the missing lines).
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, 'archive', 'data', 'transcripts_overlap.jsonl')  # fresh fetch of the shared slugs
MD_DIR = os.path.join(ROOT, 'source', 'transcripts')
SHINGLE = 8
FAIL_THRESHOLD = 10.0    # wrong-content-under-slug
REVIEW_THRESHOLD = 60.0  # possibly lossy markdown

def norm(s):
    s = s.lower().replace('\u2026', '...').replace('\u2019', "'").replace('\u2014', '-').replace('\u2013', '-')
    return re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]+', ' ', s)).strip()

def shingles(text, n=SHINGLE):
    w = text.split()
    return set(' '.join(w[i:i+n]) for i in range(len(w) - n + 1))

def md_text(path):
    """Markdown content minus title/meta/heading markers and meta bullets."""
    out = []
    for line in open(path, encoding='utf-8', errors='ignore'):
        st = line.strip()
        if not st or st.startswith('#'):
            continue
        # metadata bullets (- Source:, - Release:, - Drifter Beats:, ...)
        if re.match(r'^-\s*[A-Za-z][A-Za-z /&]+:', st):
            continue
        out.append(st)
    return ' '.join(out)

CHROME = re.compile(
    r'^(by\s+(Destiny|Ishtar|Bungie)|Act\s+[IVX0-9]+\b.*|Category\b|Transcript\b|Watch\b|Source\b)', re.I)

def web_text(d):
    """Web content minus page chrome (nav/attribution/chapter headings)."""
    out = []
    for l in d.get('lines', []):
        txt = html.unescape(l.get('text', '')).strip()
        sp = l.get('speaker', '')
        if not txt:
            continue
        if sp in {'Category', 'Ghost Scan', 'Quest', 'Sources', 'Note'}:
            continue
        if not sp and CHROME.match(txt):
            continue
        if not sp and ' | ' in txt:  # related-content nav rows
            continue
        out.append((sp + ' ' + txt).strip() if sp else txt)
    return ' '.join(out)

web = {}
for ln in open(WEB, encoding='utf-8'):
    try:
        d = json.loads(ln)
    except Exception:
        continue
    web[d['slug']] = web_text(d)

# filename <-> "- Source:" URL slug consistency (catches mislabeled scrapes)
mislabeled = []
for fname in sorted(os.listdir(MD_DIR)):
    if not fname.endswith('.md') or fname == 'index.md':
        continue
    path = os.path.join(MD_DIR, fname)
    src = None
    for line in open(path, encoding='utf-8', errors='ignore'):
        if line.startswith('- Source:'):
            src = line.split('Source:', 1)[1].strip()
            break
    if not src or 'ishtar-collective' not in src:
        continue  # non-Ishtar provenance (youtube-*, weblore-*, ingame-quotes-*)
    m = re.search(r'/transcripts/([^/\s]+)', src)
    # Known-benign renames: the file keeps the short DB slug; the Ishtar story
    # page lives under the `story-` prefix (verified 2026-11-10). All three were
    # ingested in v0.35.0 from the story pages.
    ALLOW = {('ace-in-the-hole', 'quest-ace-in-the-hole'),
             ('awaken-queensguard', 'story-awaken-queensguard'),
             ('retribution', 'story-retribution'),
             ('we-stand-unbroken', 'story-we-stand-unbroken')}
    if m and m.group(1) != fname[:-3] and (fname[:-3], m.group(1)) not in ALLOW:
        mislabeled.append((fname[:-3], m.group(1)))
if mislabeled:
    print(f'FAIL ({len(mislabeled)}) - filename does not match its Source slug:')
    for name, url in mislabeled:
        print(f'  {name!r} -> {url!r}')
    sys.exit(1)
print('filename/source-slug check: OK')

md_slugs = {f[:-3] for f in os.listdir(MD_DIR) if f.endswith('.md') and f != 'index.md'}
shared = sorted(set(web) & md_slugs)
print(f'web entries: {len(web)} | markdown transcripts: {len(md_slugs)} | shared slugs: {len(shared)}')

if len(shared) < 40:
    print('FAIL: overlap set suspiciously small (expected ~54 shared slugs)')
    sys.exit(1)

failures, review, rows = [], [], []
for slug in shared:
    ws = shingles(norm(web[slug]))
    ms = shingles(norm(md_text(os.path.join(MD_DIR, slug + '.md'))))
    if not ws or not ms:
        coverage = 0.0
    else:
        coverage = len(ws & ms) / len(ws) * 100
    rows.append((coverage, slug))
    if coverage < FAIL_THRESHOLD:
        failures.append((slug, coverage))
    elif coverage < REVIEW_THRESHOLD:
        review.append((slug, coverage))

rows.sort()
print(f'\nweb->markdown coverage across {len(rows)} shared slugs:')
print(f'  min {rows[0][0]:.1f}% ({rows[0][1]}) | median {rows[len(rows)//2][0]:.1f}% | max {rows[-1][0]:.1f}%')

if review:
    print(f'\nREVIEW ({len(review)}) - curated markdown may be lossy vs web scrape:')
    for slug, cov in sorted(review, key=lambda x: x[1]):
        print(f'  {cov:5.1f}%  {slug}')
else:
    print('\nREVIEW: none (all shared slugs above 60% coverage)')

if failures:
    print(f'\nFAIL ({len(failures)}) - same slug, different content:')
    for slug, cov in failures:
        print(f'  {cov:5.1f}%  {slug}')
    sys.exit(1)

print('\nPASS: overlap set consistent')
