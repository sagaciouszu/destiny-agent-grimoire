#!/usr/bin/env python3
"""Destiny Grimoire MCP server (stdio).

Exposes the canonical lore database as typed tools through the official MCP SDK.
Read-only: every query goes through db/api.py, which opens SQLite in mode=ro.

Run:  ./mcp-server/run.sh            (uses mcp-server/.venv)
      python3 mcp-server/server.py   (when the SDK is installed)
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'db'))

import api  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

MAX_TEXT = 4000
MCP_MAX_LIMIT = 100
READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True,
                            open_world_hint=False, destructive_hint=False)


def _limit(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(value, MCP_MAX_LIMIT))


def _offset(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(value, 10000))

server = MCPServer(
    'destiny-grimoire',
    version='1.4.0',
    instructions=(
        'Canonical Destiny lore. Search for topics, pull character lines, look up '
        'items, and call verify before quoting anything. All queries are read-only.'),
)


def _api(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except (ValueError, FileNotFoundError) as e:
        raise ToolError(str(e)) from e


def _trim(text, limit=MAX_TEXT):
    if text and len(text) > limit:
        return text[:limit].rsplit(' ', 1)[0] + '...'
    return text


@server.tool(annotations=READ_ONLY)
def search(query: str, type: str | None = None, limit: int = 10, full: bool = False,
           offset: int = 0) -> dict:
    """Full-text search over books, transcripts, cards, items and records.

    Args:
        query: FTS5 query, for example "Crota" or "hive sword logic".
        type: Optional filter: books, transcripts, grimoire, interactions, items, records.
        limit: Maximum rows (1-100).
        full: Return full text instead of bounded snippets.
        offset: Rows to skip (0-10000).
    """
    rows = _api(api.search, query, type=type, limit=_limit(limit, 10), full=full,
                offset=_offset(offset))
    if full:
        for r in rows:
            r['text'] = _trim(r.get('text', ''))
    return {'count': len(rows), 'rows': rows}


@server.tool(annotations=READ_ONLY)
def character(name: str, about: str | None = None, all_lines: bool = False,
              limit: int = 20, offset: int = 0) -> dict:
    """Character lines from canon.

    Args:
        name: Character name or slug as used in the database.
        about: Optional term the line must mention.
        all_lines: Use every transcript line instead of curated quotes.
        limit: Maximum rows (1-100).
        offset: Rows to skip (0-10000).
    """
    res = _api(api.character, name, about=about, all_lines=all_lines,
                limit=_limit(limit, 20), offset=_offset(offset))
    if res is None:
        return {'found': False, 'header': '', 'rows': []}
    for row in res['rows']:
        row['text'] = _trim(row.get('text', ''))
    return {'found': True, **res}


@server.tool(annotations=READ_ONLY)
def item(slug: str) -> dict:
    """Item details by slug, including lore and flavor text when present."""
    row = _api(api.item, slug)
    if row is None:
        raise ToolError(f'item not found: {slug}')
    row['text'] = _trim(row.get('text', ''))
    return row


@server.tool(annotations=READ_ONLY)
def verify(quote: str, speaker: str | None = None, exact: bool = False) -> dict:
    """Check a quote against canon. Use before quoting anything.

    Args:
        quote: The text to check.
        speaker: Require this attribution; sources with no speaker are excluded.
        exact: Require a full canonical row, not a substring.

    Returns verified=true only when the text traces to canonical content, with
    source, speaker and exact-match flags.
    """
    return _api(api.verify, quote, speaker=speaker, exact=exact)


@server.tool(annotations=READ_ONLY)
def list_records(kind: str, limit: int = 50, offset: int = 0) -> dict:
    """Cheap discovery listings.

    Args:
        kind: books, characters, speakers, or records.
        limit: Maximum rows (1-100).
        offset: Rows to skip (0-10000).
    """
    rows = _api(api.listing, kind, limit=_limit(limit, 50), offset=_offset(offset))
    return {'count': len(rows), 'rows': rows}


@server.tool(annotations=READ_ONLY)
def stats() -> dict:
    """Row counts plus top item types and speakers."""
    return _api(api.stats)


@server.tool(annotations=READ_ONLY)
def book(ref: str, limit: int = 20, offset: int = 0, full: bool = False) -> dict:
    """Read a lore book and its entries.

    Args:
        ref: Book slug (with or without the book- prefix) or a title fragment.
        limit: Entries per page (1-100).
        offset: Entries to skip (0-10000).
        full: Return full entry text instead of a snippet.
    """
    res = _api(api.book, ref, limit=_limit(limit, 20), offset=_offset(offset), full=full)
    if res is None:
        raise ToolError(f'book not found: {ref}')
    if full:
        for e in res['entries']:
            e['body'] = _trim(e['body'])
    return res


@server.tool(annotations=READ_ONLY)
def transcript(ref: str, speaker: str | None = None, limit: int = 50, offset: int = 0,
               full: bool = False, include_stage: bool = False) -> dict:
    """Read a transcript and its dialogue lines.

    Args:
        ref: Transcript slug or a title fragment.
        speaker: Only lines by this speaker.
        limit: Lines per page (1-100).
        offset: Lines to skip (0-10000).
        full: Return full lines instead of snippets.
        include_stage: Include stage directions.
    """
    res = _api(api.transcript, ref, speaker=speaker, limit=_limit(limit, 50),
               offset=_offset(offset), full=full, include_stage=include_stage)
    if res is None:
        raise ToolError(f'transcript not found: {ref}')
    if full:
        for line in res['lines']:
            line['text'] = _trim(line['text'])
    return res


@server.tool(annotations=READ_ONLY)
def find_item(query: str, limit: int = 10, offset: int = 0) -> dict:
    """Find items by title or slug fragment.

    Args:
        query: Title words or slug.
        limit: Maximum rows (1-100).
        offset: Rows to skip (0-10000).
    """
    return _api(api.find_item, query, limit=_limit(limit, 10), offset=_offset(offset))


@server.tool(annotations=READ_ONLY)
def record(ref: str) -> dict:
    """Read a triumph or seal by slug or title fragment."""
    res = _api(api.record, ref)
    if res is None:
        raise ToolError(f'record not found: {ref}')
    return res


@server.resource('grimoire://books', name='books', description='All lore books',
                 mime_type='application/json')
def books_resource() -> str:
    return json.dumps(api.listing('books', limit=10000), ensure_ascii=False)


@server.resource('grimoire://characters', name='characters', description='Curated characters',
                 mime_type='application/json')
def characters_resource() -> str:
    return json.dumps(api.listing('characters', limit=10000), ensure_ascii=False)


@server.resource('grimoire://records', name='records', description='Triumphs and seals',
                 mime_type='application/json')
def records_resource() -> str:
    return json.dumps(api.listing('records', limit=10000), ensure_ascii=False)


@server.resource('grimoire://stats', name='stats', description='Database row counts',
                 mime_type='application/json')
def stats_resource() -> str:
    return json.dumps(api.stats()['counts'], ensure_ascii=False)


def main():
    server.run('stdio')


if __name__ == '__main__':
    main()
