#!/usr/bin/env python3
"""Game-caption test: the extracted subtitle corpus is canonical and clean.

Captions (source_tier='game_caption') are English text pulled from the local
build. This guards the invariants that make them safe to search:

  - headers carry the tier, language and a taxonomy row;
  - every caption line keeps StringReference provenance;
  - every processed record line keeps a sighting, including merged lines;
  - no caption line duplicates text already in canon (search never returns the
    same line twice, and no second attribution is introduced);
  - activity facets are curated ('derived') and their vocabulary resolves to
    taxonomy slugs;
  - FTS and the verification index mirror the caption lines exactly;
  - stage direction / stat lines stay demoted;
  - persona canon counts exclude captions (persona.json stays authoritative).

Run: python3 tests/caption-test.py
"""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'db'))
import api       # noqa: E402
import migrate   # noqa: E402  (norm_text: one normalisation implementation)
import taxonomy  # noqa: E402

DB = os.environ.get('GRIMOIRE_DB') or os.path.join(ROOT, 'db', 'grimoire.db')
JSONL = os.path.join(ROOT, 'archive', 'data', 'captions.jsonl')
LIVE_JSONL = os.path.join(ROOT, 'archive', 'data', 'captions-live.jsonl')
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


conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
one = lambda q: conn.execute(q).fetchone()[0]
CAP = "t.source_tier='game_caption'"


def headers():
    """Caption transcripts are tagged, English and classified."""
    n = one(f'SELECT COUNT(*) FROM transcripts t WHERE {CAP}')
    assert n > 0, 'no caption transcripts loaded'
    assert one(f"SELECT COUNT(*) FROM transcripts t WHERE {CAP} "
               "AND (lang IS NULL OR lang != 'en')") == 0, 'caption lang != en'
    assert one(f"SELECT COUNT(*) FROM transcripts t WHERE {CAP} "
               "AND (title IS NULL OR title='')") == 0, 'caption without title'
    assert one(f"SELECT COUNT(*) FROM transcripts t LEFT JOIN transcript_classification c "
               f"ON c.transcript_id=t.id WHERE {CAP} AND c.transcript_id IS NULL") == 0, \
        'caption transcript without a taxonomy row'
    assert one(f"SELECT COUNT(*) FROM transcripts t WHERE {CAP} "
               "AND source_url != ''") == 0, \
        'caption source_url must stay empty (package provenance lives in caption_provenance)'


def provenance():
    """Every caption line keeps its StringReference provenance; no orphans."""
    lines = one(f'SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t '
                f'ON t.id=tl.transcript_id WHERE {CAP}')
    assert lines > 0, 'no caption lines'
    unprovenanced = one(
        'SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id '
        f"LEFT JOIN caption_provenance p ON p.line_id=tl.id WHERE {CAP} AND p.line_id IS NULL")
    assert unprovenanced == 0, f'{unprovenanced} caption lines without provenance'
    orphans = one('SELECT COUNT(*) FROM caption_provenance p '
                  'LEFT JOIN transcript_lines tl ON tl.id=p.line_id WHERE tl.id IS NULL')
    assert orphans == 0, f'{orphans} orphaned provenance rows'
    # provenance is one row per line, so a reused canon line keeps at most one.
    dup = one('SELECT COUNT(*) FROM (SELECT line_id FROM caption_provenance '
              'GROUP BY line_id HAVING COUNT(*) > 1)')
    assert dup == 0, f'{dup} lines with duplicate provenance'
    meta = dict(conn.execute("SELECT key, value FROM meta WHERE key='caption_provenance'"))
    assert meta.get('caption_provenance') == str(one('SELECT COUNT(*) FROM caption_provenance')), \
        'meta caption_provenance is stale'


def build_scope():
    """Every provenance row names a registered build; live rows are traceable.

    The corpus holds two game builds. Each row must point at `builds`, and a
    build that does not expose per-line StringReference hashes (the v53 live
    client) must still be traceable to the exact slot it came from.
    """
    stale = one('SELECT COUNT(*) FROM caption_provenance p '
                "LEFT JOIN builds b ON b.build_id=p.source_build WHERE b.build_id IS NULL")
    assert stale == 0, f'{stale} caption provenance rows name an unregistered build'
    per_build = dict(conn.execute(
        'SELECT source_build, COUNT(*) FROM caption_provenance GROUP BY 1'))
    assert per_build, 'no caption provenance rows at all'
    live = per_build.get('build-25932352', 0)
    if live:
        missing = one(
            "SELECT COUNT(*) FROM caption_provenance WHERE source_build='build-25932352' "
            'AND (record_index IS NULL OR record_part IS NULL OR source_pkg IS NULL '
            'OR bank_entry IS NULL)')
        assert missing == 0, f'{missing} live caption rows without slot provenance'
        collapsed = one(
            "SELECT COUNT(*) FROM caption_provenance WHERE source_build='build-25932352' "
            "AND source_pkg NOT GLOB '*_[0-9a-f][0-9a-f][0-9a-f][0-9a-f]'")
        assert collapsed == 0, f'{collapsed} live caption rows lost their package id'
        dup_slot = one(
            "SELECT COUNT(*) FROM (SELECT source_pkg, bank_entry, record_index, record_part "
            "FROM caption_provenance WHERE source_build='build-25932352' "
            'GROUP BY 1,2,3,4 HAVING COUNT(*) > 1)')
        assert dup_slot == 0, f'{dup_slot} live caption slots map to more than one line'
        misfiled = one(
            "SELECT COUNT(*) FROM caption_provenance p JOIN transcript_lines tl "
            "ON tl.id=p.line_id WHERE p.source_build='build-25932352' "
            "AND tl.speaker_source='build-25932352' AND p.kind != 'dialogue' "
            "AND NOT EXISTS (SELECT 1 FROM caption_sightings s "
            "WHERE s.line_id=p.line_id AND s.source_build=p.source_build "
            "AND s.kind='dialogue')")
        assert misfiled == 0, f'{misfiled} live-attributed lines have no dialogue sighting'


def sightings():
    """Every processed caption line is retained, including lines provenance drops.

    Expected shape comes from the source JSONL, never a constant: one sighting
    per non-empty record line, grouped by `(build, record slug)`. That catches a
    key that silently collapses sunrise lines sharing a bank entry.
    """
    records = []
    for path in (JSONL, LIVE_JSONL):
        with open(path, encoding='utf-8') as fh:
            records.extend(json.loads(raw) for raw in fh)
    slugs = [r['slug'] for r in records]
    assert len(slugs) == len(set(slugs)), 'caption record slugs are not unique'

    per_record, per_build = {}, {}
    sunrise_texts, live_texts = set(), set()
    for rec in records:
        build = rec.get('source_build') or 'sunrise-pre-bl'
        count = 0
        for line in rec.get('lines', []):
            text = (line.get('text') or '').strip()
            if not text:
                continue
            count += 1
            norm = migrate.norm_text(text)
            (sunrise_texts if build == 'sunrise-pre-bl' else live_texts).add(norm)
        if count:
            per_record[(build, rec['slug'])] = count
            per_build[build] = per_build.get(build, 0) + count

    actual_record = {(b, s): n for b, s, n in conn.execute(
        'SELECT source_build, source_slug, COUNT(*) FROM caption_sightings '
        'GROUP BY 1,2')}
    assert actual_record == per_record, 'sightings do not match the source record lines'
    actual_build = dict(conn.execute(
        'SELECT source_build, COUNT(*) FROM caption_sightings GROUP BY 1'))
    assert actual_build == per_build, f'sighting build totals differ: {actual_build} != {per_build}'

    missing = one(
        'SELECT COUNT(*) FROM caption_provenance p '
        'LEFT JOIN caption_sightings s ON s.line_id=p.line_id '
        'AND s.source_build=p.source_build '
        "AND COALESCE(s.source_pkg,'')=COALESCE(p.source_pkg,'') "
        'AND COALESCE(s.source_entry,-1)=COALESCE(p.source_entry,-1) '
        'AND COALESCE(s.bank_entry,-1)=COALESCE(p.bank_entry,-1) '
        'AND COALESCE(s.record_index,-1)=COALESCE(p.record_index,-1) '
        'AND COALESCE(s.record_part,-1)=COALESCE(p.record_part,-1) '
        'WHERE s.line_id IS NULL')
    assert missing == 0, f'{missing} provenance rows have no matching sighting'
    orphan = one('SELECT COUNT(*) FROM caption_sightings s '
                 'LEFT JOIN transcript_lines tl ON tl.id=s.line_id WHERE tl.id IS NULL')
    assert orphan == 0, f'{orphan} orphaned sightings'
    stale = one('SELECT COUNT(*) FROM caption_sightings s '
                'LEFT JOIN builds b ON b.build_id=s.source_build WHERE b.build_id IS NULL')
    assert stale == 0, f'{stale} sightings name an unregistered build'
    assert conn.execute('PRAGMA foreign_key_check').fetchall() == [], \
        'foreign key check failed'
    assert one('SELECT COUNT(DISTINCT line_id) FROM caption_sightings') == \
        one('SELECT COUNT(*) FROM caption_provenance'), \
        'sighting line set does not match provenance'

    multi = one('SELECT COUNT(*) FROM (SELECT line_id FROM caption_sightings '
                'GROUP BY 1 HAVING COUNT(DISTINCT source_build) > 1)')
    expected_multi = len(sunrise_texts & live_texts)
    assert multi == expected_multi, \
        f'{multi} lines seen by both builds, source says {expected_multi}'

    assert one('SELECT COUNT(*) FROM caption_sightings WHERE captured_at IS NULL') == 0, \
        'sighting without captured_at'
    drift = one('SELECT COUNT(*) FROM caption_sightings s JOIN builds b '
                'ON b.build_id=s.source_build WHERE s.captured_at != b.captured_at')
    assert drift == 0, f'{drift} sightings have a captured_at that differs from builds'
    meta = dict(conn.execute("SELECT key, value FROM meta WHERE key='caption_sightings'"))
    assert meta.get('caption_sightings') == str(one('SELECT COUNT(*) FROM caption_sightings')), \
        'meta caption_sightings is stale'


def character_tiers():
    """Caption-only speakers are labelled, and rows carry their tier."""
    cap = api.character('Lord Shaxx', all_lines=True, limit=2)
    assert cap and '(caption lines)' in cap['header'], cap and cap['header']
    assert all(r.get('source_tier') == 'game_caption' for r in cap['rows']), \
        'caption rows are not labelled game_caption'
    mixed = api.character('Calus', all_lines=True, limit=500)
    assert mixed and 'caption' in mixed['header'], mixed and mixed['header']
    assert any(r.get('source_tier') == 'game_caption' for r in mixed['rows']), \
        'mixed page did not include caption rows'


def no_duplicate_text():
    """A caption line never repeats text that canon already holds."""
    shared = one(
        'SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id '
        f"WHERE {CAP} AND EXISTS (SELECT 1 FROM transcript_lines o "
        'JOIN transcripts ot ON ot.id=o.transcript_id '
        "WHERE o.norm_line=tl.norm_line AND ot.source_tier!='game_caption')")
    assert shared == 0, f'{shared} caption lines duplicate existing canon text'
    internal = one(
        'SELECT COUNT(*) FROM (SELECT tl.norm_line FROM transcript_lines tl '
        'JOIN transcripts t ON t.id=tl.transcript_id '
        f"WHERE {CAP} GROUP BY tl.norm_line HAVING COUNT(*) > 1)")
    assert internal == 0, f'{internal} caption texts appear more than once'


def facets():
    """Activity facets are curated, and their vocabulary resolves."""
    bad = one(
        'SELECT COUNT(*) FROM transcript_classification c '
        'JOIN transcripts t ON t.id=c.transcript_id '
        f"WHERE {CAP} AND c.activity_slug IS NOT NULL AND c.confidence != 'derived'")
    assert bad == 0, f'{bad} caption facets not marked derived'
    unknown_ok = one(
        'SELECT COUNT(*) FROM transcript_classification c '
        'JOIN transcripts t ON t.id=c.transcript_id '
        f"WHERE {CAP} AND c.activity_slug IS NULL AND c.confidence != 'unknown'")
    assert unknown_ok == 0, 'caption rows without a facet must be unknown, never guessed'
    refs = one(
        'SELECT COUNT(*) FROM transcript_classification c '
        'JOIN transcripts t ON t.id=c.transcript_id '
        f"WHERE {CAP} AND c.activity_slug IS NOT NULL "
        'AND NOT EXISTS (SELECT 1 FROM activities a WHERE a.slug=c.activity_slug)')
    assert refs == 0, f'{refs} caption facets point at unknown activities'
    # Every facet key the extraction emits must resolve to a taxonomy slug:
    # a vocabulary drift would otherwise silently downgrade facets to unknown.
    if os.path.exists(JSONL):
        keys = {json.loads(line).get('activity')
                for line in open(JSONL, encoding='utf-8')}
        keys.discard(None)
        slugs = {r[0] for r in conn.execute('SELECT slug FROM activities')}
        unresolved = {k for k in keys
                      if taxonomy.CAPTION_ACTIVITY_SLUGS.get(k) not in slugs}
        assert not unresolved, f'unresolved caption activity keys: {sorted(unresolved)}'


def indexes():
    """FTS and the verification index mirror the caption lines one for one."""
    lines = one(f'SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t '
                f'ON t.id=tl.transcript_id WHERE {CAP}')
    fts = one("SELECT COUNT(*) FROM fts WHERE source='caption'")
    assert fts == lines, f'fts caption rows {fts} != caption lines {lines}'
    ver = one("SELECT COUNT(*) FROM verify_fts WHERE source='caption'")
    assert ver == lines, f'verify caption rows {ver} != caption lines {lines}'
    assert one("SELECT COUNT(*) FROM fts WHERE lang IS NULL OR lang=''") == 0, \
        'fts rows without a language'
    assert one("SELECT COUNT(*) FROM fts WHERE source='caption' AND lang!='en'") == 0, \
        'caption rows with a non-English language'


def speakers():
    """Caption speakers are canonical names, not extraction aliases."""
    alias_keys = [r[0] for r in conn.execute('SELECT alias FROM speaker_aliases')]
    if not alias_keys:
        return
    marks = ','.join('?' * len(alias_keys))
    leaked = conn.execute(
        'SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t '
        f'ON t.id=tl.transcript_id WHERE {CAP} AND tl.speaker IN ({marks})',
        alias_keys).fetchone()[0]
    assert leaked == 0, f'{leaked} caption lines use an uncanonicalised speaker'


def stage_dirs():
    """Scoreboard/stat captions stay demoted as stage directions."""
    stats = one(f'SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t '
                f'ON t.id=tl.transcript_id WHERE {CAP} AND tl.is_stage_dir=1')
    assert stats > 0, 'no demoted stat lines found'
    wrong = one(f'SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t '
                f'ON t.id=tl.transcript_id WHERE {CAP} AND tl.is_stage_dir=1 '
                "AND tl.speaker != 'Narration'")
    assert wrong == 0, f'{wrong} stage-directed caption lines with a speaker'
    narrated = one(f"SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t "
                   f"ON t.id=tl.transcript_id WHERE {CAP} AND tl.speaker='Narration' "
                   'AND tl.is_stage_dir=0')
    assert narrated == 0, f'{narrated} Narration caption lines not demoted'


def api_surface():
    """--type captions, --lang and the activity facet all reach caption rows."""
    rows = api.search('primeval', type='captions', limit=25, full=True)
    assert rows, 'caption search returned nothing'
    assert all(r['source'] == 'caption' for r in rows), 'non-caption row from --type captions'
    assert api.search_total('primeval', type='captions') >= len(rows)
    assert api.search('primeval', type='captions', lang='ja') == [], 'unexpected ja rows'
    assert api.search('primeval', type='captions', lang='en'), 'lang=en filtered everything out'
    gambit = api.search('bank', activity='gambit', limit=25, full=True)
    assert gambit, 'activity facet returned nothing'
    assert any(r['source'] == 'caption' for r in gambit), \
        'caption rows unreachable through the activity facet'


def persona_canon_excludes_captions():
    """persona.json counts stay authoritative: captions are excluded."""
    rows = conn.execute(
        "SELECT speaker, COUNT(*) FROM fts WHERE source='caption' AND speaker='Drifter' "
        'GROUP BY 1').fetchone()
    assert rows, 'expected Drifter caption lines'
    persona = os.path.join(os.path.dirname(ROOT), 'destiny-agent-drifter', 'persona.json')
    if not os.path.exists(persona):
        return                      # grimoire-only checkout: nothing to compare
    expected = json.load(open(persona, encoding='utf-8'))['canon_lines']
    info = api.character_info('Drifter')
    assert info and info['spoken_lines'] == expected, \
        f"spoken_lines {info and info['spoken_lines']} != persona canon {expected}"
    assert info['spoken_lines'] < expected + rows[1], \
        'spoken_lines appears to include caption lines'


print('=== CAPTION TEST ===')
for name, fn in [
    ('caption headers are tagged, English and classified', headers),
    ('caption lines keep provenance', provenance),
    ('caption builds are registered and traceable', build_scope),
    ('caption sightings retain merged builds', sightings),
    ('character lines name their caption tier', character_tiers),
    ('no caption text duplicates canon', no_duplicate_text),
    ('activity facets are curated and resolve', facets),
    ('caption rows indexed exactly once', indexes),
    ('caption speakers are canonical', speakers),
    ('stat captions stay demoted', stage_dirs),
    ('search reaches captions by type, lang and activity', api_surface),
    ('persona canon excludes captions', persona_canon_excludes_captions),
]:
    check(name, fn)

conn.close()
print(f'\nPassed: {PASS} | Failed: {FAIL}')
sys.exit(1 if FAIL else 0)
