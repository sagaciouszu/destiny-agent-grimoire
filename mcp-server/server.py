#!/usr/bin/env python3
"""Destiny Grimoire MCP server (stdio).

Exposes the canonical lore database as typed tools through the official MCP SDK.
Read-only: every query goes through db/api.py, which opens SQLite in mode=ro.

Run:  ./mcp-server/run.sh            (uses mcp-server/.venv)
      python3 mcp-server/server.py   (when the SDK is installed)
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'db'))

_spec = importlib.util.spec_from_file_location('grimoire_api', os.path.join(ROOT, 'db', 'api.py'))
api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(api)

from mcp.server.mcpserver import MCPServer  # noqa: E402

MAX_TEXT = 4000

server = MCPServer(
    'destiny-grimoire',
    version='1.4.0',
    instructions=(
        'Canonical Destiny lore. Search for topics, pull character lines, look up '
        'items, and call verify before quoting anything. All queries are read-only.'),
)


def _trim(text, limit=MAX_TEXT):
    if text and len(text) > limit:
        return text[:limit].rsplit(' ', 1)[0] + '...'
    return text


@server.tool()
def search(query: str, type: str | None = None, limit: int = 10, full: bool = False) -> dict:
    """Full-text search over books, transcripts, cards, items and records.

    Args:
        query: FTS5 query, for example "Crota" or "hive sword logic".
        type: Optional filter: books, transcripts, grimoire, interactions, items, records.
        limit: Maximum rows (1-100).
        full: Return full text instead of bounded snippets.
    """
    rows = api.search(query, type=type, limit=limit, full=full)
    if full:
        for r in rows:
            r['text'] = _trim(r.get('text', ''))
    return {'count': len(rows), 'rows': rows}


@server.tool()
def character(name: str, about: str | None = None, all_lines: bool = False,
              limit: int = 20) -> dict:
    """Character lines from canon.

    Args:
        name: Character name or slug as used in the database.
        about: Optional term the line must mention.
        all_lines: Use every transcript line instead of curated quotes.
        limit: Maximum rows (1-100).
    """
    res = api.character(name, about=about, all_lines=all_lines, limit=limit)
    if res is None:
        return {'found': False, 'header': '', 'rows': []}
    return {'found': True, **res}


@server.tool()
def item(slug: str) -> dict:
    """Item details by slug, including lore and flavor text when present."""
    row = api.item(slug)
    if row is None:
        raise ValueError(f'item not found: {slug}')
    row['text'] = _trim(row.get('text', ''))
    return row


@server.tool()
def verify(quote: str) -> dict:
    """Check a quote against canon. Use before quoting anything.

    Returns verified=true only when the text traces to canonical content, with
    source and speaker matches.
    """
    return api.verify(quote)


@server.tool()
def list_records(kind: str, limit: int = 50) -> dict:
    """Cheap discovery listings.

    Args:
        kind: books, characters, speakers, or records.
        limit: Maximum rows (1-100).
    """
    rows = api.listing(kind, limit=limit)
    return {'count': len(rows), 'rows': rows}


@server.tool()
def stats() -> dict:
    """Row counts plus top item types and speakers."""
    return api.stats()


def main():
    server.run('stdio')


if __name__ == '__main__':
    main()
