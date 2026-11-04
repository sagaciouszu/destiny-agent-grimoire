#!/usr/bin/env python3
"""MCP matrix: many calls, concurrent clients, parity with the API, clean errors.

Run with the MCP venv:
    mcp-server/.venv/bin/python tests/mcp-matrix-test.py
Skips when the venv is absent.
"""
import asyncio
import json
import os
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
VENV_PY = os.path.join(ROOT, 'mcp-server', '.venv', 'bin', 'python')
if not os.path.exists(VENV_PY):
    print('SKIP: mcp-server/.venv not installed')
    sys.exit(0)

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, 'db'))
import api  # noqa: E402

RUN = os.path.join(ROOT, 'mcp-server', 'run.sh')
DB = os.path.join(ROOT, 'db', 'grimoire.db')
PASS = FAIL = CALLS = 0


def report(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        print(f'  ✓ {name}')
        PASS += 1
    else:
        print(f'  ✗ {name}: {detail}')
        FAIL += 1


def payload(res):
    sc = getattr(res, 'structured_content', None)
    if sc is not None and len(sc) == 1 and 'result' in sc:
        return sc['result']
    if res.content:
        return json.loads(res.content[0].text)
    return sc


async def call(session, name, args):
    global CALLS
    CALLS += 1
    return payload(await session.call_tool(name, args))


async def matrix(s):
    for q in ('crota', 'hive', 'sword logic', 'savathûn', 'gambit'):
        for typ in (None, 'books', 'transcripts', 'grimoire', 'interactions', 'items', 'records'):
            args = {'query': q, 'limit': 3}
            if typ:
                args['type'] = typ
            if q == 'crota' and typ in (None, 'books'):
                args['full'] = True
            res = await call(s, 'search', args)
            assert isinstance(res, dict) and res['count'] == len(res['rows'])
            for row in res['rows']:
                if 'text' in row:
                    assert len(row['text']) <= 4003

    for name in ('eris', 'drifter', 'saint-14', 'nobody-here'):
        for about in (None, 'hive'):
            args = {'name': name, 'limit': 5}
            if about:
                args['about'] = about
            res = await call(s, 'character', args)
            assert 'found' in res and 'rows' in res
    res = await call(s, 'character', {'name': 'eris', 'all_lines': True, 'limit': 50})
    assert all(len(row['text']) <= 4003 for row in res['rows'])

    assert (await call(s, 'item', {'slug': '0a0x-nightmask'}))['slug'] == '0a0x-nightmask'

    for quote in ('I am Eris Morn.', 'Absolutely not.', 'Trust.', 'not canon zzz'):
        for speaker in (None, 'Eris Morn', 'Zavala'):
            for exact in (False, True):
                args = {'quote': quote, 'exact': exact}
                if speaker:
                    args['speaker'] = speaker
                res = await call(s, 'verify', args)
                assert isinstance(res['verified'], bool)

    for kind in ('books', 'characters', 'speakers', 'records'):
        res = await call(s, 'list_records', {'kind': kind, 'limit': 5})
        assert res['count'] == len(res['rows']) <= 5
        page = await call(s, 'list_records', {'kind': kind, 'limit': 2, 'offset': 2})
        assert page['count'] <= 2
    assert (await call(s, 'stats', {}))['counts']['books'] == 110

    # read tools + pagination
    assert (await call(s, 'book', {'ref': 'a-man-with-no-name', 'limit': 2}))['book']['slug'] == 'book-a-man-with-no-name'
    assert (await call(s, 'book', {'ref': 'a-man-with-no-name', 'limit': 1, 'offset': 1}))['offset'] == 1
    assert len((await call(s, 'book', {'ref': 'a-man-with-no-name', 'limit': 1, 'full': True}))['entries'][0]['body']) <= 4003
    assert (await call(s, 'transcript', {'ref': 'savathuns-spire', 'limit': 2}))['transcript']['slug'] == 'savathuns-spire'
    sp = await call(s, 'transcript', {'ref': 'savathuns-spire', 'speaker': 'Eris Morn', 'limit': 2})
    assert all('Eris' in line['speaker'] for line in sp['lines'])
    assert (await call(s, 'transcript', {'ref': 'savathuns-spire', 'limit': 1, 'offset': 1}))['offset'] == 1
    items = await call(s, 'find_item', {'query': 'nightmask', 'limit': 3})
    assert items['count'] == len(items['rows']) and items['total'] >= items['count']
    assert (await call(s, 'find_item', {'query': 'nightmask', 'limit': 1, 'offset': 1}))['offset'] == 1
    assert (await call(s, 'record', {'ref': 'am-i-to-cast-a-shadow'}))['title']
    vm = await call(s, 'verify_many', {'quotes': ['I am Eris Morn.', 'not canon zzz']})
    assert vm['total'] == 2 and vm['verified'] == 1
    ci = await call(s, 'character_info', {'name': 'eris'})
    assert ci['quotes'] == 262 and 'Eris' in ci['aliases']
    assert (await call(s, 'search', {'query': 'hive', 'limit': 2, 'rank': False}))['count'] == 2


async def parity(s):
    mcp_search = await call(s, 'search', {'query': 'crota', 'limit': 5})
    assert [r['title'] for r in mcp_search['rows']] == [r['title'] for r in api.search('crota', limit=5)]
    mcp_char = await call(s, 'character', {'name': 'eris', 'limit': 3})
    api_char = api.character('eris', limit=3)
    assert mcp_char['header'] == api_char['header']
    assert len(mcp_char['rows']) == len(api_char['rows'])
    assert (await call(s, 'item', {'slug': '0a0x-nightmask'}))['title'] == api.item('0a0x-nightmask')['title']
    mcp_v = await call(s, 'verify', {'quote': 'I am Eris Morn.', 'speaker': 'Eris Morn'})
    api_v = api.verify('I am Eris Morn.', speaker='Eris Morn')
    assert mcp_v['verified'] == api_v['verified']
    assert mcp_v['matches'][0]['slug'] == api_v['matches'][0]['slug']
    assert (await call(s, 'list_records', {'kind': 'speakers', 'limit': 3}))['rows'] == api.listing('speakers', limit=3)
    assert (await call(s, 'stats', {}))['counts'] == api.stats()['counts']


async def errors(s):
    for name, args in (('item', {'slug': 'does-not-exist'}),
                       ('search', {'query': 'x', 'type': 'bogus'}),
                       ('search', {'query': ''}),
                       ('list_records', {'kind': 'bogus'}),
                       ('book', {'ref': 'no-such-book'}),
                       ('transcript', {'ref': 'no-such-transcript'}),
                       ('find_item', {'query': ''}),
                       ('record', {'ref': 'no-such-record'})):
        res = await s.call_tool(name, args)
        text = res.content[0].text if res.content else ''
        assert res.is_error and 'Traceback' not in text, (name, text)
    res = await s.call_tool('verify', {'quote': ''})
    text = res.content[0].text if res.content else ''
    assert res.is_error and 'quote must be 1-2000' in text and 'Traceback' not in text
    for name, args in (('nope', {}), ('search', {})):
        try:
            res = await s.call_tool(name, args)
            text = res.content[0].text if res.content else ''
            assert 'Traceback' not in text
        except Exception as e:
            assert 'Traceback' not in str(e)


async def concurrent():
    async def worker(n):
        async with stdio_client(StdioServerParameters(command=RUN)) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                for i in range(15):
                    if i % 3 == 0:
                        await call(s, 'search', {'query': 'hive', 'limit': 2})
                    elif i % 3 == 1:
                        await call(s, 'verify', {'quote': 'I am Eris Morn.'})
                    else:
                        await call(s, 'stats', {})
    await asyncio.gather(*(worker(i) for i in range(3)))


async def main():
    mtime = os.stat(DB).st_mtime_ns
    async with stdio_client(StdioServerParameters(command=RUN)) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = {t.name for t in (await s.list_tools()).tools}
            report('eighteen tools listed', tools == {'search', 'character', 'character_info',
                                                      'item', 'verify', 'verify_many', 'list_records',
                                                      'stats', 'book', 'transcript', 'find_item', 'record',
                                                      'activities', 'activity', 'seasons', 'events',
                                                      'event', 'coverage'}, str(tools))
            for name, fn in (('tool matrix (80+ calls)', matrix), ('MCP matches API', parity),
                             ('malformed calls fail cleanly', errors)):
                try:
                    await fn(s)
                    report(name, True)
                except Exception as e:
                    report(name, False, f'{type(e).__name__}: {e}')
            try:
                resources = await s.list_resources()
                uris = {str(r.uri) for r in resources.resources}
                assert {'grimoire://books', 'grimoire://characters', 'grimoire://records', 'grimoire://stats'} <= uris, uris
                body = await s.read_resource('grimoire://books')
                assert 'Book' in body.contents[0].text
                book_doc = await s.read_resource('grimoire://book/a-man-with-no-name')
                assert 'Dogma' in book_doc.contents[0].text
                report('resources and templates readable', True)
            except Exception as e:
                report('resources and templates readable', False, f'{type(e).__name__}: {e}')
            try:
                prompts = await s.list_prompts()
                names = {p.name for p in prompts.prompts}
                assert {'quote_safe_lookup', 'character_brief'} <= names, names
                prompt = await s.get_prompt('quote_safe_lookup', {'topic': 'Crota'})
                assert prompt.messages
                report('prompts listed and rendered', True)
            except Exception as e:
                report('prompts listed and rendered', False, f'{type(e).__name__}: {e}')
    try:
        await concurrent()
        report('3 concurrent clients (45 calls)', True)
    except Exception as e:
        report('3 concurrent clients (45 calls)', False, f'{type(e).__name__}: {e}')
    report('database untouched by MCP', os.stat(DB).st_mtime_ns == mtime)
    print(f'\nPassed: {PASS} | Failed: {FAIL} | tool calls: {CALLS}')
    return 0 if FAIL == 0 else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
