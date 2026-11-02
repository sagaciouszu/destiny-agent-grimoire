#!/usr/bin/env python3
"""Ishtar Collective scraper for interactions and items."""
import urllib.request, re, html, json, os, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = 'https://www.ishtar-collective.net'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; lore-archivist/1.0)'}

def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read().decode('utf-8', errors='ignore')
        except Exception:
            if i == retries-1: raise
            time.sleep(1.5*(i+1))

def clean(s):
    s = s.replace('\u2014','-').replace('\u2013','-').replace('\u2018',"'").replace('\u2019',"'").replace('\u201c','"').replace('\u201d','"')
    return s.strip()

def body_from(h):
    m = re.search(r'<div class="(?:description highlightable|item-description)">(.*?)</div>', h, re.S)
    if not m: return ''
    raw = m.group(1).replace('</p>','\n\n')
    raw = re.sub(r'<br\s*/?>','\n',raw)
    t = re.sub(r'<[^>]+>','',raw)
    return clean(html.unescape(t))

def title_of(h):
    m = re.search(r'<title>(.*?)</title>',h)
    if not m: return 'Unknown','Unknown'
    raw = html.unescape(m.group(1)).split(' \u2014 ')[0]
    parts = [p.strip() for p in re.split(r'\s+[—–-]\s+', html.unescape(m.group(1)))]
    if len(parts) >= 2:
        return clean(parts[0]), clean(parts[1])
    return clean(parts[0]), clean(parts[0])

def release_of(h):
    m = re.search(r'Added In\s*</div>\s*<div[^>]*class="section-data"[^>]*>.*?(?:<abbr[^>]*>|<a[^>]*>)([^<]+)', h, re.S)
    return clean(m.group(1)) if m else ''

def type_of(h):
    m = re.search(r'Type\s*</div>\s*<div[^>]*class="section-data"[^>]*>\s*<a[^>]*>([^<]+)</a>', h, re.S)
    if not m:
        m = re.search(r'>Type<.*?section-data[^>]*>\s*([^<]+)', h, re.S)
    return clean(m.group(1)) if m else ''

def parse_interaction(slug):
    h = fetch(f'{BASE}/interactions/{slug}')
    speaker, title = title_of(h)
    return {'kind':'interaction','slug':slug,'title':title,'speaker':speaker,
            'text':body_from(h),'release':release_of(h),'type':'','url':f'{BASE}/interactions/{slug}'}

def parse_item(slug):
    h = fetch(f'{BASE}/items/{slug}')
    title, _ = title_of(h)
    return {'kind':'item','slug':slug,'title':title,'speaker':'',
            'text':body_from(h),'release':release_of(h),'type':type_of(h),
            'url':f'{BASE}/items/{slug}'}

def list_slugs(kind, page):
    h = fetch(f'{BASE}/{kind}?page={page}' if page>1 else f'{BASE}/{kind}')
    pats = re.findall(r'href="/'+kind+r'/([^"]+)"', h)
    return sorted(set(s for s in pats if not s.startswith('page/')))

def scrape(kind, parser, out_path, start_page, end_page, workers=8):
    done = set()
    if os.path.exists(out_path):
        for line in open(out_path, encoding='utf-8'):
            try: done.add(json.loads(line)['slug'])
            except: pass
    results = []
    pages = list(range(start_page, end_page+1))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(list_slugs, kind, p): p for p in pages}
        all_slugs = []
        for f in as_completed(futs):
            try: all_slugs.extend(f.result())
            except Exception as e: print(f'  page fail {futs[f]}: {e}', flush=True)
    new = sorted(set(all_slugs) - done)
    print(f'{kind}: {len(new)} new slugs', flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(parser, s): s for s in new}
        for i, f in enumerate(as_completed(futs)):
            try:
                results.append(f.result())
            except Exception as e:
                print(f'  fail {futs[f]}: {e}', flush=True)
            if i % 100 == 0 and i:
                with open(out_path,'a',encoding='utf-8') as fh:
                    for r in results: fh.write(json.dumps(r,ensure_ascii=False)+'\n')
                results = []
                print(f'  ...{i}/{len(new)}', flush=True)
    if results:
        with open(out_path,'a',encoding='utf-8') as fh:
            for r in results: fh.write(json.dumps(r,ensure_ascii=False)+'\n')
    print(f'{kind}: done, total lines = {sum(1 for _ in open(out_path,encoding="utf-8"))}', flush=True)

if __name__ == '__main__':
    os.makedirs('archive/data', exist_ok=True)
    kind = sys.argv[1]
    s, e = int(sys.argv[2]), int(sys.argv[3])
    if kind == 'interactions':
        scrape('interactions', parse_interaction, 'archive/data/interactions.jsonl', s, e)
    elif kind == 'items':
        scrape('items', parse_item, 'archive/data/items.jsonl', s, e)
