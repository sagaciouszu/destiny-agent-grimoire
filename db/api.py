#!/usr/bin/env python3
"""Importable query layer for the Destiny Grimoire database.

Both the CLI (`db/query.py`) and the MCP server (`mcp-server/server.py`) call
these functions. Read-only: connections use SQLite URI mode=ro.

Environment:
  GRIMOIRE_DB  override the database path (default: db/grimoire.db)
"""
import functools
import os
import re
import sqlite3
import unicodedata
from pathlib import Path

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grimoire.db')
TYPE_TO_SOURCE = {
    'books': 'book_entry', 'transcripts': 'transcript_line', 'grimoire': 'grimoire_card',
    'interactions': 'interaction', 'items': 'item', 'records': 'record',
    'lore': 'lore_entry', 'captions': 'caption',
}
MAX_LIMIT = 10000  # safety bound for the shared API; MCP clamps tighter


def db_path():
    return os.environ.get('GRIMOIRE_DB') or DEFAULT_DB


_CONTROL = re.compile(
    r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u00ad\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]')


def clean_input(value, limit):
    """Reject non-text, strip control characters and collapse whitespace."""
    if not isinstance(value, str):
        raise ValueError('input must be text')
    value = _CONTROL.sub(' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    if not value:
        raise ValueError('input must not be empty')
    if len(value) > limit:
        raise ValueError(f'input must be 1-{limit} characters')
    return value


def literal_fts(term):
    """Turn arbitrary user text into a safe FTS5 query of quoted terms."""
    tokens = [t for t in term.split() if re.search(r'[0-9A-Za-z\u00a1-\uffff]', t)]
    if not tokens:
        raise ValueError('query must contain at least one searchable word')
    return ' AND '.join('"' + t.replace('"', '""') + '"' for t in tokens)


def fts_query(conn, term):
    """Use the term as FTS syntax when valid, otherwise treat it literally."""
    try:
        conn.execute('SELECT 1 FROM fts WHERE fts MATCH ? LIMIT 1', (term,)).fetchone()
        return term
    except sqlite3.OperationalError:
        pass
    safe = literal_fts(term)
    conn.execute('SELECT 1 FROM fts WHERE fts MATCH ? LIMIT 1', (safe,)).fetchone()
    return safe


def _speaker_matches(want, speaker):
    """Attribution match on name boundaries: 'Eris' and 'The Drifter' pass,
    'ris' and 'Morn' do not."""
    def canon(value):
        value = ' '.join((value or '').split()).casefold()
        return value[4:] if value.startswith('the ') else value
    want, speaker = canon(want), canon(speaker)
    if not want or not speaker:
        return False
    return speaker == want or speaker.startswith(want + ' ')


def norm(s):
    s = s.lower().replace('\u2026', '...').replace('\u2019', "'").replace('\u2014', '-').replace('\u2013', '-')
    n = re.sub(r'[^a-z0-9 ]+', ' ', s)
    n = re.sub(r'\s+', ' ', n).strip()
    if n:
        return n
    # Punctuation-only canon lines stay verifiable: keep the lowered text
    # (minus LIKE wildcards) so verify(':)') can match its canonical row.
    return re.sub(r'\s+', ' ', s.replace('%', ' ').replace('_', ' ')).strip()


_ROMAN = {'ii': 2, 'iii': 3, 'iv': 4, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9,
          'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13, 'xiv': 14, 'xv': 15}

# Apostrophe/prime codepoints are deleted outright (possessive rule), everything
# else outside [0-9a-z] becomes a space after the NFKD fold.
_APOSTROPHES = "'’‘′`"
_ALL_DASHES = '-–—/'


def fold_name(s):
    """Fold a name to the entity-web lookup key.

    NFKD decompose, strip combining marks, casefold, delete apostrophes,
    hyphens/dashes/slashes become spaces, remaining punctuation becomes a
    space, single spaces, roman numerals fold to arabic (key generation only).
    """
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', str(s))
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    s = s.casefold()
    for ch in _APOSTROPHES:
        s = s.replace(ch, '')
    for ch in _ALL_DASHES:
        s = s.replace(ch, ' ')
    s = re.sub(r'[^0-9a-z ]+', ' ', s)
    tokens = [str(_ROMAN[t]) if t in _ROMAN else t for t in s.split()]
    return ' '.join(tokens)


def _fold_key(s):
    """norm_key for entity canonicals: fold_name plus leading 'the' strip."""
    key = fold_name(s)
    return key[4:] if key.startswith('the ') else key


def _query_keys(base):
    """Lookup keys for a folded query (order stable, deduplicated)."""
    keys = [base]
    if base.endswith(' s') and len(base) > 2:
        keys.append(base[:-2].rstrip())
    if base.startswith('the '):
        keys.append(base[4:])
    if base and not base.startswith('the '):
        keys.append('the ' + base)
    seen, out = set(), []
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _skeleton(s):
    """Consonant skeleton used only by the phonetic (fuzzy) fallback."""
    s = fold_name(s)
    for a, b in [('ph', 'f'), ('ck', 'k'), ('qu', 'k'), ('x', 'ks'),
                 ('th', 't'), ('sh', 's'), ('ch', 'c'), ('z', 's'),
                 ('c', 'k'), ('q', 'k')]:
        s = s.replace(a, b)
    s = re.sub(r'[^a-z]', '', s)
    return re.sub(r'[aeiouy]', '', s)


def _edit_distance(a, b, cap=3):
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + (ca != cb))
        prev = cur
    return prev[-1]


_ENTITY_KINDS = ('char', 'power', 'faction', 'place')


@functools.lru_cache(maxsize=512)
def _entity_resolve_cached(base, kind, limit, include_unreviewed):
    keys = _query_keys(base)
    conn = connect()
    try:
        placeholders = ','.join('?' * len(keys))
        where = f'a.norm_alias IN ({placeholders})'
        params = list(keys)
        if kind:
            where += ' AND e.kind = ?'
            params.append(kind)
        if not include_unreviewed:
            where += ' AND a.reviewed = 1'
        considered = conn.execute(
            f'SELECT COUNT(DISTINCT e.id) FROM entity_aliases a JOIN entities e ON e.id = a.entity_id WHERE {where}',
            params).fetchone()[0]
        order = (" ORDER BY a.weight DESC, CASE a.confidence WHEN 'high' THEN 3 "
                 "WHEN 'medium' THEN 2 ELSE 1 END DESC, e.id ASC")
        rows = conn.execute(
            'SELECT e.id AS entity_id, e.canonical, e.kind, e.confidence AS entity_confidence, '
            'a.alias, a.norm_alias, a.confidence AS alias_confidence, a.requires_ctx, a.weight '
            f'FROM entity_aliases a JOIN entities e ON e.id = a.entity_id WHERE {where}{order}',
            params).fetchall()
        # one row per entity: the best (first, per ORDER BY) matching alias wins
        seen, results = set(), []
        for r in rows:
            if r['entity_id'] in seen:
                continue
            seen.add(r['entity_id'])
            matched = ('canonical' if r['norm_alias'] == _fold_key(r['canonical']) or
                       r['norm_alias'] == fold_name(r['canonical']) else 'alias')
            results.append({
                'entity_id': r['entity_id'], 'canonical': r['canonical'], 'kind': r['kind'],
                'alias': r['alias'], 'matched': matched, 'fuzzy': False,
                'confidence': r['alias_confidence'], 'requires_ctx': bool(r['requires_ctx']),
                'score': round(min(1.0, r['weight'] / 3.0), 3),
            })
            if len(results) >= limit:
                break
        fuzzy = False
        if considered == 0:
            fuzzy = True
            sql = ('SELECT e.id AS entity_id, e.canonical, e.kind, a.alias, a.confidence AS alias_confidence, '
                   'a.norm_alias FROM entity_aliases a JOIN entities e ON e.id = a.entity_id '
                   'WHERE a.reviewed = 1')
            params = []
            if kind:
                sql += ' AND e.kind = ?'
                params.append(kind)
            skel = _skeleton(base)
            cand = []
            for r in conn.execute(sql, params):
                dist = _edit_distance(skel, _skeleton(r['norm_alias']), cap=2)
                if dist <= 2:
                    cand.append((dist, r))
            cand.sort(key=lambda item: (item[0], item[1]['entity_id']))
            seen, results = set(), []
            for dist, r in cand:
                if r['entity_id'] in seen:
                    continue
                seen.add(r['entity_id'])
                results.append({
                    'entity_id': r['entity_id'], 'canonical': r['canonical'], 'kind': r['kind'],
                    'alias': r['alias'], 'matched': 'fuzzy', 'fuzzy': True,
                    'confidence': r['alias_confidence'], 'requires_ctx': False,
                    'score': round(max(0.05, 0.5 - 0.25 * dist), 3),
                })
                if len(results) >= 3:
                    break
            considered = len(seen)
        return {'results': results, 'fuzzy': fuzzy, 'candidates_considered': considered}
    finally:
        conn.close()


def entity_resolve(query, kind=None, limit=5, include_unreviewed=False):
    """Resolve a name to entity candidate(s).

    Exact folded match first (alias key or canonical key), then a phonetic
    fallback that is always flagged `fuzzy: true` with `score <= 0.5`. Never
    silently picks: callers get a ranked list. `include_unreviewed` gates
    reviewed=0 rows (strict by default).
    """
    query = clean_input(query, 200)
    if kind is not None and kind not in _ENTITY_KINDS:
        raise ValueError(f'kind must be one of: {", ".join(_ENTITY_KINDS)}')
    limit = _limit(limit, 5)
    base = fold_name(query)
    res = _entity_resolve_cached(base, kind, limit, bool(include_unreviewed))
    return {'query': query, 'normalized': base, **res}


def entity_index():
    """Curated entity list for the grimoire://entities resource."""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT e.canonical, e.kind, e.confidence, "
            "(SELECT COUNT(*) FROM entity_aliases a WHERE a.entity_id = e.id) AS aliases, "
            "(SELECT COUNT(*) FROM entity_links l WHERE l.entity_id = e.id) AS documents "
            'FROM entities e ORDER BY e.kind, e.canonical').fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def entity(ref, limit=10, kind=None, include_unreviewed=False):
    """Entity detail: aliases, relations, document counts and top documents.

    Exact (non-fuzzy) match required for the detail block; fuzzy candidates
    are returned separately so callers never mistake a suggestion for a hit.
    """
    res = entity_resolve(ref, kind=kind, limit=limit, include_unreviewed=include_unreviewed)
    top = res['results'][0] if res['results'] and not res['results'][0]['fuzzy'] else None
    out = {**res, 'entity': None, 'aliases': [], 'relations': [],
           'counts': {}, 'documents': [], 'total_documents': 0}
    if top is None:
        return out
    eid = top['entity_id']
    conn = connect()
    try:
        row = conn.execute(
            'SELECT id, canonical, norm_key, kind, confidence, reviewed, source, first_seen '
            'FROM entities WHERE id = ?', (eid,)).fetchone()
        out['entity'] = dict(row)
        out['aliases'] = [dict(r) for r in conn.execute(
            'SELECT alias, norm_alias, confidence, requires_ctx, reviewed, weight '
            'FROM entity_aliases WHERE entity_id = ? ORDER BY weight DESC, alias', (eid,))]
        counts = dict(conn.execute(
            'SELECT kind, COUNT(*) FROM entity_links WHERE entity_id = ? GROUP BY kind',
            (eid,)).fetchall())
        out['counts'] = counts
        out['total_documents'] = sum(counts.values())
        out['documents'] = [dict(r) for r in conn.execute(
            'SELECT kind, ref, weight, match FROM entity_links '
            'WHERE entity_id = ? ORDER BY weight DESC, ref LIMIT ?', (eid, _limit(limit, 10)))]
        out['relations'] = [{'direction': 'out', 'relation': r['relation'],
                             'target': r['canonical'], 'target_kind': r['kind']}
                            for r in conn.execute(
            'SELECT r.relation, t.canonical, t.kind FROM entity_relations r '
            'JOIN entities t ON t.id = r.target_entity_id WHERE r.entity_id = ? '
            'ORDER BY r.relation, t.canonical', (eid,))]
        out['relations'] += [{'direction': 'in', 'relation': r['relation'],
                              'source': r['canonical'], 'source_kind': r['kind']}
                             for r in conn.execute(
            'SELECT r.relation, t.canonical, t.kind FROM entity_relations r '
            'JOIN entities t ON t.id = r.entity_id WHERE r.target_entity_id = ? '
            'ORDER BY r.relation, t.canonical', (eid,))]
        return out
    finally:
        conn.close()


def connect():
    path = db_path()
    if not os.path.exists(path):
        raise FileNotFoundError(
            f'database not found at {path} - bootstrap: ./setup.sh, or python3 db/migrate.py')
    conn = sqlite3.connect(f'{Path(path).as_uri()}?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('SELECT COUNT(*) FROM sqlite_master').fetchone()
    except sqlite3.DatabaseError as e:
        conn.close()
        raise ValueError(f'database unreadable at {path}: {e}') from e
    return conn


def _offset(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(value, MAX_LIMIT))


def _snippet(text, limit=400):
    text = " ".join((text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:-") + "..."


def _resolve(conn, table, ref, cols):
    row = conn.execute(
        f"SELECT {cols} FROM {table} WHERE slug = ? LIMIT 1", (ref,)).fetchone()
    if row:
        return row
    return conn.execute(
        f"SELECT {cols} FROM {table} WHERE title LIKE ? ESCAPE '\\' ORDER BY title LIMIT 1",
        (f"%{_like(ref.replace('-', ' '))}%",)).fetchone()


def _like(value):
    """Escape LIKE wildcards so user input matches literally, not by pattern."""
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def _resolve_character(conn, name):
    for candidate in _speaker_variants(name):
        slug = candidate.lower().replace(' ', '-')
        row = conn.execute(
            'SELECT id, name, slug FROM characters WHERE LOWER(name)=LOWER(?) OR LOWER(slug)=LOWER(?)',
            (candidate, slug)).fetchone()
        if row:
            return row
        row = conn.execute(
            "SELECT id, name, slug FROM characters WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
            "OR LOWER(slug) LIKE LOWER(?) ESCAPE '\\' "
            'ORDER BY LENGTH(name) LIMIT 1', (f'{_like(candidate)}%', f'{_like(slug)}%')).fetchone()
        if row:
            return row
        row = conn.execute(
            "SELECT id, name, slug FROM characters WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
            "OR LOWER(slug) LIKE LOWER(?) ESCAPE '\\' "
            'ORDER BY LENGTH(name) LIMIT 1', (f'%{_like(candidate)}%', f'%{_like(slug)}%')).fetchone()
        if row:
            return row
    return None

def _guard(fn):
    """Translate SQLite failures into clean ValueErrors for CLI and MCP."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except sqlite3.DatabaseError as e:
            raise ValueError(f'database error: {e}') from e
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


def _limit(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, MAX_LIMIT))


@_guard
def _entity_fts_filter(conn, entity_name):
    """Map an entity name to an FTS (source, source_slug) filter.

    Returns (clause, params) or None when the entity resolves but links to
    nothing the FTS indexes (e.g. seals only). Raises ValueError when the name
    resolves to no reviewed entity.
    """
    res = entity_resolve(entity_name)
    if not res['results'] or res['results'][0]['fuzzy']:
        raise ValueError(f'entity not found: {entity_name} (try `entity <name>`)')
    eid = res['results'][0]['entity_id']
    rows = conn.execute('SELECT kind, ref FROM entity_links WHERE entity_id = ?', (eid,)).fetchall()
    by_source = {}
    book_entry_ids = []
    for kind, ref in rows:
        if kind == 'transcript':
            by_source.setdefault('transcript_line', set()).add(ref)
        elif kind == 'book':
            by_source.setdefault('book_entry', set()).add(ref)
        elif kind == 'book_entry':
            book_entry_ids.append(int(ref.split(':', 1)[1]))
        elif kind == 'lore_entry':
            by_source.setdefault('lore_entry', set()).add('lore-' + ref.split(':', 1)[1])
        elif kind == 'item':
            by_source.setdefault('item', set()).add(ref)
        elif kind == 'record':
            by_source.setdefault('record', set()).add(ref)
        # seals are not indexed in the FTS surface; they add no rows here
    for i in range(0, len(book_entry_ids), 500):
        chunk = book_entry_ids[i:i + 500]
        q = ('SELECT DISTINCT books.slug FROM book_entries '
             'JOIN books ON books.id = book_entries.book_id '
             f"WHERE book_entries.id IN ({','.join('?' * len(chunk))})")
        for (slug,) in conn.execute(q, chunk):
            by_source.setdefault('book_entry', set()).add(slug)
    clauses, params = [], []
    for source, slugs in sorted(by_source.items()):
        slugs = sorted(slugs)
        if not slugs:
            continue
        clauses.append(f"(source = ? AND source_slug IN ({','.join('?' * len(slugs))}))")
        params.append(source)
        params.extend(slugs)
    if not clauses:
        return None
    return ' AND (' + ' OR '.join(clauses) + ')', params


def search(term, type=None, limit=10, full=False, offset=0, rank=True,
           activity=None, season=None, event=None, expansion=None, class_tag=None,
           exclude_stage=False, timeline=None, lang=None, entity=None):
    """Full-text search. Returns rows with a snippet unless full=True.

    The term is used as FTS5 syntax when valid; otherwise every word is quoted
    and ANDed, so punctuation (`"`, `(`, `+`, `%`, `:`, `-`) never breaks a query.

    Ranked results demote stage directions (speaker Narration) and unattributed
    cutscene captions (speaker Cutscene); set exclude_stage=True to drop them.
    Game-caption rows (source='caption') carry a -1.0 boost so extracted in-game
    text competes with the curated corpus; stage-direction penalties still apply
    on top, so stat/scoreboard captions stay demoted (net +1.0).

    timeline filters rows to one in-universe story chapter slug (see
    timeline_chapters / capabilities.json), for example 'the_dark_age'.
    lang filters to one document language (fts.lang is UNINDEXED, so this never
    affects bm25); the only populated value today is 'en' — future caption
    languages arrive as data, not a schema change.
    entity restricts rows to documents the named entity is linked to in the
    entity web (e.g. entity='Savathûn'); raise ValueError when the name does
    not resolve to a reviewed entity.
    """
    term = clean_input(term, 500)
    if type is not None and type not in TYPE_TO_SOURCE:
        raise ValueError(f'type must be one of: {", ".join(TYPE_TO_SOURCE)}')
    conn = connect()
    try:
        entity_clause = entity_params = None
        if entity:
            entity_clause, entity_params = _entity_fts_filter(conn, entity)
            if entity_clause is None:
                return []
        term = fts_query(conn, term)
        where = 'fts MATCH ?'
        params = [term]
        if type:
            where += ' AND source = ?'
            params.append(TYPE_TO_SOURCE[type])
        if lang:
            where += ' AND lang = ?'
            params.append(str(lang))
        facet, facet_params = _taxonomy_filter(conn, activity, season, event, expansion)
        if facet:
            where += ' AND ' + facet
            params.extend(facet_params)
        cfilter, cparams = _class_filter(class_tag)
        where += cfilter
        params.extend(cparams)
        if exclude_stage:
            where += " AND speaker NOT IN ('Narration', 'Cutscene')"
        if timeline:
            where += ' AND timeline = ?'
            params.append(str(timeline))
        if entity_clause is not None:
            where += entity_clause
            params.extend(entity_params)
        params.append(_limit(limit, 10))
        params.append(_offset(offset))
        order = (" ORDER BY bm25(fts, 3.0, 1.0, 1.0, 1.0, 0.0)"
                 " + CASE WHEN source='item' THEN 1.0 ELSE 0 END"
                 " + CASE WHEN source='caption' THEN -1.0 ELSE 0 END"
                 " + CASE WHEN speaker='Narration' THEN 2.0"
                 " WHEN speaker='Cutscene' THEN 1.0 ELSE 0 END") if rank else ''
        try:
            if full:
                rows = conn.execute(
                    f'SELECT title, speaker, text, source, source_slug, timeline FROM fts WHERE {where}{order} LIMIT ? OFFSET ?', params).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT title, speaker, source, source_slug, timeline, snippet(fts, 1, '[', ']', '…', 25) AS snippet "
                    f'FROM fts WHERE {where}{order} LIMIT ? OFFSET ?', params).fetchall()
        except sqlite3.OperationalError as e:
            raise ValueError(f'invalid search query: {e}') from e
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _speaker_variants(name):
    value = (name or '').strip()
    variants = [value]
    if value.lower().startswith('the '):
        variants.append(value[4:])
    return [v for v in variants if v]


def _tier_label(rows):
    """Name the provenance tier of a page of transcript rows."""
    tiers = {r.get('source_tier') for r in rows}
    if tiers == {'game_caption'}:
        return 'caption lines'
    if 'game_caption' in tiers:
        return 'transcript + caption lines'
    return 'transcript lines'


def _tier_values(value):
    """Normalise a tier filter: list, tuple or comma-separated string."""
    if not value:
        return []
    if isinstance(value, str):
        value = value.split(',')
    out = []
    for item in value:
        for part in str(item).split(','):
            name = part.strip()
            if name and name not in out:
                out.append(name)
    return out


def _tier_sql(tiers=None, exclude_tiers=None, alias='t'):
    """SQL fragment and params for an include/exclude tier filter."""
    clauses, params = [], []
    include = _tier_values(tiers)
    exclude = _tier_values(exclude_tiers)
    if include:
        clauses.append(f"{alias}.source_tier IN ({','.join('?' * len(include))})")
        params.extend(include)
    if exclude:
        clauses.append(f"COALESCE({alias}.source_tier, '') NOT IN "
                       f"({','.join('?' * len(exclude))})")
        params.extend(exclude)
    return clauses, params


def _transcript_lines(conn, name, pattern, limit, offset, canon_only=False,
                      class_tag=None, tiers=None, exclude_tiers=None):
    for variant in _speaker_variants(name):
        params = [f'%{_like(variant)}%']
        sql = ("SELECT line AS text, speaker, '' AS source_slug, t.timeline, "
               "t.source_tier AS source_tier "
               "FROM transcript_lines JOIN transcripts t ON t.id = transcript_lines.transcript_id "
               "WHERE speaker LIKE ? ESCAPE '\\' AND is_stage_dir=0")
        if canon_only:
            sql += ' AND is_optional=0'
        if class_tag:
            sql += " AND (class_tag IS NULL OR class_tag='' OR class_tag=?)"
            params.append(str(class_tag).lower())
        tier_clauses, tier_params = _tier_sql(tiers, exclude_tiers)
        for clause in tier_clauses:
            sql += ' AND ' + clause
        params.extend(tier_params)
        if pattern:
            sql += " AND LOWER(line) LIKE ? ESCAPE '\\'"
            params.append(pattern)
        sql += ' LIMIT ? OFFSET ?'
        params.append(_limit(limit, 20))
        params.append(_offset(offset))
        rows = conn.execute(sql, params).fetchall()
        if rows:
            return [dict(r) for r in rows]
    return []


@_guard
def character(name, about=None, all_lines=False, limit=20, offset=0, canon_only=False,
              class_tag=None, tiers=None, exclude_tiers=None):
    """Curated character quotes, or transcript lines for any canon speaker.

    Curated characters use the compendium. Speakers who exist only in
    transcripts fall back to their canonical lines. A tier filter always uses
    transcript rows, because curated compendium rows carry no source tier.
    """
    conn = connect()
    try:
        pattern = f'%{_like(about.lower())}%' if about else None
        if all_lines:
            params = [f'%{_like(name)}%']
            sql = ("SELECT line AS text, speaker, '' AS source_slug, t.timeline, "
                   "t.source_tier AS source_tier "
                   "FROM transcript_lines JOIN transcripts t ON t.id = transcript_lines.transcript_id "
                   "WHERE speaker LIKE ? ESCAPE '\\' AND is_stage_dir=0")
            if canon_only:
                sql += ' AND is_optional=0'
            if class_tag:
                sql += " AND (class_tag IS NULL OR class_tag='' OR class_tag=?)"
                params.append(str(class_tag).lower())
            tier_clauses, tier_params = _tier_sql(tiers, exclude_tiers)
            for clause in tier_clauses:
                sql += ' AND ' + clause
            params.extend(tier_params)
            if pattern:
                sql += " AND LOWER(line) LIKE ? ESCAPE '\\'"
                params.append(pattern)
            sql += ' LIMIT ? OFFSET ?'
            params.append(_limit(limit, 20))
            params.append(_offset(offset))
            rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
            return {'header': f'=== {name} ({_tier_label(rows)}) ===', 'rows': rows}

        ch = _resolve_character(conn, name)
        if not ch or _tier_values(tiers) or _tier_values(exclude_tiers):
            rows = _transcript_lines(conn, name, pattern, limit, offset, canon_only=canon_only,
                                     class_tag=class_tag, tiers=tiers,
                                     exclude_tiers=exclude_tiers)
            if not rows:
                return None
            return {'header': f'=== {name} ({_tier_label(rows)}) ===', 'rows': rows}
        params = [ch['id']]
        sql = "SELECT text, '' AS speaker, source_slug, timeline FROM character_lines WHERE character_id = ?"
        if pattern:
            sql += " AND LOWER(text) LIKE ? ESCAPE '\\'"
            params.append(pattern)
        sql += ' LIMIT ? OFFSET ?'
        params.append(_limit(limit, 20))
        params.append(_offset(offset))
        rows = conn.execute(sql, params).fetchall()
        return {'header': f"=== {ch['name']} ({ch['slug']}) ===", 'rows': [dict(r) for r in rows]}
    finally:
        conn.close()


def _lore_links(conn, titles, limit=8):
    """Linked manifest lore titles for a set of item titles (best-sorted, capped)."""
    if not titles:
        return {}
    qmarks = ','.join('?' * len(titles))
    links = {}
    for r in conn.execute(
            'SELECT lei.item_title, le.title FROM lore_entry_items lei '
            'JOIN lore_entries le ON le.hash = lei.lore_hash '
            f'WHERE lei.item_title IN ({qmarks}) ORDER BY le.title', list(titles)):
        bucket = links.setdefault(r[0], [])
        if len(bucket) < limit:
            bucket.append(r[1])
    return links


def _enrich_item_rows(conn, rows, text_limit=200, lore_limit=8):
    """Attach flavor-text snippets and lore links so find_item() is one call."""
    out = [dict(r) for r in rows]
    if not out:
        return out
    slugs = [r['slug'] for r in out]
    qmarks = ','.join('?' * len(slugs))
    rows_by_slug = {r['slug']: r for r in conn.execute(
        f'SELECT slug, text, timeline FROM items WHERE slug IN ({qmarks})', slugs)}
    links = _lore_links(conn, sorted({r['title'] for r in out if r['title']}), lore_limit)
    for r in out:
        src = rows_by_slug.get(r['slug'])
        r['text'] = _snippet((src['text'] if src else '') or '', text_limit)
        r['timeline'] = src['timeline'] if src else None
        r['lore'] = links.get(r['title'], [])
    return out


@_guard
def item(slug):
    """Item details by slug: title, flavor text, provenance and linked lore.

    Returns a bounded dict without internal fields (no row id, no normalized
    text); use find_item() to search by name first.
    """
    conn = connect()
    try:
        row = conn.execute(
            'SELECT slug, title, text, release, item_type, source_url, timeline, timeline_basis '
            'FROM items WHERE slug = ?', (slug,)).fetchone()
        if not row:
            return None
        out = dict(row)
        out['text'] = _snippet(out['text'] or '', 2000)
        out['lore'] = _lore_links(
            conn, [out['title']] if out['title'] else []).get(out['title'] or '', [])
        return out
    finally:
        conn.close()


def _verify_exact(conn, nq):
    """Tokenizer-edge rows (punctuation-only norms) that FTS phrases can't match."""
    rows = conn.execute(
        'SELECT norm, source, slug, speaker FROM verify_fts WHERE norm = ? LIMIT 50',
        (nq,)).fetchall()
    return [{'source': r[1], 'slug': r[2], 'speaker': r[3], 'norm': r[0]} for r in rows]


def _verify_index(conn, nq):
    """Phrase lookup over the verification index; miss falls back to a scan."""
    phrase = '"' + nq.replace('"', '""') + '"'
    try:
        rows = conn.execute(
            'SELECT norm, source, slug, speaker FROM verify_fts '
            'WHERE verify_fts MATCH ? LIMIT 500', (phrase,)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [{'source': r[1], 'slug': r[2], 'speaker': r[3], 'norm': r[0]}
            for r in rows if nq in (r[0] or '')]


@_guard
def verify(quote, speaker=None, exact=False):
    """Check a quoted string against canon.

    Uses the verification index (normalized phrase lookup). Punctuation-only
    quotes fall back to an exact normalized-row match, which the FTS phrase
    tokenizer cannot express.

    speaker: only accept matches attributed to this speaker (drops sources with
             no speaker, such as books and items).
    exact:   require the normalized quote to equal a full canonical row, not a
             substring of one.

    Returns {'quote', 'verified', 'speaker', 'exact', 'matches'}.
    """
    if not quote or len(quote) > 2000:
        raise ValueError('quote must be 1-2000 characters')
    quote = clean_input(quote, 2000)
    nq = norm(quote)
    if not nq:
        return {'quote': quote, 'verified': False, 'speaker': speaker,
                'exact': exact, 'matches': []}
    conn = connect()
    try:
        hits = _verify_index(conn, nq)
        if not hits and not re.search(r'[a-z0-9]', nq):
            hits = _verify_exact(conn, nq)
    finally:
        conn.close()

    if exact:
        hits = [h for h in hits if h['norm'] == nq]
    if speaker:
        hits = [h for h in hits if h['speaker'] and _speaker_matches(speaker, h['speaker'])]

    seen, uniq = set(), []
    for h in hits:
        key = (h['source'], h['slug'], h['speaker'])
        if key in seen:
            continue
        seen.add(key)
        uniq.append({'source': h['source'], 'slug': h['slug'], 'speaker': h['speaker'],
                     'exact': h['norm'] == nq})
    return {'quote': quote, 'verified': bool(uniq), 'speaker': speaker,
            'exact': exact, 'matches': uniq}


@_guard
def search_total(term, type=None, activity=None, season=None, event=None, expansion=None,
                 class_tag=None, exclude_stage=False, timeline=None, lang=None, entity=None):
    """Total FTS matches for a query (for paging). Mirrors search() filters."""
    term = clean_input(term, 500)
    if type is not None and type not in TYPE_TO_SOURCE:
        raise ValueError(f'type must be one of: {", ".join(TYPE_TO_SOURCE)}')
    conn = connect()
    try:
        entity_clause = entity_params = None
        if entity:
            entity_clause, entity_params = _entity_fts_filter(conn, entity)
            if entity_clause is None:
                return 0
        term = fts_query(conn, term)
        where = 'fts MATCH ?'
        params = [term]
        if type:
            where += ' AND source = ?'
            params.append(TYPE_TO_SOURCE[type])
        if lang:
            where += ' AND lang = ?'
            params.append(str(lang))
        facet, facet_params = _taxonomy_filter(conn, activity, season, event, expansion)
        if facet:
            where += ' AND ' + facet
            params.extend(facet_params)
        cfilter, cparams = _class_filter(class_tag)
        where += cfilter
        params.extend(cparams)
        if exclude_stage:
            where += " AND speaker NOT IN ('Narration', 'Cutscene')"
        if timeline:
            where += ' AND timeline = ?'
            params.append(str(timeline))
        if entity_clause is not None:
            where += entity_clause
            params.extend(entity_params)
        return conn.execute(f'SELECT COUNT(*) FROM fts WHERE {where}', params).fetchone()[0]
    finally:
        conn.close()


@_guard
def verify_many(quotes, speaker=None, exact=False):
    """Verify up to 20 quotes in one call."""
    if not isinstance(quotes, (list, tuple)) or not quotes:
        raise ValueError('quotes must be a list of 1-20 strings')
    if len(quotes) > 20:
        raise ValueError('at most 20 quotes per call')
    results = [verify(q, speaker=speaker, exact=exact) for q in quotes]
    return {'verified': sum(1 for r in results if r['verified']), 'total': len(results),
            'results': results}


@_guard
def character_info(name):
    """Character metadata, aliases and line counts."""
    conn = connect()
    try:
        ch = _resolve_character(conn, name)
        if not ch:
            row = None
            for variant in _speaker_variants(name):
                row = conn.execute(
                    "SELECT speaker, COUNT(*) FROM transcript_lines "
                    "WHERE speaker LIKE ? ESCAPE '\\' AND is_stage_dir=0 "
                    "GROUP BY speaker ORDER BY 2 DESC LIMIT 1",
                    (f'%{_like(variant)}%',)).fetchone()
                if row:
                    break
            if not row:
                return None
            spoken = conn.execute(
                "SELECT COUNT(*) FROM transcript_lines tl "
                "JOIN transcripts t ON t.id = tl.transcript_id "
                "WHERE tl.speaker=? AND tl.is_stage_dir=0 AND tl.is_optional=0 "
                "AND COALESCE(t.source_tier, '') != 'game_caption'",
                (row[0],)).fetchone()[0]
            return {'name': row[0], 'slug': row[0].lower().replace(' ', '-'),
                    'quotes': 0, 'spoken_lines': spoken,
                    'sources': {'transcript': spoken}, 'aliases': []}
        quotes = conn.execute('SELECT COUNT(*) FROM character_lines WHERE character_id=?', (ch['id'],)).fetchone()[0]
        sources = {r[0]: r[1] for r in conn.execute(
            'SELECT source_type, COUNT(*) FROM character_lines WHERE character_id=? GROUP BY source_type',
            (ch['id'],)).fetchall()}
        # spoken_lines matches persona.json canon_lines: exact speaker, canonical
        # rows only, game captions excluded (source_tier='game_caption' is
        # searchable canon but not part of a persona's curated voice count).
        # Variant speakers ("Eris Morn (Transformed)") stay reachable through
        # character(all_lines=True), which uses a LIKE match.
        spoken = conn.execute(
            "SELECT COUNT(*) FROM transcript_lines tl "
            "JOIN transcripts t ON t.id = tl.transcript_id "
            "WHERE tl.speaker=? AND tl.is_stage_dir=0 AND tl.is_optional=0 "
            "AND COALESCE(t.source_tier, '') != 'game_caption'",
            (ch['name'],)).fetchone()[0]
        aliases = [r[0] for r in conn.execute(
            'SELECT alias FROM speaker_aliases WHERE canonical=? ORDER BY alias', (ch['name'],)).fetchall()]
        return {'name': ch['name'], 'slug': ch['slug'], 'quotes': quotes,
                'spoken_lines': spoken, 'sources': sources, 'aliases': aliases}
    finally:
        conn.close()


@_guard
def book(ref, limit=20, offset=0, full=False):
    """Book metadata and entries. ref accepts a slug or a title fragment."""
    conn = connect()
    try:
        b = _resolve(conn, 'books', ref, 'id, slug, title, source_url, entry_count')
        if not b:
            b = _resolve(conn, 'books', f'book-{ref}', 'id, slug, title, source_url, entry_count')
        if not b:
            return None
        total = conn.execute('SELECT COUNT(*) FROM book_entries WHERE book_id=?', (b['id'],)).fetchone()[0]
        rows = conn.execute(
            'SELECT title, body, seq FROM book_entries WHERE book_id=? ORDER BY seq LIMIT ? OFFSET ?',
            (b['id'], _limit(limit, 20), _offset(offset))).fetchall()
        entries = [{'title': r['title'] or b['title'], 'seq': r['seq'],
                    'body': (r['body'] or '') if full else _snippet(r['body'])}
                   for r in rows]
        return {'book': dict(b), 'total': total, 'limit': _limit(limit, 20),
                'offset': _offset(offset), 'entries': entries}
    finally:
        conn.close()


@_guard
def transcript(ref, speaker=None, limit=50, offset=0, full=False, include_stage=False,
               canon_only=False, section=None, class_tag=None, tiers=None,
               exclude_tiers=None):
    """Transcript metadata and dialogue lines. ref accepts a slug or title fragment.

    A transcript has one source tier, so a tier filter either includes the
    whole transcript or returns its metadata with zero lines and
    `tier_match: false`.
    """
    conn = connect()
    try:
        t = _resolve(conn, 'transcripts', ref, 'id, slug, title, release, characters, arc, source_url, source_tier, timeline, timeline_basis')
        if not t:
            return None
        tier = (t['source_tier'] or '')
        include = _tier_values(tiers)
        exclude = _tier_values(exclude_tiers)
        tier_match = ((not include or tier in include)
                      and tier not in exclude)
        if not tier_match:
            return {'transcript': dict(t), 'total': 0, 'limit': _limit(limit, 50),
                    'offset': _offset(offset), 'lines': [], 'tier_match': False,
                    'tier_filter': {'tiers': include, 'exclude_tiers': exclude}}
        where = ['transcript_id = ?']
        params = [t['id']]
        if not include_stage:
            where.append('is_stage_dir = 0')
        if speaker:
            where.append("speaker LIKE ? ESCAPE '\\'")
            params.append(f'%{_like(speaker)}%')
        if canon_only:
            where.append('is_optional = 0')
        if section:
            where.append("section LIKE ? ESCAPE '\\'")
            params.append(f'%{_like(section)}%')
        if class_tag:
            where.append("(class_tag IS NULL OR class_tag='' OR class_tag=?)")
            params.append(str(class_tag).lower())
        clause = ' AND '.join(where)
        total = conn.execute(f'SELECT COUNT(*) FROM transcript_lines WHERE {clause}', params).fetchone()[0]
        rows = conn.execute(
            f'SELECT seq, speaker, line, section, is_optional, class_tag FROM transcript_lines WHERE {clause} '
            f'ORDER BY seq LIMIT ? OFFSET ?',
            params + [_limit(limit, 50), _offset(offset)]).fetchall()
        lines = [{'seq': r['seq'], 'speaker': r['speaker'],
                  'text': (r['line'] or '') if full else _snippet(r['line']),
                  'section': r['section'], 'optional': bool(r['is_optional']),
                  'class_tag': r['class_tag'] or None}
                 for r in rows]
        tax = conn.execute(
            'SELECT activity_slug, activity_type, season_slug, act, event_slug, '
            'expansion_slug, confidence, evidence FROM transcript_classification '
            'WHERE transcript_id=?', (t['id'],)).fetchone()
        out = {'transcript': dict(t), 'total': total, 'limit': _limit(limit, 50),
               'offset': _offset(offset), 'lines': lines, 'tier_match': True}
        if tax:
            out['taxonomy'] = dict(tax)
        return out
    finally:
        conn.close()


@_guard
def find_item(query, limit=10, offset=0):
    """Find items by title or slug fragment."""
    if not query or len(query) > 200:
        raise ValueError('query must be 1-200 characters')
    conn = connect()
    try:
        tokens = re.findall(r'[A-Za-z0-9]+', query)
        fts_query = ' '.join(f'{t}*' for t in tokens) if tokens else ''
        rows = []
        total = 0
        if fts_query:
            try:
                total = conn.execute(
                    'SELECT COUNT(*) FROM item_title_fts WHERE item_title_fts MATCH ?',
                    (fts_query,)).fetchone()[0]
                rows = conn.execute(
                    'SELECT slug, title, item_type, release FROM item_title_fts '
                    'WHERE item_title_fts MATCH ? ORDER BY rank, title LIMIT ? OFFSET ?',
                    (fts_query, _limit(limit, 10), _offset(offset))).fetchall()
            except sqlite3.OperationalError:
                rows, total = [], 0
        if not rows:
            where = "slug = ? OR title LIKE ? ESCAPE '\\'"
            params = [query, f'%{_like(query)}%']
            total = conn.execute(f'SELECT COUNT(*) FROM items WHERE {where}', params).fetchone()[0]
            rows = conn.execute(
                f'SELECT slug, title, item_type, release FROM items WHERE {where} '
                f'ORDER BY CASE WHEN slug = ? THEN 0 ELSE 1 END, title LIMIT ? OFFSET ?',
                params + [query, _limit(limit, 10), _offset(offset)]).fetchall()
        enriched = _enrich_item_rows(conn, rows)
        return {'count': len(enriched), 'total': total, 'limit': _limit(limit, 10),
                'offset': _offset(offset), 'rows': enriched}
    finally:
        conn.close()


@_guard
def record(ref):
    """Record or seal details by slug or title fragment."""
    conn = connect()
    try:
        r = _resolve(conn, 'records', ref, 'slug, title, body, release, source_url')
        if not r:
            return None
        out = dict(r)
        out['body'] = _snippet(out['body'], 4000)
        return out
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Taxonomy: activity / season / event / expansion discovery
# ---------------------------------------------------------------------------
def _resolve_season(conn, ref):
    """Accept a slug, numeric season, 'season 17', or a name fragment."""
    if ref is None:
        return None
    ref = str(ref).strip()
    row = conn.execute('SELECT slug FROM seasons WHERE slug = ?', (ref,)).fetchone()
    if row:
        return row[0]
    m = re.match(r'^(?:season\s+)?(\d{1,2})$', ref, re.I)
    if m:
        row = conn.execute('SELECT slug FROM seasons WHERE season_number = ?', (int(m.group(1)),)).fetchone()
        if row:
            return row[0]
    row = conn.execute(
        "SELECT slug FROM seasons WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
        'ORDER BY season_number LIMIT 1', (f'%{_like(ref)}%',)).fetchone()
    return row[0] if row else None


def _resolve_activity(conn, ref):
    if ref is None:
        return None
    ref = str(ref).strip()
    row = conn.execute('SELECT slug FROM activities WHERE slug = ?', (ref,)).fetchone()
    if row:
        return row[0]
    row = conn.execute(
        "SELECT slug FROM activities WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
        'ORDER BY LENGTH(name) LIMIT 1', (f'%{_like(ref)}%',)).fetchone()
    return row[0] if row else None


def _resolve_event(conn, ref):
    if ref is None:
        return None
    ref = str(ref).strip()
    row = conn.execute('SELECT slug FROM events WHERE slug = ?', (ref,)).fetchone()
    if row:
        return row[0]
    row = conn.execute(
        "SELECT slug FROM events WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
        'ORDER BY LENGTH(name) LIMIT 1', (f'%{_like(ref)}%',)).fetchone()
    return row[0] if row else None


def _resolve_expansion(conn, ref):
    if ref is None:
        return None
    ref = str(ref).strip()
    row = conn.execute('SELECT slug FROM expansions WHERE slug = ?', (ref,)).fetchone()
    if row:
        return row[0]
    row = conn.execute(
        "SELECT slug FROM expansions WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
        'ORDER BY LENGTH(name) LIMIT 1', (f'%{_like(ref)}%',)).fetchone()
    return row[0] if row else None


def _class_filter(value):
    if not value:
        return '', []
    value = str(value).lower()
    if value not in ('hunter', 'titan', 'warlock'):
        return '0', []
    return " AND (class_tag IS NULL OR class_tag='' OR class_tag=?)", [value]


def _taxonomy_filter(conn, activity=None, season=None, event=None, expansion=None):
    """Build an fts.source_slug predicate for the requested facets."""
    clauses, params = [], []
    if activity:
        slug = _resolve_activity(conn, activity)
        if not slug:
            return '0', []
        clauses.append(
            'source_slug IN (SELECT t.slug FROM transcript_classification c '
            'JOIN transcripts t ON t.id=c.transcript_id WHERE c.activity_slug=?)')
        params.append(slug)
    if season:
        slug = _resolve_season(conn, season)
        if not slug:
            return '0', []
        clauses.append(
            '(source_slug IN (SELECT t.slug FROM transcript_classification c '
            ' JOIN transcripts t ON t.id=c.transcript_id WHERE c.season_slug=?)'
            ' OR source_slug IN (SELECT i.slug FROM item_classification c '
            ' JOIN items i ON i.id=c.item_id WHERE c.season_slug=?)'
            ' OR source_slug IN (SELECT b.slug FROM document_classification c '
            " JOIN books b ON b.id=c.source_id WHERE c.source='book' AND c.season_slug=?)"
            ' OR source_slug IN (SELECT r.slug FROM document_classification c '
            " JOIN records r ON r.id=c.source_id WHERE c.source='record' AND c.season_slug=?))")
        params.extend([slug, slug, slug, slug])
    if event:
        slug = _resolve_event(conn, event)
        if not slug:
            return '0', []
        clauses.append(
            '(source_slug IN (SELECT t.slug FROM transcript_classification c '
            ' JOIN transcripts t ON t.id=c.transcript_id WHERE c.event_slug=?)'
            ' OR source_slug IN (SELECT i.slug FROM item_classification c '
            ' JOIN items i ON i.id=c.item_id WHERE c.event_slug=?)'
            ' OR source_slug IN (SELECT b.slug FROM document_classification c '
            " JOIN books b ON b.id=c.source_id WHERE c.source='book' AND c.event_slug=?)"
            ' OR source_slug IN (SELECT r.slug FROM document_classification c '
            " JOIN records r ON r.id=c.source_id WHERE c.source='record' AND c.event_slug=?))")
        params.extend([slug, slug, slug, slug])
    if expansion:
        slug = _resolve_expansion(conn, expansion)
        if not slug:
            return '0', []
        clauses.append(
            '(source_slug IN (SELECT t.slug FROM transcript_classification c '
            ' JOIN transcripts t ON t.id=c.transcript_id WHERE c.expansion_slug=?)'
            ' OR source_slug IN (SELECT i.slug FROM item_classification c '
            ' JOIN items i ON i.id=c.item_id WHERE c.expansion_slug=?)'
            ' OR source_slug IN (SELECT b.slug FROM document_classification c '
            " JOIN books b ON b.id=c.source_id WHERE c.source='book' AND c.expansion_slug=?)"
            ' OR source_slug IN (SELECT r.slug FROM document_classification c '
            " JOIN records r ON r.id=c.source_id WHERE c.source='record' AND c.expansion_slug=?))")
        params.extend([slug, slug, slug, slug])
    return (' AND '.join(clauses) if clauses else ''), params


@_guard
def activities(activity_type=None, season=None, event=None, limit=100, offset=0):
    """List activities with transcript/line coverage."""
    conn = connect()
    try:
        where, params = [], []
        if activity_type:
            where.append('activity_type = ?')
            params.append(activity_type)
        if season:
            slug = _resolve_season(conn, season)
            if not slug:
                return []
            where.append('season_slug = ?')
            params.append(slug)
        if event:
            slug = _resolve_event(conn, event)
            if not slug:
                return []
            where.append('event_slug = ?')
            params.append(slug)
        sql = ('SELECT slug,name,activity_type,season_slug,expansion_slug,event_slug,'
               'vaulted,transcripts,lines, '
               "COALESCE((SELECT status FROM coverage_notes n "
               "WHERE n.entity_type='activity' AND n.slug=v_activity_coverage.slug), "
               "CASE WHEN transcripts>0 THEN 'covered' ELSE 'missing' END) AS coverage_status "
               'FROM v_activity_coverage')
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY lines DESC, name LIMIT ? OFFSET ?'
        params += [_limit(limit, 100), _offset(offset)]
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


@_guard
def seasons():
    """List every season/episode with coverage."""
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(
            'SELECT season_number,slug,name,season_type,vaulted,transcripts,lines, '
            "COALESCE((SELECT status FROM coverage_notes n "
            "WHERE n.entity_type='season' AND n.slug=v_season_coverage.slug), "
            "CASE WHEN transcripts>0 THEN 'covered' ELSE 'missing' END) AS coverage_status "
            'FROM v_season_coverage ORDER BY season_number').fetchall()]
    finally:
        conn.close()


@_guard
def events():
    """List every rotating event with coverage and occurrence count."""
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(
            'SELECT slug,name,event_type,vaulted,transcripts,lines,occurrences, '
            "COALESCE((SELECT status FROM coverage_notes n "
            "WHERE n.entity_type='event' AND n.slug=v_event_coverage.slug), "
            "CASE WHEN transcripts>0 THEN 'covered' ELSE 'missing' END) AS coverage_status "
            'FROM v_event_coverage ORDER BY name').fetchall()]
    finally:
        conn.close()


@_guard
def event(ref):
    """Event details, occurrences and classified transcripts."""
    conn = connect()
    try:
        slug = _resolve_event(conn, ref)
        if not slug:
            return None
        row = conn.execute('SELECT * FROM events WHERE slug=?', (slug,)).fetchone()
        out = dict(row)
        out['occurrences'] = [dict(r) for r in conn.execute(
            'SELECT year,season_slug,start_date,end_date,vaulted FROM event_occurrences '
            'WHERE event_slug=? ORDER BY year', (slug,)).fetchall()]
        out['transcripts'] = [dict(r) for r in conn.execute(
            'SELECT t.slug,t.title,c.confidence FROM transcript_classification c '
            'JOIN transcripts t ON t.id=c.transcript_id WHERE c.event_slug=? '
            'ORDER BY t.title LIMIT 100', (slug,)).fetchall()]
        return out
    finally:
        conn.close()


@_guard
def activity(ref, limit=50, offset=0):
    """Activity details, coverage and classified transcripts."""
    conn = connect()
    try:
        slug = _resolve_activity(conn, ref)
        if not slug:
            return None
        row = conn.execute('SELECT * FROM activities WHERE slug=?', (slug,)).fetchone()
        out = dict(row)
        cov = conn.execute('SELECT transcripts,lines FROM v_activity_coverage WHERE slug=?',
                           (slug,)).fetchone()
        out['coverage'] = dict(cov) if cov else {'transcripts': 0, 'lines': 0}
        note = conn.execute(
            "SELECT status,evidence,source_url FROM coverage_notes "
            "WHERE entity_type='activity' AND slug=?", (slug,)).fetchone()
        out['coverage']['status'] = (dict(note)['status'] if note else
                                     ('covered' if out['coverage']['transcripts'] else 'missing'))
        if note:
            out['coverage']['evidence'] = note['evidence']
            out['coverage']['source_url'] = note['source_url']
        out['transcripts'] = [dict(r) for r in conn.execute(
            'SELECT t.slug,t.title,c.season_slug,c.confidence FROM transcript_classification c '
            'JOIN transcripts t ON t.id=c.transcript_id WHERE c.activity_slug=? '
            'ORDER BY t.title LIMIT ? OFFSET ?',
            (slug, _limit(limit, 50), _offset(offset))).fetchall()]
        out['speakers'] = [{'speaker': r[0], 'lines': r[1]} for r in conn.execute(
            'SELECT tl.speaker, COUNT(*) FROM transcript_classification c '
            'JOIN transcript_lines tl ON tl.transcript_id=c.transcript_id '
            "WHERE c.activity_slug=? AND tl.is_stage_dir=0 AND tl.speaker != '' "
            'GROUP BY tl.speaker ORDER BY 2 DESC LIMIT 15', (slug,)).fetchall()]
        return out
    finally:
        conn.close()


@_guard
def seals():
    """List manifest seals with triumph record counts."""
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(
            'SELECT s.hash, s.name, s.description, COUNT(r.record_hash) AS records '
            'FROM seals s LEFT JOIN seal_records r ON r.seal_hash=s.hash '
            'GROUP BY s.hash ORDER BY s.name').fetchall()]
    finally:
        conn.close()


@_guard
def seal(ref):
    """Seal details and its triumph records."""
    conn = connect()
    try:
        row = conn.execute(
            'SELECT hash,name,description,completion_record_hash FROM seals '
            'WHERE CAST(hash AS TEXT)=? LIMIT 1', (str(ref),)).fetchone()
        if not row:
            row = conn.execute(
                "SELECT hash,name,description,completion_record_hash FROM seals "
                "WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' ORDER BY LENGTH(name) LIMIT 1",
                (f'%{_like(str(ref))}%',)).fetchone()
        if not row:
            return None
        out = dict(row)
        out['records'] = [dict(r) for r in conn.execute(
            'SELECT record_hash,name,description,lore_hash FROM seal_records '
            'WHERE seal_hash=? ORDER BY name', (row['hash'],)).fetchall()]
        return out
    finally:
        conn.close()


@_guard
def lore(ref):
    """Read a lore entry by hash or title fragment, with linked item names."""
    conn = connect()
    try:
        row = conn.execute(
            'SELECT hash,title,subtitle,body,is_duplicate,duplicate_of FROM lore_entries '
            'WHERE CAST(hash AS TEXT)=? LIMIT 1', (str(ref),)).fetchone()
        if not row:
            row = conn.execute(
                "SELECT hash,title,subtitle,body,is_duplicate,duplicate_of FROM lore_entries "
                "WHERE LOWER(title) LIKE LOWER(?) ESCAPE '\\' ORDER BY LENGTH(title) LIMIT 1",
                (f'%{_like(str(ref))}%',)).fetchone()
        if not row:
            return None
        out = dict(row)
        out['items'] = [r[0] for r in conn.execute(
            'SELECT item_title FROM lore_entry_items WHERE lore_hash=? ORDER BY item_title',
            (out['hash'],)).fetchall()]
        return out
    finally:
        conn.close()


@_guard
def coverage():
    """Coverage summary across activities, seasons and events plus gap lists."""
    conn = connect()
    try:
        acts = [dict(r) for r in conn.execute(
            'SELECT slug,name,activity_type,season_slug,vaulted,transcripts,lines '
            'FROM v_activity_coverage ORDER BY lines DESC, name').fetchall()]
        seasons_ = [dict(r) for r in conn.execute(
            'SELECT season_number,slug,name,season_type,vaulted,transcripts,lines '
            'FROM v_season_coverage ORDER BY season_number').fetchall()]
        events_ = [dict(r) for r in conn.execute(
            'SELECT slug,name,event_type,vaulted,transcripts,lines,occurrences '
            'FROM v_event_coverage ORDER BY name').fetchall()]
        notes = [dict(r) for r in conn.execute(
            'SELECT entity_type,slug,status,evidence,source_url '
            'FROM coverage_notes ORDER BY entity_type,slug').fetchall()]
        note_map = {(n['entity_type'], n['slug']): n['status'] for n in notes}

        def status(kind, slug, transcripts):
            return note_map.get((kind, slug), 'covered' if transcripts else 'missing')

        for a in acts:
            a['coverage_status'] = status('activity', a['slug'], a['transcripts'])
        for s in seasons_:
            s['coverage_status'] = status('season', s['slug'], s['transcripts'])
        for e in events_:
            e['coverage_status'] = status('event', e['slug'], e['transcripts'])
        return {
            'activities': acts,
            'seasons': seasons_,
            'events': events_,
            'notes': notes,
            'gaps': {
                'activities_without_transcripts': [a['slug'] for a in acts if a['transcripts'] == 0],
                'seasons_without_transcripts': [s['slug'] for s in seasons_ if s['transcripts'] == 0],
                'events_without_transcripts': [e['slug'] for e in events_ if e['transcripts'] == 0],
                'unexplained': [
                    f"{kind}:{item['slug']}"
                    for kind, items in (('activity', acts), ('event', events_), ('season', seasons_))
                    for item in items
                    if item['coverage_status'] == 'missing'
                ],
            },
        }
    finally:
        conn.close()


def listing(kind, limit=50, offset=0):
    kind = {'triumphs': 'records', 'triumph': 'records'}.get(kind, kind)
    if kind not in ('books', 'characters', 'speakers', 'canon_speakers', 'records',
                    'activities', 'seasons', 'events', 'lore', 'seals'):
        raise ValueError('kind must be one of: books, characters, speakers, '
                         'canon_speakers, records, activities, seasons, events, '
                         'lore, seals, triumphs (alias of records)')
    conn = connect()
    try:
        n = _limit(limit, 50)
        o = _offset(offset)
        if kind == 'books':
            rows = conn.execute('SELECT slug, title, entry_count FROM books ORDER BY title LIMIT ? OFFSET ?', (n, o))
        elif kind == 'characters':
            rows = conn.execute('SELECT slug, name FROM characters ORDER BY name LIMIT ? OFFSET ?', (n, o))
        elif kind == 'speakers':
            rows = conn.execute(
                "SELECT speaker, COUNT(*) AS lines FROM transcript_lines "
                "WHERE speaker NOT IN ('Narration','Cutscene') GROUP BY speaker ORDER BY 2 DESC LIMIT ? OFFSET ?", (n, o))
        elif kind == 'canon_speakers':
            rows = conn.execute(
                'SELECT speaker, lines, transcripts FROM v_canon_speakers '
                'ORDER BY lines DESC, speaker LIMIT ? OFFSET ?', (n, o))
        elif kind == 'activities':
            rows = conn.execute(
                'SELECT slug, name, activity_type, season_slug, transcripts, lines '
                'FROM v_activity_coverage ORDER BY lines DESC, name LIMIT ? OFFSET ?', (n, o))
        elif kind == 'seasons':
            rows = conn.execute(
                'SELECT season_number, slug, name, season_type, transcripts, lines '
                'FROM v_season_coverage ORDER BY season_number LIMIT ? OFFSET ?', (n, o))
        elif kind == 'events':
            rows = conn.execute(
                'SELECT slug, name, event_type, transcripts, lines, occurrences '
                'FROM v_event_coverage ORDER BY name LIMIT ? OFFSET ?', (n, o))
        elif kind == 'lore':
            rows = conn.execute(
                'SELECT hash, title, subtitle, is_duplicate FROM lore_entries '
                'ORDER BY title LIMIT ? OFFSET ?', (n, o))
        elif kind == 'seals':
            rows = conn.execute(
                'SELECT s.hash, s.name, COUNT(r.record_hash) AS records FROM seals s '
                'LEFT JOIN seal_records r ON r.seal_hash=s.hash '
                'GROUP BY s.hash ORDER BY s.name LIMIT ? OFFSET ?', (n, o))
        else:
            rows = conn.execute('SELECT slug, title FROM records ORDER BY title LIMIT ? OFFSET ?', (n, o))
        return [dict(r) for r in rows]
    finally:
        conn.close()


@_guard
def stats():
    """Row counts and top lists, tolerant of an older schema.

    A pre-1.9 database has no `caption_sightings`; that table (and any other
    missing one) is reported in `missing_tables` instead of failing the whole
    call. Consumers should show the gap rather than imply the counts are
    complete.
    """
    conn = connect()
    try:
        counts, missing = {}, []
        for t in ['books', 'book_entries', 'transcripts', 'transcript_lines', 'grimoire_cards',
                  'interactions', 'items', 'records', 'characters', 'character_lines', 'fts',
                  'expansions', 'seasons', 'events', 'event_occurrences', 'activities',
                  'transcript_classification', 'item_classification',
                  'document_classification', 'lore_entries', 'lore_entry_items',
                  'caption_provenance', 'caption_sightings']:
            try:
                counts[t] = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
            except sqlite3.OperationalError:
                missing.append(t)
        try:
            top_items = [{'item_type': r[0], 'count': r[1]} for r in conn.execute(
                "SELECT item_type, COUNT(*) FROM items WHERE item_type != '' "
                'GROUP BY item_type ORDER BY 2 DESC LIMIT 10').fetchall()]
        except sqlite3.OperationalError:
            top_items = []
        try:
            top_speakers = [{'speaker': r[0], 'count': r[1]} for r in conn.execute(
                "SELECT speaker, COUNT(*) FROM transcript_lines WHERE speaker != '' "
                'GROUP BY speaker ORDER BY 2 DESC LIMIT 10').fetchall()]
        except sqlite3.OperationalError:
            top_speakers = []
        out = {'counts': counts, 'top_item_types': top_items,
               'top_speakers': top_speakers}
        try:
            row = conn.execute("SELECT value FROM meta WHERE key='version'").fetchone()
        except sqlite3.OperationalError:
            row = None
        if row:
            out['schema_version'] = row[0]
        if missing:
            out['missing_tables'] = missing
        return out
    finally:
        conn.close()
