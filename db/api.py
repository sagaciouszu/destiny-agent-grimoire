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
    q = (name or '').strip()
    slug = q.lower().replace(' ', '-')
    row = conn.execute(
        'SELECT id, name, slug FROM characters WHERE LOWER(name)=LOWER(?) OR LOWER(slug)=LOWER(?)',
        (q, slug)).fetchone()
    if row:
        return row
    row = conn.execute(
        "SELECT id, name, slug FROM characters WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
        "OR LOWER(slug) LIKE LOWER(?) ESCAPE '\\' "
        'ORDER BY LENGTH(name) LIMIT 1', (f'{_like(q)}%', f'{_like(slug)}%')).fetchone()
    if row:
        return row
    return conn.execute(
        "SELECT id, name, slug FROM characters WHERE LOWER(name) LIKE LOWER(?) ESCAPE '\\' "
        "OR LOWER(slug) LIKE LOWER(?) ESCAPE '\\' "
        'ORDER BY LENGTH(name) LIMIT 1', (f'%{_like(q)}%', f'%{_like(slug)}%')).fetchone()


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
def search(term, type=None, limit=10, full=False, offset=0, rank=True):
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
        params.append(_limit(limit, 10))
        params.append(_offset(offset))
        order = (" ORDER BY bm25(fts, 3.0, 1.0, 1.0, 1.0, 0.0)"
                 " + CASE WHEN source='item' THEN 1.0 ELSE 0 END") if rank else ''
        try:
            if full:
                rows = conn.execute(
                    f'SELECT title, speaker, text, source FROM fts WHERE {where}{order} LIMIT ? OFFSET ?', params).fetchall()
            else:
                rows = conn.execute(
                    f"SELECT title, speaker, source, snippet(fts, 1, '[', ']', '…', 10) AS snip "
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


def _transcript_lines(conn, name, pattern, limit, offset):
    for variant in _speaker_variants(name):
        params = [f'%{_like(variant)}%']
        sql = ("SELECT line AS text, speaker, '' AS source_slug FROM transcript_lines "
               "WHERE speaker LIKE ? ESCAPE '\\' AND is_stage_dir=0")
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
def character(name, about=None, all_lines=False, limit=20, offset=0):
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
            rows = _transcript_lines(conn, name, pattern, limit, offset)
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
def search_total(term, type=None):
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
def transcript(ref, speaker=None, limit=50, offset=0, full=False, include_stage=False):
    """Transcript metadata and dialogue lines. ref accepts a slug or title fragment."""
    conn = connect()
    try:
        t = _resolve(conn, 'transcripts', ref, 'id, slug, title, release, characters, arc, source_url')
        if not t:
            return None
        where = ['transcript_id = ?']
        params = [t['id']]
        if not include_stage:
            where.append('is_stage_dir = 0')
        if speaker:
            where.append("speaker LIKE ? ESCAPE '\\'")
            params.append(f'%{_like(speaker)}%')
        clause = ' AND '.join(where)
        total = conn.execute(f'SELECT COUNT(*) FROM transcript_lines WHERE {clause}', params).fetchone()[0]
        rows = conn.execute(
            f'SELECT seq, speaker, line FROM transcript_lines WHERE {clause} '
            f'ORDER BY seq LIMIT ? OFFSET ?',
            params + [_limit(limit, 50), _offset(offset)]).fetchall()
        lines = [{'seq': r['seq'], 'speaker': r['speaker'],
                  'text': (r['line'] or '') if full else _snippet(r['line'])}
                 for r in rows]
        return {'transcript': dict(t), 'total': total, 'limit': _limit(limit, 50),
                'offset': _offset(offset), 'lines': lines}
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


def listing(kind, limit=50, offset=0):
    if kind not in ('books', 'characters', 'speakers', 'records'):
        raise ValueError('kind must be one of: books, characters, speakers, records')
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
                  'interactions', 'items', 'records', 'characters', 'character_lines', 'fts']:
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
