#!/usr/bin/env python3
"""Additive Bungie manifest reconciliation.

Run after `db/migrate.py` and `db/enrich_lore.py`:

    python3 db/enrich_manifest.py

Creates `manifest_activities` (the full 3,744-row catalogue) and
`manifest_links` (curated activity/season -> manifest hash). It never edits the
curated `activities` or `seasons` rows; conflicts are reported, not applied.
"""
import json
import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from migrate import DB_PATH as DEFAULT_DB  # noqa: E402

DB_PATH = os.environ.get('GRIMOIRE_DB') or DEFAULT_DB
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAN = os.path.join(ROOT, 'archive', 'data', 'manifest')

TYPE_MAP = {
    'Raid': 'raid', 'Dungeon': 'dungeon', 'Strike': 'strike', 'Nightfall': 'strike',
    'Story': 'story', 'Mission': 'story', 'Seasonal Arena': 'seasonal',
    'Lost Sector': 'lost_sector', 'Nightmare Hunt': 'seasonal', 'Solo Ops': 'story',
    'The Crucible': 'crucible', 'Iron Banner': 'crucible', 'Rumble': 'crucible',
    'Gambit': 'gambit', 'Explore': 'patrol',
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS manifest_activities (
    hash INTEGER PRIMARY KEY,
    name TEXT,
    activity_type TEXT,
    manifest_type TEXT,
    modes TEXT,
    season_hash INTEGER,
    season_name TEXT,
    destination_hash INTEGER,
    is_playlist INTEGER
);
CREATE INDEX IF NOT EXISTS idx_ma_type ON manifest_activities(activity_type);
CREATE TABLE IF NOT EXISTS manifest_links (
    kind TEXT NOT NULL,
    curated_slug TEXT NOT NULL,
    manifest_hash INTEGER NOT NULL,
    match TEXT,
    PRIMARY KEY (kind, curated_slug, manifest_hash)
);
"""


def norm_name(value):
    value = (value or '').lower().replace("'", '').replace('’', '')
    value = re.sub(r'[^a-z0-9 ]+', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    if value.startswith('the '):
        value = value[4:]
    return value


def base_name(value):
    return norm_name((value or '').split(':')[0])


def main():
    seasons = json.load(open(os.path.join(MAN, 'seasons.json'), encoding='utf-8'))
    activities = json.load(open(os.path.join(MAN, 'activities.json'), encoding='utf-8'))
    version = json.load(open(os.path.join(MAN, 'manifest.json'), encoding='utf-8')).get('version')

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.execute('DELETE FROM manifest_activities')
    conn.execute('DELETE FROM manifest_links')

    for a in activities:
        conn.execute(
            'INSERT OR REPLACE INTO manifest_activities '
            '(hash,name,activity_type,manifest_type,modes,season_hash,season_name,'
            'destination_hash,is_playlist) VALUES (?,?,?,?,?,?,?,?,?)',
            (a['hash'], a['name'], TYPE_MAP.get(a.get('activityType'), 'other'),
             a.get('activityType'), ','.join(a.get('modes') or []),
             a.get('seasonHash'), a.get('seasonName'), a.get('destinationHash'),
             1 if a.get('isPlaylist') else 0))

    # Curated activity -> manifest hashes by base name.
    curated = conn.execute('SELECT slug,name,activity_type FROM activities').fetchall()
    by_base = {}
    for a in activities:
        by_base.setdefault(base_name(a['name']), []).append(a)
    linked = 0
    conflicts = []
    for slug, name, atype in curated:
        matches = by_base.get(base_name(name), [])
        for m in matches:
            conn.execute('INSERT OR IGNORE INTO manifest_links '
                         '(kind,curated_slug,manifest_hash,match) VALUES (?,?,?,?)',
                         ('activity', slug, m['hash'], 'name'))
            linked += 1
        if matches:
            mtypes = {TYPE_MAP.get(m.get('activityType'), 'other') for m in matches}
            if mtypes and atype not in mtypes:
                conflicts.append({'activity': slug, 'curated_type': atype,
                                  'manifest_types': sorted(mtypes)})

    # Curated season -> manifest season hash by number.
    manifest_by_number = {s['seasonNumber']: s for s in seasons if s.get('seasonNumber')}
    season_conflicts = []
    for num, slug, name, stype, *rest in conn.execute(
            'SELECT season_number,slug,name,season_type FROM seasons').fetchall():
        m = manifest_by_number.get(num)
        if not m:
            season_conflicts.append({'season': slug, 'number': num, 'manifest': None})
            continue
        conn.execute('INSERT OR IGNORE INTO manifest_links '
                     '(kind,curated_slug,manifest_hash,match) VALUES (?,?,?,?)',
                     ('season', slug, m['hash'], 'number'))
        if norm_name(m['name']) and norm_name(m['name']) != norm_name(name):
            season_conflicts.append({'season': slug, 'number': num,
                                     'curated_name': name, 'manifest_name': m['name']})

    conn.execute("INSERT OR REPLACE INTO meta (key,value) VALUES ('manifest_version',?)",
                 (version or '',))
    conn.execute("INSERT OR REPLACE INTO meta (key,value) VALUES ('manifest_activities',?)",
                 (str(len(activities)),))
    conn.commit()
    conn.execute('PRAGMA journal_mode=DELETE')
    conn.execute('VACUUM')
    conn.close()

    report = {'manifest_version': version, 'manifest_seasons': len(seasons),
              'manifest_activities': len(activities), 'activity_links': linked,
              'activity_type_conflicts': conflicts, 'season_conflicts': season_conflicts}
    json.dump(report, open(os.path.join(MAN, 'reconcile-report.json'), 'w'), indent=2)
    print(f'manifest {version}: {len(seasons)} seasons, {len(activities)} activities, '
          f'{linked} activity links, {len(conflicts)} type conflicts, '
          f'{len(season_conflicts)} season conflicts')


if __name__ == '__main__':
    main()
