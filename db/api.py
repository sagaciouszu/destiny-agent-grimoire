#!/usr/bin/env python3
"""Importable query layer for the Destiny Grimoire database.

Both the CLI (`db/query.py`) and the MCP server (`mcp-server/server.py`) call
these functions. Read-only: connections use SQLite URI mode=ro.

Environment:
  GRIMOIRE_DB  override the database path (default: db/grimoire.db)
"""
import os
import re
import sqlite3
from pathlib import Path

DEFAULT_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grimoire.db')
TYPE_TO_SOURCE = {
    'books': 'book_entry', 'transcripts': 'transcript_line', 'grimoire': 'grimoire_card',
    'interactions': 'interaction', 'items': 'item', 'records': 'record',
    'lore': 'lore_entry',
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
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


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
def search(term, type=None, limit=10, full=False, offset=0, rank=True,
           activity=None, season=None, event=None, expansion=None):
    """Full-text search. Returns rows with a snippet unless full=True.

    The term is used as FTS5 syntax when valid; otherwise every word is quoted
    and ANDed, so punctuation (`"`, `(`, `+`, `%`, `:`, `-`) never breaks a query.
    """
    term = clean_input(term, 500)
    if type is not None and type not in TYPE_TO_SOURCE:
        raise ValueError(f'type must be one of: {", ".join(TYPE_TO_SOURCE)}')
    conn = connect()
    try:
        term = fts_query(conn, term)
        where = 'fts MATCH ?'
        params = [term]
        if type:
            where += ' AND source = ?'
            params.append(TYPE_TO_SOURCE[type])
        facet, facet_params = _taxonomy_filter(conn, activity, season, event, expansion)
        if facet:
            where += ' AND ' + facet
            params.extend(facet_params)
        params.append(_limit(limit, 10))
        params.append(_offset(offset))
        order = (" ORDER BY bm25(fts, 3.0, 1.0, 1.0, 1.0, 0.0)"
                 " + CASE WHEN source='item' THEN 1.0 ELSE 0 END") if rank else ''
        try:
            if full:
                rows = conn.execute(
                    f'SELECT title, speaker, text, source, source_slug FROM fts WHERE {where}{order} LIMIT ? OFFSET ?', params).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT title, speaker, source, source_slug, snippet(fts, 1, '[', ']', '…', 10) AS snip "
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


def _transcript_lines(conn, name, pattern, limit, offset, canon_only=False):
    for variant in _speaker_variants(name):
        params = [f'%{_like(variant)}%']
        sql = ("SELECT line AS text, speaker, '' AS source_slug FROM transcript_lines "
               "WHERE speaker LIKE ? ESCAPE '\\' AND is_stage_dir=0")
        if canon_only:
            sql += ' AND is_optional=0'
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
def character(name, about=None, all_lines=False, limit=20, offset=0, canon_only=False):
    """Curated character quotes, or transcript lines for any canon speaker.

    Curated characters use the compendium. Speakers who exist only in
    transcripts fall back to their canonical lines.
    """
    conn = connect()
    try:
        pattern = f'%{_like(about.lower())}%' if about else None
        if all_lines:
            params = [f'%{_like(name)}%']
            sql = ("SELECT line AS text, speaker, '' AS source_slug FROM transcript_lines "
                   "WHERE speaker LIKE ? ESCAPE '\\' AND is_stage_dir=0")
            if pattern:
                sql += " AND LOWER(line) LIKE ? ESCAPE '\\'"
                params.append(pattern)
            sql += ' LIMIT ? OFFSET ?'
            params.append(_limit(limit, 20))
            params.append(_offset(offset))
            rows = conn.execute(sql, params).fetchall()
            return {'header': f'=== {name} (transcript lines) ===', 'rows': [dict(r) for r in rows]}

        ch = _resolve_character(conn, name)
        if not ch:
            rows = _transcript_lines(conn, name, pattern, limit, offset, canon_only=canon_only)
            if not rows:
                return None
            return {'header': f'=== {name} (transcript lines) ===', 'rows': rows}
        params = [ch['id']]
        sql = "SELECT text, '' AS speaker, source_slug FROM character_lines WHERE character_id = ?"
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


@_guard
def item(slug):
    conn = connect()
    try:
        row = conn.execute('SELECT * FROM items WHERE slug = ?', (slug,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _verify_scan(conn, nq):
    """Substring scan across every source (fallback and mid-word fragments)."""
    hits = []
    rows = conn.execute(
        'SELECT t.slug, tl.speaker, tl.norm_line AS norm FROM transcript_lines tl '
        'JOIN transcripts t ON t.id=tl.transcript_id WHERE tl.norm_line LIKE ? LIMIT 3',
        (f'%{nq}%',)).fetchall()
    hits += [{'source': 'transcript', 'slug': r[0], 'speaker': r[1], 'norm': r[2]} for r in rows]
    rows = conn.execute(
        'SELECT b.slug, e.norm_text AS norm FROM book_entries e JOIN books b ON b.id=e.book_id '
        'WHERE e.norm_text LIKE ? LIMIT 3', (f'%{nq}%',)).fetchall()
    hits += [{'source': 'book', 'slug': r[0], 'speaker': '', 'norm': r[1]} for r in rows]
    plain = [
        ('grimoire_cards', 'norm_body', 'grimoire_card', False),
        ('interactions', 'norm_text', 'interaction', True),
        ('items', 'norm_text', 'item', False),
        ('records', 'norm_body', 'record', False),
    ]
    for tbl, nrm, source, has_speaker in plain:
        cols = (f'slug, speaker, {nrm} AS norm' if has_speaker
                else f"slug, {nrm} AS norm, '' AS speaker")
        rows = conn.execute(
            f'SELECT {cols} FROM {tbl} WHERE {nrm} LIKE ? LIMIT 3', (f'%{nq}%',)).fetchall()
        hits += [{'source': source, 'slug': r[0], 'speaker': r[1], 'norm': r[2]} for r in rows]
    return hits


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

    Uses the verification index (normalized phrase lookup) and falls back to a
    substring scan for mid-word fragments or index misses.

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
        if not hits:
            hits = _verify_scan(conn, nq)
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
def search_total(term, type=None, activity=None, season=None, event=None, expansion=None):
    """Total FTS matches for a query (for paging)."""
    term = clean_input(term, 500)
    if type is not None and type not in TYPE_TO_SOURCE:
        raise ValueError(f'type must be one of: {", ".join(TYPE_TO_SOURCE)}')
    conn = connect()
    try:
        term = fts_query(conn, term)
        where = 'fts MATCH ?'
        params = [term]
        if type:
            where += ' AND source = ?'
            params.append(TYPE_TO_SOURCE[type])
        facet, facet_params = _taxonomy_filter(conn, activity, season, event, expansion)
        if facet:
            where += ' AND ' + facet
            params.extend(facet_params)
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
                "SELECT COUNT(*) FROM transcript_lines WHERE speaker=? AND is_stage_dir=0",
                (row[0],)).fetchone()[0]
            return {'name': row[0], 'slug': row[0].lower().replace(' ', '-'),
                    'quotes': 0, 'spoken_lines': spoken,
                    'sources': {'transcript': spoken}, 'aliases': []}
        quotes = conn.execute('SELECT COUNT(*) FROM character_lines WHERE character_id=?', (ch['id'],)).fetchone()[0]
        sources = {r[0]: r[1] for r in conn.execute(
            'SELECT source_type, COUNT(*) FROM character_lines WHERE character_id=? GROUP BY source_type',
            (ch['id'],)).fetchall()}
        spoken = conn.execute(
            "SELECT COUNT(*) FROM transcript_lines WHERE speaker LIKE ? AND is_stage_dir=0",
            (f"%{ch['name']}%",)).fetchone()[0]
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
               canon_only=False, section=None):
    """Transcript metadata and dialogue lines. ref accepts a slug or title fragment."""
    conn = connect()
    try:
        t = _resolve(conn, 'transcripts', ref, 'id, slug, title, release, characters, arc, source_url, source_tier')
        if not t:
            return None
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
        clause = ' AND '.join(where)
        total = conn.execute(f'SELECT COUNT(*) FROM transcript_lines WHERE {clause}', params).fetchone()[0]
        rows = conn.execute(
            f'SELECT seq, speaker, line, section, is_optional FROM transcript_lines WHERE {clause} '
            f'ORDER BY seq LIMIT ? OFFSET ?',
            params + [_limit(limit, 50), _offset(offset)]).fetchall()
        lines = [{'seq': r['seq'], 'speaker': r['speaker'],
                  'text': (r['line'] or '') if full else _snippet(r['line']),
                  'section': r['section'], 'optional': bool(r['is_optional'])}
                 for r in rows]
        tax = conn.execute(
            'SELECT activity_slug, activity_type, season_slug, act, event_slug, '
            'expansion_slug, confidence, evidence FROM transcript_classification '
            'WHERE transcript_id=?', (t['id'],)).fetchone()
        out = {'transcript': dict(t), 'total': total, 'limit': _limit(limit, 50),
               'offset': _offset(offset), 'lines': lines}
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
        return {'count': len(rows), 'total': total, 'limit': _limit(limit, 10),
                'offset': _offset(offset), 'rows': [dict(r) for r in rows]}
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
               'vaulted,transcripts,lines FROM v_activity_coverage')
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
            'SELECT season_number,slug,name,season_type,vaulted,transcripts,lines '
            'FROM v_season_coverage ORDER BY season_number').fetchall()]
    finally:
        conn.close()


@_guard
def events():
    """List every rotating event with coverage and occurrence count."""
    conn = connect()
    try:
        return [dict(r) for r in conn.execute(
            'SELECT slug,name,event_type,vaulted,transcripts,lines,occurrences '
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
        return {
            'activities': acts,
            'seasons': seasons_,
            'events': events_,
            'gaps': {
                'activities_without_transcripts': [a['slug'] for a in acts if a['transcripts'] == 0],
                'seasons_without_transcripts': [s['slug'] for s in seasons_ if s['transcripts'] == 0],
                'events_without_transcripts': [e['slug'] for e in events_ if e['transcripts'] == 0],
            },
        }
    finally:
        conn.close()


def listing(kind, limit=50, offset=0):
    if kind not in ('books', 'characters', 'speakers', 'records',
                    'activities', 'seasons', 'events', 'lore'):
        raise ValueError('kind must be one of: books, characters, speakers, records, '
                         'activities, seasons, events, lore')
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
        else:
            rows = conn.execute('SELECT slug, title FROM records ORDER BY title LIMIT ? OFFSET ?', (n, o))
        return [dict(r) for r in rows]
    finally:
        conn.close()


@_guard
def stats():
    conn = connect()
    try:
        counts = {}
        for t in ['books', 'book_entries', 'transcripts', 'transcript_lines', 'grimoire_cards',
                  'interactions', 'items', 'records', 'characters', 'character_lines', 'fts',
                  'expansions', 'seasons', 'events', 'event_occurrences', 'activities',
                  'transcript_classification', 'item_classification',
                  'document_classification', 'lore_entries', 'lore_entry_items']:
            counts[t] = conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
        top_items = [{'item_type': r[0], 'count': r[1]} for r in conn.execute(
            "SELECT item_type, COUNT(*) FROM items WHERE item_type != '' "
            'GROUP BY item_type ORDER BY 2 DESC LIMIT 10').fetchall()]
        top_speakers = [{'speaker': r[0], 'count': r[1]} for r in conn.execute(
            "SELECT speaker, COUNT(*) FROM transcript_lines WHERE speaker != '' "
            'GROUP BY speaker ORDER BY 2 DESC LIMIT 10').fetchall()]
        return {'counts': counts, 'top_item_types': top_items, 'top_speakers': top_speakers}
    finally:
        conn.close()
