#!/usr/bin/env python3
"""Destiny Grimoire MCP server (stdio).

Exposes the canonical lore database as typed tools through the official MCP SDK.
Read-only: every query goes through db/api.py, which opens SQLite in mode=ro.

Run:  ./mcp-server/run.sh            (uses mcp-server/.venv)
      python3 mcp-server/server.py   (when the SDK is installed)
"""
import json
import os
from functools import lru_cache
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'db'))

import api  # noqa: E402
from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

MAX_TEXT = 4000
MAX_RESOURCE = 16000
MCP_MAX_LIMIT = 100
MAX_TOPIC = 300
READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True,
                            open_world_hint=False, destructive_hint=False)


def _topic(value):
    """Clean a free-text prompt topic: no control chars, quotes or blanks."""
    value = api.clean_input(value, MAX_TOPIC)
    return value.replace('"', "'")


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
    version='1.9.0',
    instructions=(
        'Canonical Destiny lore. Tool map: search (keyword discovery across all '
        'content, with an optional entity filter), entity (resolve a name to an '
        'entity: aliases, document counts, relations, fuzzy-flagged candidates), '
        'character + character_info (quotes and metadata by name), '
        'find_item -> item (search items, then details with lore links), book / '
        'transcript / lore / record / seal (read one document by ref), activities '
        '/ activity / seasons / events / event / coverage (taxonomy and coverage), '
        'list_records (cheap listings), stats (row counts), verify / verify_many '
        '(quote check). Call verify with the speaker and exact=true before quoting '
        'any line, and cite the source slug. Prefer search first, then entity, then '
        'fetch the full document by slug. All queries are read-only.'),
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


def _json_len(obj):
    return len(json.dumps(obj, ensure_ascii=False, separators=(',', ':')))


def _jcap(obj):
    """Serialize a resource to JSON that always parses.

    Bound: MAX_RESOURCE. Strategy: try pretty-printed first for readability,
    fall back to compact, then shrink list-valued fields (prefix truncation)
    until it fits. Trimmed collections carry a sibling `<key>_omitted` counter
    so agents know exactly what was left behind and can repage via the tools.
    """
    pretty = json.dumps(obj, ensure_ascii=False)
    if len(pretty) <= MAX_RESOURCE:
        return pretty
    work = json.loads(json.dumps(obj, ensure_ascii=False, separators=(',', ':')))
    wrapped_top = isinstance(work, list)
    if wrapped_top:
        work = {'rows': work}
    while _json_len(work) > MAX_RESOURCE:
        # Pick the largest remaining list and binary-search the largest prefix
        # that still leaves room for the omitted-counters we may add.
        lst_key = None
        lst_bytes = -1
        for key, value in work.items():
            if isinstance(value, list) and value:
                b = _json_len(value)
                if b > lst_bytes:
                    lst_bytes, lst_key = b, key
        if lst_key is None:
            raise ValueError('resource payload exceeds MAX_RESOURCE')
        lst = work[lst_key]
        lo, hi = 0, len(lst) - 1
        while lo <= hi:
            mid = (lo + hi + 1) // 2
            candidate = dict(work, **{lst_key: lst[:mid + 1]})
            omitted_key = f'{lst_key}_omitted'
            candidate[omitted_key] = len(lst) - (mid + 1)
            if _json_len(candidate) <= MAX_RESOURCE:
                lo = mid + 1
            else:
                hi = mid - 1
        if hi < 0:
            # Even a zero-length list does not fit; the scalar fields are too big.
            raise ValueError(f'resource payload exceeds MAX_RESOURCE after trimming {lst_key}')
        work = dict(work, **{lst_key: lst[:hi + 1]})
        work[f'{lst_key}_omitted'] = len(lst) - (hi + 1)
    if wrapped_top:
        # Never silently swap a list for a dict when only the tail was clipped.
        if 'rows_omitted' in work:
            return json.dumps(work, ensure_ascii=False, separators=(',', ':'))
        return json.dumps(work['rows'], ensure_ascii=False, separators=(',', ':'))
    return json.dumps(work, ensure_ascii=False, separators=(',', ':'))


@server.tool(annotations=READ_ONLY)
def search(query: str, type: str | None = None, limit: int = 10, full: bool = False,
           offset: int = 0, rank: bool = True, activity: str | None = None,
           season: str | None = None, event: str | None = None,
           expansion: str | None = None, class_tag: str | None = None,
           exclude_stage: bool = False, timeline: str | None = None,
           lang: str | None = None, entity: str | None = None) -> dict:
    """Full-text search over books, transcripts, cards, items, records and captions.

    Args:
        query: FTS5 query, for example "Crota" or "hive sword logic".
        type: Optional filter: books, transcripts, grimoire, interactions, items,
            records, lore, captions.
        limit: Maximum rows (1-100).
        full: Return full text instead of bounded snippets.
        offset: Rows to skip (0-10000; higher values clamp to 10000).
        rank: Order by FTS relevance instead of insertion order.
        activity: Only content classified under this activity (name or slug).
        season: Season number, slug or name, for example 17 or "haunted".
        event: Rotating event slug or name, for example "the-dawning".
        expansion: Expansion slug or name.
        class_tag: Filter to base lines plus hunter, titan or warlock variants.
        exclude_stage: Drop stage directions and unattributed cutscene captions
            (ranked results already demote them).
        timeline: Only rows from one in-universe story chapter, for example
            the_dark_age, the_taken_war, the_red_war, the_sack_of_the_dreaming_city
            (23 chapters, chronological; see capabilities.json).
        lang: Document language code; every row is 'en' today and later caption
            languages arrive as data rows (see capabilities.json).
        entity: Restrict to documents this entity is linked to in the entity
            web, for example "Savathûn" or "The Witness".

    Rows carry a `snippet` field with the match context highlighted in brackets
    and a `timeline` field (the chapter slug, empty when unknown).
    """
    rows = _api(api.search, query, type=type, limit=_limit(limit, 10), full=full,
                offset=_offset(offset), rank=rank, activity=activity, season=season,
                event=event, expansion=expansion, class_tag=class_tag,
                exclude_stage=exclude_stage, timeline=timeline, lang=lang, entity=entity)
    total = _api(api.search_total, query, type=type, activity=activity, season=season,
                 event=event, expansion=expansion, class_tag=class_tag,
                 exclude_stage=exclude_stage, timeline=timeline, lang=lang, entity=entity)
    if full:
        for r in rows:
            r['text'] = _trim(r.get('text', ''))
    nxt = _offset(offset) + len(rows)
    return {'count': len(rows), 'total': total,
            'next_offset': nxt if nxt < total else None, 'rows': rows}


@server.tool(annotations=READ_ONLY)
def entity(ref: str, kind: str | None = None, limit: int = 10,
           include_unreviewed: bool = False) -> dict:
    """Resolve a name to an entity in the entity web.

    Exact folded match first; when nothing matches, a phonetic fallback is
    returned with fuzzy=true and score <= 0.5 (suggestions, never picks).

    Args:
        ref: Entity or alias name, for example "Savathûn", "Saint-14",
            "The Exo Stranger" or "Elsie Bray".
        kind: Optional filter: char, power, faction or place.
        limit: Candidates to return (1-100).
        include_unreviewed: Include reviewed=0 aliases (default strict).

    Returns ranked candidates plus, for an exact match, the entity's aliases,
    relations (adjacent_to / related_to), document counts by kind and the top
    documents.
    """
    res = _api(api.entity, ref, limit=_limit(limit, 10), kind=kind,
               include_unreviewed=include_unreviewed)
    for row in res['documents']:
        row['ref'] = _trim(row['ref'])
    return res


@server.tool(annotations=READ_ONLY)
def character(name: str, about: str | None = None, all_lines: bool = False,
              limit: int = 20, offset: int = 0, canon_only: bool = False,
              class_tag: str | None = None) -> dict:
    """Character lines from canon.

    Rows carry `timeline`, the in-universe story chapter of the source
    transcript, so a character's voice can be read era by era.

    Args:
        name: Character name or slug as used in the database.
        about: Optional term the line must mention.
        all_lines: Use every transcript line instead of curated quotes.
        limit: Maximum rows (1-100).
        offset: Rows to skip (0-10000).
        canon_only: Exclude optional/variant lines.
        class_tag: Base lines plus hunter, titan or warlock variants.
    """
    res = _api(api.character, name, about=about, all_lines=all_lines,
                limit=_limit(limit, 20), offset=_offset(offset), canon_only=canon_only,
                class_tag=class_tag)
    if res is None:
        return {'found': False, 'header': '', 'rows': []}
    for row in res['rows']:
        row['text'] = _trim(row.get('text', ''))
    return {'found': True, **res}


@server.tool(annotations=READ_ONLY)
def item(slug: str) -> dict:
    """Item details by slug: flavor text, provenance and linked lore.

    Args:
        slug: Lowercase-hyphen slug, for example "gjallarhorn". Discover slugs
            with find_item first; never guess one.
    """
    row = _api(api.item, slug)
    if row is None:
        raise ToolError(f'item not found: {slug}; call find_item(query) to discover slugs')
    row['text'] = _trim(row.get('text', ''))
    return row


@lru_cache(maxsize=512)
def _verify_cached(quote, speaker, exact):
    return json.dumps(api.verify(quote, speaker=speaker, exact=exact), sort_keys=True)


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
    try:
        return json.loads(_verify_cached(quote, speaker or '', exact))
    except (ValueError, FileNotFoundError) as e:
        raise ToolError(str(e)) from e


@server.tool(annotations=READ_ONLY)
def list_records(kind: str, limit: int = 50, offset: int = 0) -> dict:
    """Cheap discovery listings.

    Args:
        kind: books, characters, speakers, records (or triumphs), activities,
            seasons, events, or lore.
        limit: Maximum rows (1-100).
        offset: Rows to skip (0-10000; higher values clamp to 10000).
    """
    rows = _api(api.listing, kind, limit=_limit(limit, 50), offset=_offset(offset))
    return {'count': len(rows), 'rows': rows}


@server.tool(annotations=READ_ONLY)
def stats() -> dict:
    """Row counts plus top item types and speakers.

    A pre-1.9 database has no `caption_sightings`; the response carries
    `missing_tables` instead of failing, so a client can show the gap.
    """
    return _api(api.stats)


@server.tool(annotations=READ_ONLY)
def verify_many(quotes: list[str], speaker: str | None = None, exact: bool = False) -> dict:
    """Verify up to 20 quotes in one call.

    Args:
        quotes: 1-20 strings to check.
        speaker: Require this attribution for every quote.
        exact: Require full canonical lines.
    """
    return _api(api.verify_many, quotes, speaker=speaker, exact=exact)


@server.tool(annotations=READ_ONLY)
def character_info(name: str) -> dict:
    """Character metadata, aliases and line counts.

    Args:
        name: Character name or slug.
    """
    res = _api(api.character_info, name)
    if res is None:
        raise ToolError(f'character not found: {name}')
    return res


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
               full: bool = False, include_stage: bool = False,
               canon_only: bool = False, section: str | None = None,
               class_tag: str | None = None) -> dict:
    """Read a transcript and its dialogue lines.

    The transcript metadata carries `timeline` (in-universe story chapter slug,
    e.g. the_red_war) and `timeline_basis`; lines inherit it in search results.

    Args:
        ref: Transcript slug or a title fragment.
        speaker: Only lines by this speaker.
        limit: Lines per page (1-100).
        offset: Lines to skip (0-10000).
        full: Return full lines instead of snippets.
        include_stage: Include stage directions.
        canon_only: Exclude optional/variant lines.
        section: Only lines from this section or location.
        class_tag: Base lines plus hunter, titan or warlock variants.
    """
    res = _api(api.transcript, ref, speaker=speaker, limit=_limit(limit, 50),
               offset=_offset(offset), full=full, include_stage=include_stage,
               canon_only=canon_only, section=section, class_tag=class_tag)
    if res is None:
        raise ToolError(f'transcript not found: {ref}')
    if full:
        for line in res['lines']:
            line['text'] = _trim(line['text'])
    return res


@server.tool(annotations=READ_ONLY)
def find_item(query: str, limit: int = 10, offset: int = 0) -> dict:
    """Find items by title or slug fragment. Rows include flavor-text snippets
    and linked lore titles, so a follow-up item() call is usually unnecessary.

    Args:
        query: Title words or slug.
        limit: Maximum rows (1-100).
        offset: Rows to skip (0-10000; higher values clamp to 10000).
    """
    return _api(api.find_item, query, limit=_limit(limit, 10), offset=_offset(offset))


@server.tool(annotations=READ_ONLY)
def activities(activity_type: str | None = None, season: str | None = None,
               event: str | None = None, limit: int = 100, offset: int = 0) -> dict:
    """List raids, dungeons, seasonal activities and other content with coverage.

    Args:
        activity_type: raid, dungeon, seasonal, story, patrol, exotic_mission,
            strike, crucible, gambit, public_event, lost_sector, quest, event.
        season: Optional season number, slug or name.
        event: Optional rotating event slug or name.
        limit: Maximum rows (1-100).
        offset: Rows to skip (0-10000).
    """
    rows = _api(api.activities, activity_type=activity_type, season=season,
                event=event, limit=_limit(limit, 100), offset=_offset(offset))
    return {'count': len(rows), 'rows': rows}


@server.tool(annotations=READ_ONLY)
def activity(ref: str, limit: int = 50, offset: int = 0) -> dict:
    """Activity details, coverage status, speakers and classified transcripts.

    Args:
        ref: Activity slug or name fragment (raid, dungeon, seasonal activity).
        limit: Transcripts per page (1-100).
        offset: Transcripts to skip (0-10000).
    """
    res = _api(api.activity, ref, limit=_limit(limit, 50), offset=_offset(offset))
    if res is None:
        raise ToolError(f'activity not found: {ref}')
    return res


@server.tool(annotations=READ_ONLY)
def seasons() -> dict:
    """Every season and episode with its official number and coverage."""
    rows = _api(api.seasons)
    return {'count': len(rows), 'rows': rows}


@server.tool(annotations=READ_ONLY)
def events() -> dict:
    """Every rotating event with coverage and occurrence count."""
    rows = _api(api.events)
    return {'count': len(rows), 'rows': rows}


@server.tool(annotations=READ_ONLY)
def event(ref: str) -> dict:
    """Event details, yearly occurrences and classified transcripts.

    Args:
        ref: Event slug or name fragment, for example "Festival of the Lost".
    """
    res = _api(api.event, ref)
    if res is None:
        raise ToolError(f'event not found: {ref}')
    return res


@server.tool(annotations=READ_ONLY)
def coverage() -> dict:
    """Coverage summary for activities, seasons and events.

    Each row carries `coverage_status`: covered, partial_transcript,
    narration_only, dialogue_source_missing, no_dialogue or missing. The
    `notes` list explains every non-covered entity, and `gaps.unexplained`
    is empty when every zero-coverage entity has a status.
    """
    return _api(api.coverage)


@server.tool(annotations=READ_ONLY)
def record(ref: str) -> dict:
    """Read a triumph or seal record by slug or title fragment.

    Args:
        ref: Record slug (lowercase-hyphen, for example "a-friend-in-need") or
            a title fragment; discover slugs with list_records(kind="records").
    """
    res = _api(api.record, ref)
    if res is None:
        raise ToolError(f'record not found: {ref}')
    return res


@server.tool(annotations=READ_ONLY)
def seals() -> dict:
    """Every manifest seal with its triumph record count.

    Returns:
        {count, rows}; each row carries hash, name, description and records.
    """
    rows = _api(api.seals)
    return {'count': len(rows), 'rows': rows}


@server.tool(annotations=READ_ONLY)
def seal(ref: str) -> dict:
    """Read a seal and its triumph records.

    Args:
        ref: Seal hash or name fragment, for example "30th Anniversary".
            Discover names with seals().
    """
    res = _api(api.seal, ref)
    if res is None:
        raise ToolError(f'seal not found: {ref}')
    return res


@server.tool(annotations=READ_ONLY)
def lore(ref: str) -> dict:
    """Read a manifest lore entry by hash or title fragment.

    Args:
        ref: Numeric lore hash or a TITLE fragment (lore entries have no slug;
            "the-books-of-sorrow" style slugs will not resolve — pass e.g.
            "Books of Sorrow" or a hash).
    """
    res = _api(api.lore, ref)
    if res is None:
        raise ToolError(f'lore entry not found: {ref}')
    res['body'] = _trim(res.get('body') or '')
    return res


@server.resource('grimoire://books', name='books', description='All lore books',
                 mime_type='application/json')
def books_resource() -> str:
    return _jcap(api.listing('books', limit=10000))


@server.resource('grimoire://characters', name='characters', description='Curated characters',
                 mime_type='application/json')
def characters_resource() -> str:
    return _jcap(api.listing('characters', limit=10000))


@server.resource('grimoire://records', name='records', description='Triumphs and seals',
                 mime_type='application/json')
def records_resource() -> str:
    return _jcap(api.listing('records', limit=10000))


@server.resource('grimoire://stats', name='stats', description='Database row counts',
                 mime_type='application/json')
def stats_resource() -> str:
    return _jcap(api.stats()['counts'])


@server.resource('grimoire://entities', name='entities',
                 description='Entity web: every entity with kind, alias count and document count',
                 mime_type='application/json')
def entities_resource() -> str:
    return _jcap(api.entity_index())


@server.resource('grimoire://activities', name='activities',
                 description='Activities with transcript and line coverage',
                 mime_type='application/json')
def activities_resource() -> str:
    return _jcap(api.activities(limit=10000))


@server.resource('grimoire://seasons', name='seasons',
                 description='Official seasons and episodes with coverage',
                 mime_type='application/json')
def seasons_resource() -> str:
    return _jcap(api.seasons())


@server.resource('grimoire://events', name='events',
                 description='Rotating events with coverage', mime_type='application/json')
def events_resource() -> str:
    return _jcap(api.events())


@server.resource('grimoire://coverage', name='coverage',
                 description='Coverage matrix and gap lists', mime_type='application/json')
def coverage_resource() -> str:
    return _jcap(api.coverage())


@server.resource('grimoire://book/{slug}', name='book', description='A lore book with entries',
                 mime_type='application/json')
def book_resource(slug: str) -> str:
    res = api.book(slug, limit=10000, full=True)
    if res is None:
        raise ValueError(f'book not found: {slug}')
    return _jcap(res)


@server.resource('grimoire://transcript/{slug}', name='transcript',
                 description='A transcript with dialogue', mime_type='application/json')
def transcript_resource(slug: str) -> str:
    res = api.transcript(slug, limit=2000, full=True)
    if res is None:
        raise ValueError(f'transcript not found: {slug}')
    return _jcap(res)


@server.resource('grimoire://character/{slug}', name='character',
                 description='Character metadata and curated quotes', mime_type='application/json')
def character_resource(slug: str) -> str:
    info = api.character_info(slug)
    if info is None:
        raise ValueError(f'character not found: {slug}')
    lines = api.character(slug, limit=10000)
    return _jcap({'info': info, 'lines': lines['rows'] if lines else []})


@server.resource('grimoire://record/{slug}', name='record', description='A triumph or seal',
                 mime_type='application/json')
def record_resource(slug: str) -> str:
    res = api.record(slug)
    if res is None:
        raise ValueError(f'record not found: {slug}')
    return _jcap(res)


@server.prompt(name='quote_safe_lookup', description='Look up lore and return only verified quotes')
def quote_safe_lookup(topic: str) -> str:
    topic = _topic(topic)
    return (f'Find canonical Destiny lore about "{topic}". Search the grimoire, then '
            'call verify with the speaker and exact=true for every line before quoting it. '
            'If verify fails, do not quote the line.')


@server.prompt(name='character_brief', description='Build a source-backed character brief')
def character_brief(name: str) -> str:
    return (f'Use character_info("{name}") and character("{name}"), then summarize the '
            'character using only verified lines. Attribute every quote to its speaker.')


def main():
    server.run('stdio')


if __name__ == '__main__':
    main()
