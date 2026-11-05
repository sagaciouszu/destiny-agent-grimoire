#!/usr/bin/env python3
"""Deep taxonomy/model test for the additive layers.

Covers transcript tiers, classification integrity, seasons, events, lore,
seals and manifest links, plus API parity for the new lookups.
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'db'))
import api  # noqa: E402

DB = os.path.join(ROOT, 'db', 'grimoire.db')
PASS = FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f'  ✓ {name}')
        PASS += 1
    except Exception as e:
        print(f'  ✗ {name}: {e}')
        FAIL += 1


conn = sqlite3.connect(DB)
one = lambda q: conn.execute(q).fetchone()[0]


def tiers():
    assert one("SELECT COUNT(*) FROM transcripts WHERE source_tier IS NULL OR source_tier=''") == 0
    allowed = {'ishtar_main', 'ishtar_web', 'ishtar_commons', 'destinypedia',
               'youtube_captions', 'validated', 'published', 'proofed', 'cutscene'}
    bad = {r[0] for r in conn.execute('SELECT DISTINCT source_tier FROM transcripts')} - allowed
    assert not bad, f'unknown tiers: {bad}'


def classified():
    assert one('SELECT COUNT(*) FROM transcripts t LEFT JOIN transcript_classification c '
               'ON c.transcript_id=t.id WHERE c.transcript_id IS NULL') == 0


def speaker_identity():
    assert one("SELECT COUNT(*) FROM transcript_lines WHERE speaker='The Crow'") == 0
    assert one("SELECT COUNT(*) FROM transcript_lines WHERE speaker='Crow'") > 0
    assert one("SELECT COUNT(*) FROM speaker_aliases WHERE alias='The Crow' AND canonical='Crow'") == 1


def speaker_filter():
    from migrate import is_junk_speaker, canon_speaker
    # The Saint-14 family must never be dropped, even with a Roman numeral.
    for name in ('Saint-14', 'Saint-XIV', 'Saint XIV', 'Saint IV',
                 'The Saint', 'Saint', 'Kellbreaker'):
        assert not is_junk_speaker(name), f'{name} wrongly dropped'
        assert canon_speaker(name) == 'Saint-14', (name, canon_speaker(name))
    # Quest/step titles are still dropped.
    for title in ('Path of the Splicer II', 'Into the Depths VI', 'Act I'):
        assert is_junk_speaker(title), f'{title} wrongly kept'
    aliases = dict(conn.execute('SELECT alias, canonical FROM speaker_aliases'))
    for alias in ('Saint-XIV', 'Saint XIV', 'Saint IV', 'The Saint', 'Saint',
                  'Kellbreaker'):
        assert aliases.get(alias) == 'Saint-14', (alias, aliases.get(alias))
    variants = one("SELECT COUNT(*) FROM transcript_lines WHERE speaker IN "
                   "('Saint-XIV','Saint XIV','Saint IV','The Saint','Kellbreaker')")
    assert variants == 0, f'variant speakers leaked into the DB: {variants}'


def coverage_notes():
    allowed = {'no_dialogue', 'narration_only', 'dialogue_source_missing',
               'partial_transcript', 'unverified'}
    bad = {r[0] for r in conn.execute('SELECT DISTINCT status FROM coverage_notes')} - allowed
    assert not bad, f'unknown coverage statuses: {bad}'
    for kind, table in (('activity', 'activities'), ('season', 'seasons'), ('event', 'events')):
        orphans = one(f'SELECT COUNT(*) FROM coverage_notes n LEFT JOIN {table} x '
                      f"ON x.slug=n.slug WHERE n.entity_type='{kind}' AND x.slug IS NULL")
        assert orphans == 0, f'{kind} coverage-note orphans: {orphans}'
    # Every entity with zero transcripts must carry an explicit status.
    for kind, view in (('activity', 'v_activity_coverage'),
                       ('season', 'v_season_coverage'),
                       ('event', 'v_event_coverage')):
        unexplained = one(
            f"SELECT COUNT(*) FROM {view} v LEFT JOIN coverage_notes n "
            f"ON n.entity_type='{kind}' AND n.slug=v.slug "
            'WHERE v.transcripts=0 AND n.slug IS NULL')
        assert unexplained == 0, f'{kind} gaps without a note: {unexplained}'
    partial_without = one(
        "SELECT COUNT(*) FROM coverage_notes n LEFT JOIN v_activity_coverage a "
        "ON a.slug=n.slug WHERE n.status='partial_transcript' AND n.entity_type='activity' "
        'AND (a.slug IS NULL OR a.transcripts=0 OR a.lines=0)')
    assert partial_without == 0, f'partial notes without transcript: {partial_without}'
    season_partial_without = one(
        "SELECT COUNT(*) FROM coverage_notes n JOIN v_season_coverage s ON s.slug=n.slug "
        "WHERE n.entity_type='season' AND n.status='partial_transcript' "
        'AND (s.transcripts=0 OR s.lines=0)')
    assert season_partial_without == 0, 'season partial without transcript'


def refs():
    for kind, table in (('activity', 'activities'), ('season', 'seasons'),
                        ('event', 'events'), ('expansion', 'expansions')):
        col = kind + '_slug'
        n = one(f'SELECT COUNT(*) FROM transcript_classification c LEFT JOIN {table} x '
                f'ON x.slug=c.{col} WHERE c.{col} IS NOT NULL AND x.slug IS NULL')
        assert n == 0, f'{kind} orphans: {n}'


def seasons():
    nums = [r[0] for r in conn.execute('SELECT season_number FROM seasons ORDER BY 1')]
    assert nums == list(range(1, 29)), nums


def events():
    assert one('SELECT COUNT(*) FROM (SELECT event_slug,year FROM event_occurrences '
               'GROUP BY 1,2 HAVING COUNT(*)>1)') == 0


def lore():
    assert one('SELECT COUNT(*) FROM (SELECT hash FROM lore_entries GROUP BY 1 HAVING COUNT(*)>1)') == 0
    assert one("SELECT COUNT(*) FROM lore_entries WHERE is_duplicate=1 AND duplicate_of=''") == 0
    missing = one("SELECT COUNT(*) FROM lore_entries l WHERE l.is_duplicate=0 AND NOT EXISTS "
                  "(SELECT 1 FROM fts WHERE source='lore_entry' AND source_slug='lore-'||l.hash)")
    assert missing == 0, f'missing lore FTS rows: {missing}'
    assert one("SELECT COUNT(*) FROM lore_entries WHERE is_duplicate=0") > 1500


def seals():
    assert one('SELECT COUNT(*) FROM seal_records r LEFT JOIN seals s ON s.hash=r.seal_hash '
               'WHERE s.hash IS NULL') == 0
    assert one('SELECT COUNT(*) FROM seals') >= 60
    assert one('SELECT COUNT(*) FROM seal_records') >= 800


def manifest():
    assert one('SELECT COUNT(*) FROM manifest_activities') > 3000
    for kind, table in (('activity', 'activities'), ('season', 'seasons')):
        n = one(f"SELECT COUNT(*) FROM manifest_links l WHERE l.kind='{kind}' AND NOT EXISTS "
                f"(SELECT 1 FROM {table} x WHERE x.slug=l.curated_slug)")
        assert n == 0, f'{kind} link orphans: {n}'
    n = one("SELECT COUNT(*) FROM manifest_links l WHERE l.kind='activity' AND NOT EXISTS "
            '(SELECT 1 FROM manifest_activities m WHERE m.hash=l.manifest_hash)')
    assert n == 0, f'manifest hash orphans: {n}'


def metadata():
    assert one('SELECT COUNT(*) FROM transcript_lines WHERE section LIKE "++%"') == 0
    assert one('SELECT COUNT(*) FROM transcript_lines WHERE section != ""') > 100
    assert one('SELECT COUNT(*) FROM transcript_lines WHERE is_optional=1') > 0


def class_tags():
    tags = {r[0] for r in conn.execute("SELECT DISTINCT class_tag FROM transcript_lines WHERE class_tag!=''")}
    assert tags <= {'hunter', 'titan', 'warlock'}, tags
    assert tags == {'hunter', 'titan', 'warlock'}, tags
    optional = one("SELECT COUNT(*) FROM transcript_lines WHERE class_tag!='' AND is_optional=1")
    assert optional >= 3, optional


def api_lore():
    res = api.lore("Gate Lord's Eye")
    assert res and res['body'] and res['items']


def api_seal():
    rows = api.seals()
    assert len(rows) >= 60
    res = api.seal('Conqueror')
    assert res and res['records']


def api_canon():
    full = api.transcript('commons-1407-the-arms-dealer-strike', limit=1000)
    canon = api.transcript('commons-1407-the-arms-dealer-strike', limit=1000, canon_only=True)
    assert canon['total'] <= full['total']
    assert any(line['section'] for line in full['lines'])


def api_coverage():
    cov = api.coverage()
    zero = one('SELECT COUNT(*) FROM v_activity_coverage WHERE transcripts=0')
    assert len(cov['gaps']['activities_without_transcripts']) == zero
    assert cov['notes'], 'coverage notes missing'
    assert cov['gaps']['unexplained'] == [], cov['gaps']['unexplained']
    acts = {a['slug']: a for a in api.activities()}
    assert acts['ketchcrash']['coverage_status'] == 'partial_transcript'
    assert api.activity('ketchcrash')['coverage']['status'] == 'partial_transcript'
    seasons_ = {s['slug']: s for s in api.seasons()}
    assert seasons_['monument-of-triumph']['coverage_status'] == 'partial_transcript'


print('=== TAXONOMY DEEP TEST ===')
for name, fn in [
    ('source tiers present and known', tiers),
    ('every transcript classified', classified),
    ('Crow identity is canonical', speaker_identity),
    ('speaker filter keeps the Saint-14 family', speaker_filter),
    ('coverage gaps have explicit statuses', coverage_notes),
    ('classification references resolve', refs),
    ('seasons 1-28 unique', seasons),
    ('event occurrences unique', events),
    ('lore flags and search parity', lore),
    ('seal records resolve', seals),
    ('manifest catalogue and links resolve', manifest),
    ('section/optional metadata', metadata),
    ('class variant tags', class_tags),
    ('API lore lookup', api_lore),
    ('API seal lookup', api_seal),
    ('API canon-only and section', api_canon),
    ('API coverage gaps match DB', api_coverage),
]:
    check(name, fn)
conn.close()
print(f'\nPassed: {PASS} | Failed: {FAIL}')
sys.exit(1 if FAIL else 0)
