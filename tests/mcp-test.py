#!/usr/bin/env python3
"""MCP contract test: tools, read-only guard, limits, and a stdio protocol smoke.

Run with the server venv:  mcp-server/.venv/bin/python tests/mcp-test.py
Exit 0 also when the SDK is absent (SKIP) so the default audit stays dependency-free.
"""
import json
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
SERVER = os.path.join(ROOT, 'mcp-server', 'server.py')
RUN = os.path.join(ROOT, 'mcp-server', 'run.sh')
VENV_PY = os.path.join(ROOT, 'mcp-server', '.venv', 'bin', 'python')

if not os.path.exists(VENV_PY):
    print('SKIP: mcp-server/.venv not installed')
    sys.exit(0)

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


sys.path.insert(0, os.path.join(ROOT, 'mcp-server'))
import server  # noqa: E402


def tools_listed():
    srv = server.server
    tools = srv._tool_manager.list_tools()
    names = {t.name for t in tools}
    want = {'search', 'character', 'item', 'verify', 'list_records', 'stats'}
    assert want <= names, f'missing tools: {want - names}'


def search_works():
    res = server.search('Crota', limit=3)
    assert res['count'] == len(res['rows']) > 0, 'no rows'
    assert all('source' in r and 'title' in r for r in res['rows'])


def verify_works():
    assert server.verify('I am Eris Morn.')['verified'] is True
    assert server.verify('not a canon line at all zzz')['verified'] is False


def limits_clamped():
    res = server.search('hive', limit=10_000)
    assert res['count'] <= 100, f"{res['count']} rows returned"
    assert server.list_records('speakers', limit=10_000)['count'] <= 100


def read_only():
    sys.path.insert(0, os.path.join(ROOT, 'db'))
    import api
    conn = api.connect()
    try:
        conn.execute("UPDATE items SET title = 'x' LIMIT 1")
        raise AssertionError('write succeeded on a read-only connection')
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()


def protocol_smoke():
    proc = subprocess.Popen([RUN], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True, bufsize=1)
    def send(obj):
        proc.stdin.write(json.dumps(obj) + '\n')
        proc.stdin.flush()
    def recv(want_id):
        while True:
            line = proc.stdout.readline()
            if not line:
                raise AssertionError('server closed the stream')
            msg = json.loads(line)
            if msg.get('id') == want_id:
                return msg
    try:
        send({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
              'params': {'protocolVersion': '2025-06-18', 'capabilities': {},
                         'clientInfo': {'name': 'mcp-test', 'version': '0'}}})
        init = recv(1)
        assert 'result' in init, init
        send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        send({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'})
        tools = recv(2)['result']['tools']
        assert len(tools) >= 6, f'{len(tools)} tools'
        send({'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
              'params': {'name': 'verify', 'arguments': {'quote': 'I am Eris Morn.'}}})
        call = recv(3)
        text = json.dumps(call)
        assert 'verified' in text and 'true' in text, call
    finally:
        proc.terminate()


print('MCP contract test')
check('six tools registered', tools_listed)
check('search returns rows', search_works)
check('verify accepts and rejects', verify_works)
check('limit is clamped', limits_clamped)
check('connection is read-only', read_only)
check('stdio protocol smoke', protocol_smoke)

print(f'\nPassed: {PASS} | Failed: {FAIL}')
sys.exit(1 if FAIL else 0)
