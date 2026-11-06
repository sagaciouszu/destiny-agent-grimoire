#!/usr/bin/env python3
"""Game-caption test: the extracted subtitle corpus is canonical and clean.

Captions (source_tier='game_caption') are English text pulled from the local
build. This guards the invariants that make them safe to search:

  - headers carry the tier, language and a taxonomy row;
  - every caption line keeps StringReference provenance;
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
import taxonomy  # noqa: E402

DB = os.environ.get('GRIMOIRE_DB') or os.path.join(ROOT, 'db', 'grimoire.db')
JSONL = os.path.join(ROOT, 'archive', 'data', 'captions.jsonl')
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
    persona = os.path.join(os.path.dirname(ROOT), 'how-to-drift-for-agents', 'persona.json')
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
