#!/usr/bin/env python3
"""Fetch and flatten the Bungie Destiny 2 manifest.

Credentials (never committed):
  BUNGIE_API_KEY environment variable, or
  ~/.config/destiny-agent/bungie.key containing the key on one line.

Usage:
  python3 archive/data/fetch_manifest.py --check
  python3 archive/data/fetch_manifest.py --fetch
  python3 archive/data/fetch_manifest.py --extract
  python3 archive/data/fetch_manifest.py --fetch --extract

Outputs (archive/data/manifest/):
  manifest.json            index + version
  seasons.json             hash, name, seasonNumber, start, end, type
  activities.json          hash, name, type, modes, season, destination
  item_seasons.jsonl       hash, name, itemType, seasonHash, seasonName

The extractor is read-only with respect to grimoire.db. Applying manifest
values to the database is a separate, reviewed step (db/taxonomy.py).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'archive', 'data', 'manifest')
API = 'https://www.bungie.net/Platform'
CDN = 'https://www.bungie.net'
KEY_FILE = os.path.expanduser('~/.config/destiny-agent/bungie.key')

DEFS = [
    'DestinySeasonDefinition',
    'DestinyActivityDefinition',
    'DestinyActivityModeDefinition',
    'DestinyActivityTypeDefinition',
    'DestinyInventoryItemDefinition',
    'DestinyEventCardDefinition',
]


def api_key():
    key = os.environ.get('BUNGIE_API_KEY', '').strip()
    if not key and os.path.exists(KEY_FILE):
        key = open(KEY_FILE, encoding='utf-8').read().strip()
    if not key:
        raise SystemExit(
            'BUNGIE_API_KEY not set. Export it or write it to '
            f'{KEY_FILE} (chmod 600). Do not commit the key.')
    return key


def get_json(url, key=None, retries=3):
    headers = {'User-Agent': 'destiny-agent-grimoire/0.21'}
    if key:
        headers['X-API-Key'] = key
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt + 1 < retries:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError('unreachable')


def manifest_index(key):
    data = get_json(f'{API}/Destiny2/Manifest/', key)
    return data['Response']


def fetch():
    key = api_key()
    index = manifest_index(key)
    os.makedirs(OUT, exist_ok=True)
    json.dump(index, open(os.path.join(OUT, 'manifest.json'), 'w'), indent=2)
    paths = index['jsonWorldComponentContentPaths']['en']
    for name in DEFS:
        rel = paths.get(name)
        if not rel:
            print(f'skip {name}: not in manifest')
            continue
        dest = os.path.join(OUT, name + '.json')
        print(f'fetch {name} -> {dest}')
        data = get_json(CDN + rel, key)
        json.dump(data, open(dest, 'w'), separators=(',', ':'))
    print(f'manifest version: {index.get("version")}')


def load(name):
    path = os.path.join(OUT, name + '.json')
    if not os.path.exists(path):
        raise SystemExit(f'missing {path}; run --fetch first')
    return json.load(open(path, encoding='utf-8'))


def name_of(defn):
    return (defn.get('displayProperties') or {}).get('name') or ''


def extract():
    seasons_def = load('DestinySeasonDefinition')
    activities_def = load('DestinyActivityDefinition')
    modes_def = load('DestinyActivityModeDefinition')
    types_def = load('DestinyActivityTypeDefinition')

    modes = {int(k): name_of(v) for k, v in modes_def.items()}
    types = {int(k): name_of(v) for k, v in types_def.items()}
    season_name = {}
    seasons = []
    for k, d in seasons_def.items():
        h = int(d.get('hash', k))
        name = name_of(d)
        season_name[h] = name
        seasons.append({
            'hash': h,
            'name': name,
            'seasonNumber': d.get('seasonNumber'),
            'seasonType': d.get('seasonType'),
            'startDate': d.get('startDate'),
            'endDate': d.get('endDate'),
        })
    seasons.sort(key=lambda s: (s['seasonNumber'] is None, s['seasonNumber'], s['name']))
    json.dump(seasons, open(os.path.join(OUT, 'seasons.json'), 'w'), indent=2)

    activities = []
    for k, d in activities_def.items():
        name = name_of(d)
        if not name:
            continue
        sh = d.get('seasonHash')
        activities.append({
            'hash': int(d.get('hash', k)),
            'name': name,
            'activityType': types.get(d.get('activityTypeHash')),
            'modes': [modes.get(m) for m in d.get('activityModeHashes', []) if modes.get(m)],
            'seasonHash': sh,
            'seasonName': season_name.get(sh),
            'destinationHash': d.get('destinationHash'),
            'isPlaylist': bool(d.get('isPlaylist')),
        })
    activities.sort(key=lambda a: (a['activityType'] or '', a['name']))
    json.dump(activities, open(os.path.join(OUT, 'activities.json'), 'w'), indent=2)

    items_def = load('DestinyInventoryItemDefinition')
    count = 0
    with open(os.path.join(OUT, 'item_seasons.jsonl'), 'w', encoding='utf-8') as fh:
        for k, d in items_def.items():
            sh = d.get('seasonHash')
            if not sh:
                continue
            rec = {
                'hash': int(d.get('hash', k)),
                'name': name_of(d),
                'itemType': d.get('itemType'),
                'itemTypeDisplayName': d.get('itemTypeDisplayName'),
                'seasonHash': sh,
                'seasonName': season_name.get(sh),
                'redacted': bool(d.get('redacted')),
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + '\n')
            count += 1
    print(f'seasons: {len(seasons)}, activities: {len(activities)}, items with season: {count}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='verify the key and print manifest version')
    parser.add_argument('--fetch', action='store_true', help='download manifest definitions')
    parser.add_argument('--extract', action='store_true', help='flatten downloaded definitions')
    args = parser.parse_args()
    if not any((args.check, args.fetch, args.extract)):
        parser.print_help()
        return 0
    if args.check:
        idx = manifest_index(api_key())
        print('manifest version:', idx.get('version'))
    if args.fetch:
        fetch()
    if args.extract:
        extract()
    return 0


if __name__ == '__main__':
    sys.exit(main())
