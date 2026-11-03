#!/usr/bin/env python3
"""Robustness tests: corrupt inputs, edge cases, concurrency, read-only guarantees.

Run with the system Python (no optional dependencies):
    python3 tests/robustness-test.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.path.join(ROOT, 'db', 'grimoire.db')
sys.path.insert(0, os.path.join(ROOT, 'db'))
import api  # noqa: E402

PASS = FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f'  ✓ {name}')
        PASS += 1
    except Exception as e:
        print(f'  ✗ {name}: {type(e).__name__}: {e}')
        FAIL += 1


def raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return
    raise AssertionError(f'{fn} did not raise {exc}')


def run(cmd, env=None):
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, env=e)


def clean_failure(cmd, env=None):
    r = run(cmd, env=env)
    assert r.returncode != 0, f'exit 0: {cmd}'
    assert 'Traceback' not in (r.stderr + r.stdout), f'traceback: {cmd}'
    assert 'Traceback' not in (r.stderr + r.stdout)


tmp = tempfile.mkdtemp(prefix='grimoire-robust-')
try:
    corrupt = os.path.join(tmp, 'corrupt.db')
    with open(corrupt, 'wb') as fh:
        fh.write(b'this is not a sqlite database')
    truncated = os.path.join(tmp, 'truncated.db')
    with open(DB, 'rb') as src, open(truncated, 'wb') as dst:
        dst.write(src.read(2048))

    print('robustness test')

    def db_failure(path, fn):
        old = os.environ.get('GRIMOIRE_DB')
        os.environ['GRIMOIRE_DB'] = path
        try:
            raises(fn, (ValueError, FileNotFoundError))
        finally:
            if old is None:
                os.environ.pop('GRIMOIRE_DB', None)
            else:
                os.environ['GRIMOIRE_DB'] = old

    check('missing database raises cleanly',
          lambda: db_failure(os.path.join(tmp, 'missing.db'), lambda: api.stats()))
    check('corrupt database raises cleanly',
          lambda: db_failure(corrupt, lambda: api.stats()))
    check('truncated database raises cleanly',
          lambda: db_failure(truncated, lambda: api.search('crota')))

    check('empty query rejected', lambda: raises(lambda: api.search('')))
    check('long query rejected', lambda: raises(lambda: api.search('a' * 501)))
    check('injection text searched literally', lambda: isinstance(api.search("'; DROP TABLE items; --"), list))
    check('long quote rejected', lambda: raises(lambda: api.verify('x' * 2001)))
    check('empty quote rejected', lambda: raises(lambda: api.verify('')))
    check('unicode query works', lambda: api.search('savathûn', limit=2) is not None)
    check('limit 0 clamps to 1', lambda: len(api.listing('speakers', limit=0)) == 1)
    check('negative limit clamps to 1', lambda: len(api.listing('speakers', limit=-5)) == 1)
    check('huge limit is bounded', lambda: len(api.listing('speakers', limit=10**9)) <= 10000)
    check('missing item returns None', lambda: api.item('definitely-not-an-item') is None)
    check('missing character returns None', lambda: api.character('Nobody At All') is None)
    check('verify hit', lambda: api.verify('I am Eris Morn.')['verified'] is True)
    check('verify miss', lambda: api.verify('not canon at all zzz')['verified'] is False)
    check('verify wrong speaker rejected',
          lambda: api.verify('I am Eris Morn.', speaker='Zavala')['verified'] is False)
    check('verify fragment is not exact',
          lambda: api.verify('Eris Mor', exact=True)['verified'] is False)
    check('verify exact line', lambda: api.verify('Absolutely not.', exact=True)['verified'] is True)
    check('path traversal slug is just a miss', lambda: api.item('../../etc/passwd') is None)

    def read_only():
        conn = api.connect()
        try:
            raises(lambda: conn.execute("UPDATE items SET title='x' LIMIT 1"), Exception)
        finally:
            conn.close()

    check('connection is read-only', read_only)

    def concurrency():
        work = [('search', 'hive'), ('character', 'eris'), ('verify', 'I am Eris Morn.'),
                ('item', '0a0x-nightmask'), ('stats', None), ('listing', 'speakers')]
        def one(i):
            name, arg = work[i % len(work)]
            if name == 'search':
                return api.search(arg, limit=3)
            if name == 'character':
                return api.character(arg, limit=3)
            if name == 'verify':
                return api.verify(arg)
            if name == 'item':
                return api.item(arg)
            if name == 'stats':
                return api.stats()
            return api.listing(arg, limit=3)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(one, range(160)))
        assert len(results) == 160

    check('concurrent queries (160, 8 threads)', concurrency)

    def cli_errors():
        cases = [
            'db/query.py search ""',
            'db/query.py search "' + 'a' * 501 + '"',
            'db/query.py item nope-nope',
            'db/query.py character "Nobody Here"',
            'db/query.py verify ""',
            'db/query.py verify "' + 'x' * 2100 + '"',
        ]
        for c in cases:
            clean_failure(f'python3 {c}', env={'GRIMOIRE_DB': DB})
        for path in (os.path.join(tmp, 'missing.db'), corrupt, truncated):
            clean_failure('python3 db/query.py stats', env={'GRIMOIRE_DB': path})

    check('CLI fails without tracebacks', cli_errors)

    def injection_is_clean():
        r = run('python3 db/query.py search "\'; DROP TABLE items; --"',
                env={'GRIMOIRE_DB': DB})
        assert r.returncode in (0, 1), r.returncode
        assert 'Traceback' not in r.stderr

    check('injection attempts never traceback', injection_is_clean)

    def json_outputs():
        for c in ('search hive --limit 2', 'character eris --limit 2',
                  'item 0a0x-nightmask', 'verify "I am Eris Morn."',
                  'list books --limit 2', 'stats', 'verify "not canon zzz"'):
            r = run(f'python3 db/query.py {c} --json', env={'GRIMOIRE_DB': DB})
            json.loads(r.stdout or '{}')

    check('every command emits valid JSON', json_outputs)

    def no_data_loss():
        items = api.stats()['counts']['items']
        try:
            api.search("'; DROP TABLE items; --")
        except ValueError:
            pass
        assert api.stats()['counts']['items'] == items

    check('injection attempt leaves data intact', no_data_loss)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f'\nPassed: {PASS} | Failed: {FAIL}')
sys.exit(1 if FAIL else 0)
