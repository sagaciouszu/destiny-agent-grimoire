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
MAX_LIMIT = 100


def db_path():
    return os.environ.get('GRIMOIRE_DB') or DEFAULT_DB


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
    return conn


def _limit(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, MAX_LIMIT))


def search(term, type=None, limit=10, full=False):
    """Full-text search. Returns rows with a snippet unless full=True."""
    if type is not None and type not in TYPE_TO_SOURCE:
        raise ValueError(f'type must be one of: {", ".join(TYPE_TO_SOURCE)}')
    conn = connect()
    try:
        where = 'fts MATCH ?'
        params = [term]
        if type:
            where += ' AND source = ?'
            params.append(TYPE_TO_SOURCE[type])
        params.append(_limit(limit, 10))
        if full:
            rows = conn.execute(
                f'SELECT title, speaker, text, source FROM fts WHERE {where} LIMIT ?', params).fetchall()
        else:
            rows = conn.execute(
                f"SELECT title, speaker, source, snippet(fts, 1, '[', ']', '…', 10) AS snip "
                f'FROM fts WHERE {where} LIMIT ?', params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def character(name, about=None, all_lines=False, limit=20):
    """Curated character quotes, or every transcript line with all_lines=True.

    Returns {'header': str, 'rows': [...]} or None when a curated character is absent.
    """
    conn = connect()
    try:
        pattern = f'%{about.lower()}%' if about else None
        if all_lines:
            params = [f'%{name}%']
            sql = ("SELECT line AS text, speaker, '' AS source_slug FROM transcript_lines "
                   'WHERE speaker LIKE ? AND is_stage_dir=0')
            if pattern:
                sql += ' AND LOWER(line) LIKE ?'
                params.append(pattern)
            sql += ' LIMIT ?'
            params.append(_limit(limit, 20))
            rows = conn.execute(sql, params).fetchall()
            return {'header': f'=== {name} (transcript lines) ===', 'rows': [dict(r) for r in rows]}

        ch = conn.execute(
            "SELECT id, name, slug FROM characters WHERE name LIKE ? OR slug LIKE ?",
            (f'%{name}%', f'%{name.lower().replace(" ", "-")}%')).fetchone()
        if not ch:
            return None
        params = [ch['id']]
        sql = "SELECT text, '' AS speaker, source_slug FROM character_lines WHERE character_id = ?"
        if pattern:
            sql += ' AND LOWER(text) LIKE ?'
            params.append(pattern)
        sql += ' LIMIT ?'
        params.append(_limit(limit, 20))
        rows = conn.execute(sql, params).fetchall()
        return {'header': f"=== {ch['name']} ({ch['slug']}) ===", 'rows': [dict(r) for r in rows]}
    finally:
        conn.close()


def item(slug):
    conn = connect()
    try:
        row = conn.execute('SELECT * FROM items WHERE slug = ?', (slug,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def verify(quote):
    """Check a quoted string against canon. Returns {'quote','verified','matches'}."""
    nq = norm(quote)
    hits = []
    if not nq:
        return {'quote': quote, 'verified': False, 'matches': []}
    conn = connect()
    try:
        rows = conn.execute(
            'SELECT t.slug, tl.speaker FROM transcript_lines tl JOIN transcripts t ON t.id=tl.transcript_id '
            'WHERE tl.norm_line LIKE ? LIMIT 3', (f'%{nq}%',)).fetchall()
        hits += [{'source': 'transcript', 'slug': r[0], 'speaker': r[1]} for r in rows]
        rows = conn.execute(
            'SELECT b.slug FROM book_entries e JOIN books b ON b.id = e.book_id '
            'WHERE e.norm_text LIKE ? LIMIT 3', (f'%{nq}%',)).fetchall()
        hits += [{'source': 'book', 'slug': r[0], 'speaker': ''} for r in rows]
        plain = [
            ('grimoire_cards', 'norm_body', 'grimoire_card'),
            ('interactions', 'norm_text', 'interaction'),
            ('items', 'norm_text', 'item'),
            ('records', 'norm_body', 'record'),
        ]
        for tbl, nrm, source in plain:
            if tbl == 'interactions':
                rows = conn.execute(
                    f'SELECT slug, speaker FROM {tbl} WHERE {nrm} LIKE ? LIMIT 3', (f'%{nq}%',)).fetchall()
                hits += [{'source': source, 'slug': r[0], 'speaker': r[1]} for r in rows]
            else:
                rows = conn.execute(
                    f'SELECT slug FROM {tbl} WHERE {nrm} LIKE ? LIMIT 3', (f'%{nq}%',)).fetchall()
                hits += [{'source': source, 'slug': r[0], 'speaker': ''} for r in rows]
    finally:
        conn.close()
    seen, uniq = set(), []
    for h in hits:
        key = (h['source'], h['slug'], h['speaker'])
        if key not in seen:
            seen.add(key)
            uniq.append(h)
    return {'quote': quote, 'verified': bool(uniq), 'matches': uniq}


def listing(kind, limit=50):
    if kind not in ('books', 'characters', 'speakers', 'records'):
        raise ValueError('kind must be one of: books, characters, speakers, records')
    conn = connect()
    try:
        n = _limit(limit, 50)
        if kind == 'books':
            rows = conn.execute('SELECT slug, title, entry_count FROM books ORDER BY title LIMIT ?', (n,))
        elif kind == 'characters':
            rows = conn.execute('SELECT slug, name FROM characters ORDER BY name LIMIT ?', (n,))
        elif kind == 'speakers':
            rows = conn.execute(
                "SELECT speaker, COUNT(*) AS lines FROM transcript_lines "
                "WHERE speaker NOT IN ('Narration','Cutscene') GROUP BY speaker ORDER BY 2 DESC LIMIT ?", (n,))
        else:
            rows = conn.execute('SELECT slug, title FROM records ORDER BY title LIMIT ?', (n,))
        return [dict(r) for r in rows]
    finally:
        conn.close()


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
