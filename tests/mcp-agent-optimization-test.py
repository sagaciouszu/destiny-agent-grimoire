#!/usr/bin/env python3
"""MCP agent-optimization gate: descriptions, errors, snippets, caps, clamps.

Checks that the MCP surface stays LLM-friendly: every tool description names
every parameter, ToolErrors are actionable (no tracebacks, allowed values),
search returns long `snippet` fields with stage directions demoted or
excludable, limit/offset clamps hold, resources are capped, find_item/item
carry flavor text and lore links, and character_info counts match the DB.

Run with the server venv:  mcp-server/.venv/bin/python tests/mcp-agent-optimization-test.py
Exit 0 also when the SDK is absent (SKIP) so the default audit stays dependency-free.
Exit 0 pass / 1 fail.
"""
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

VENV_PY = next((p for p in (
    os.path.join(ROOT, 'mcp-server', '.venv', 'bin', 'python'),
    os.path.join(ROOT, 'mcp-server', '.venv', 'Scripts', 'python.exe'),
) if os.path.exists(p)), None)
if not VENV_PY or os.path.realpath(sys.executable) != os.path.realpath(VENV_PY):
    if not VENV_PY:
        print('SKIP: mcp-server/.venv not installed')
        sys.exit(0)
    # Re-run under the venv so the MCP SDK imports cleanly.
    import subprocess
    result = subprocess.run([sys.executable if False else VENV_PY,
                             os.path.realpath(__file__)])
    sys.exit(result.returncode)

sys.path.insert(0, os.path.join(ROOT, 'db'))
sys.path.insert(0, os.path.join(ROOT, 'mcp-server'))
import server  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

MAX_RESOURCE = server.MAX_RESOURCE
PASSED = FAILED = 0


def check(name, ok, detail=''):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f'  PASS: {name}')
    else:
        FAILED += 1
        print(f'  FAIL: {name}' + (f' ({detail})' if detail else ''))


def main():
    srv = server.server

    # 1. Instructions guide tool selection and verification.
    instructions = getattr(srv, 'instructions', '') or ''
    check('instructions name verify + search + read-only',
          'verify' in instructions and 'search' in instructions
          and 'read-only' in instructions and len(instructions) > 150,
          f'len={len(instructions)}')

    # 2. Every tool description names every parameter.
    tools = srv._tool_manager.list_tools()
    check('21 tools registered', len(tools) == 21, f'got {len(tools)}')
    missing = []
    empty = []
    for t in tools:
        desc = t.description or ''
        if not desc.strip():
            empty.append(t.name)
        for prop in (t.parameters or {}).get('properties', {}):
            if prop not in desc:
                missing.append(f'{t.name}.{prop}')
    check('every tool has a description', not empty, ','.join(empty))
    check('every parameter appears in its tool description',
          not missing, ','.join(missing))

    # 3. Errors are actionable: no tracebacks, allowed values present.
    for name, args, needle in (
            ('item', {'slug': 'does-not-exist'}, 'not found'),
            ('record', {'ref': 'no-such-record-xyz'}, 'not found'),
            ('character_info', {'name': 'Nobody McFake'}, 'not found'),
            ('list_records', {'kind': 'bogus'}, 'must be one of'),
            ('search', {'query': 'Crota', 'type': 'bogus'}, 'must be one of')):
        try:
            getattr(server, name)(**args)
            check(f'{name} bad input raises', False, 'no error raised')
        except ToolError as e:
            msg = str(e)
            check(f'{name} error is actionable',
                  needle in msg and 'Traceback' not in msg, msg[:120])
        except Exception as e:  # noqa: BLE001 - any other shape is a failure
            check(f'{name} error is actionable', False,
                  f'{type(e).__name__}: {e}')

    # 4. Snippets: right key, long enough to judge relevance.
    found = server.search('illuminated a path', limit=3)['rows']
    check('search rows use key "snippet"', found and 'snippet' in found[0]
          and 'snip' not in found[0], ','.join(found[0].keys()) if found else 'no rows')
    longest = max((len(r['snippet']) for r in found), default=0)
    check('snippet long enough to judge relevance (>100 chars)',
          longest > 100, f'longest={longest}')

    # 5. Stage directions demoted by default, excludable on demand.
    top = server.search('Crota', limit=5)['rows']
    check('default ranking does not lead with stage directions',
          top and top[0]['speaker'] != 'Narration',
          str([r['speaker'] for r in top]))
    excl = server.search('Crota', limit=20, exclude_stage=True)['rows']
    check('exclude_stage drops Narration and Cutscene',
          all(r['speaker'] not in ('Narration', 'Cutscene') for r in excl),
          str({r['speaker'] for r in excl}))
    plain_total = server.api.search_total('Crota')
    excl_total = server.api.search_total('Crota', exclude_stage=True)
    check('exclude_stage shrinks the reported total',
          0 < excl_total < plain_total, f'{excl_total} !< {plain_total}')

    # 6. Clamps.
    capped = server.search('Crota', limit=999999, offset=999999)
    check('limit=999999 clamps to 100', capped['count'] <= 100,
          str(capped['count']))
    check('offset=999999 clamps to 10000 (no rows past the data)',
          capped['count'] == 0, str(capped['count']))

    # 7. Resource payloads stay inside the cap.
    oversized = []
    for fn in (server.books_resource, server.characters_resource,
               server.records_resource, server.stats_resource,
               server.activities_resource, server.seasons_resource,
               server.events_resource, server.coverage_resource,
               lambda: server.book_resource('book-above-all-else'),
               lambda: server.transcript_resource('contact-io'),
               lambda: server.character_resource('drifter'),
               lambda: server.record_resource('a-friend-in-need')):
        text = fn()
        if len(text) > MAX_RESOURCE + 64:
            oversized.append(f'{fn.__name__}={len(text)}')
    check(f'resources capped at ~{MAX_RESOURCE} chars', not oversized,
          ','.join(oversized))

    # 8. find_item carries text+lore so agents skip the follow-up item() call.
    found = server.find_item('Gjallarhorn', limit=3)
    row = found['rows'][0]
    check('find_item rows include text and lore',
          'text' in row and 'lore' in row, ','.join(row.keys()))
    detail = server.item(row['slug'])
    check('item() drops internal fields',
          'norm_text' not in detail and 'id' not in detail
          and 'lore' in detail, ','.join(detail.keys()))
    check('find_item -> item title parity',
          detail['title'] == row['title'])

    # 9. character_info.spoken_lines matches the canonical DB count.
    db = os.path.join(ROOT, 'db', 'grimoire.db')
    conn = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    for speaker in ('Eris Morn', 'Drifter', 'Zavala', 'Calus', 'Ghost'):
        expected = conn.execute(
            'SELECT COUNT(*) FROM transcript_lines '
            'WHERE speaker=? AND is_stage_dir=0 AND is_optional=0',
            (speaker,)).fetchone()[0]
        info = server.character_info(speaker)
        check(f'{speaker} spoken_lines matches DB ({expected})',
              info['spoken_lines'] == expected,
              f"got {info['spoken_lines']}")
    conn.close()

    print(f'Passed: {PASSED} | Failed: {FAILED}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
