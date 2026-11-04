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
               'validated', 'published', 'proofed', 'cutscene'}
    bad = {r[0] for r in conn.execute('SELECT DISTINCT source_tier FROM transcripts')} - allowed
    assert not bad, f'unknown tiers: {bad}'


def classified():
    assert one('SELECT COUNT(*) FROM transcripts t LEFT JOIN transcript_classification c '
               'ON c.transcript_id=t.id WHERE c.transcript_id IS NULL') == 0


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


print('=== TAXONOMY DEEP TEST ===')
for name, fn in [
    ('source tiers present and known', tiers),
    ('every transcript classified', classified),
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
