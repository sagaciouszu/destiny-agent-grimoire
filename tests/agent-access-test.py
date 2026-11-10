#!/usr/bin/env python3
"""Agent access contract: setup, missing database, broken link, read-only DB.

Registry-driven. For every present agent repository:
  - setup.sh parses and offers --help;
  - --dry-run detects a dangling lore/ link and changes nothing;
  - connection-test fails clearly when the database is absent;
  - the published database opens read-only (a write is rejected);
  - the query CLI answers stats.

Read-only; no network. Skips absent repositories.
"""
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import _roster  # noqa: E402

DB = os.environ.get('GRIMOIRE_DB') or os.path.join(ROOT, 'db', 'grimoire.db')
PASS = FAIL = 0


def check(name, ok, detail=''):
    global PASS, FAIL
    if ok:
        print(f'  ✓ {name}')
        PASS += 1
    else:
        print(f'  ✗ {name}' + (f': {detail}' if detail else ''))
        FAIL += 1


def run(args, env=None):
    return subprocess.run(args, capture_output=True, text=True, env=env)


def main():
    if not os.path.isfile(DB):
        print('SKIP: database missing')
        return 0
    repos = _roster.present()
    if not repos:
        print('SKIP: no agent repositories present')
        return 0

    for ident, repo in sorted(repos.items()):
        setup = os.path.join(repo, 'setup.sh')
        print(f'{ident}:')
        check('setup.sh present', os.path.isfile(setup))
        if not os.path.isfile(setup):
            continue
        check('setup.sh syntax', run(['bash', '-n', setup]).returncode == 0)
        helped = run(['bash', setup, '--help'])
        check('setup --help', helped.returncode == 0 and 'usage' in helped.stdout,
              helped.stderr.strip())

        tmp = tempfile.mkdtemp(prefix=f'access-{ident}-')
        try:
            copy = os.path.join(tmp, 'setup.sh')
            shutil.copy2(setup, copy)
            os.symlink('/nonexistent/grimoire', os.path.join(tmp, 'lore'))
            plan = run(['bash', copy, '--dry-run', ROOT])
            text = plan.stdout + plan.stderr
            check('dry-run detects a dangling lore link',
                  plan.returncode == 0 and 'dangling' in text.lower(), text[-300:])
            check('dry-run changes nothing',
                  not os.path.exists(os.path.join(tmp, 'lore', 'db')) or
                  os.path.islink(os.path.join(tmp, 'lore')), text[-300:])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

        empty = tempfile.mkdtemp(prefix=f'access-empty-{ident}-')
        try:
            env = dict(os.environ, LORE=empty, WORKSPACE=repo)
            broken = run(['bash', os.path.join(repo, 'tests', 'connection-test.sh')], env)
            text = broken.stdout + broken.stderr
            check('missing database fails clearly',
                  broken.returncode != 0 and 'database present' in text, text[-300:])
        finally:
            shutil.rmtree(empty, ignore_errors=True)

        # The agent's own mounted archive: same database, same query surface.
        lore = os.path.join(repo, 'lore')
        lore_db = os.path.join(lore, 'db', 'grimoire.db')
        has_lore = os.path.isfile(lore_db)
        check('lore database present', has_lore)
        if has_lore:
            def digest(path):
                h = hashlib.sha256()
                with open(path, 'rb') as fh:
                    for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b''):
                        h.update(chunk)
                return h.hexdigest()
            check('lore database matches the archive',
                  digest(lore_db) == digest(DB))
            query = os.path.join(lore, 'db', 'query.py')
            check('agent query interface',
                  run([sys.executable, query, 'stats']).returncode == 0)
            persona_path = os.path.join(repo, 'persona.json')
            speaker = None
            if os.path.isfile(persona_path):
                import json as _json
                speaker = _json.load(open(persona_path, encoding='utf-8')).get('speaker')
            if speaker:
                check('persona speaker resolves',
                      run([sys.executable, query, 'character-info', speaker]).returncode == 0)
                check('persona freshness',
                      run([sys.executable, os.path.join(repo, 'tests', 'persona-freshness.py'),
                           persona_path, lore_db]).returncode == 0)
            check('lore lookup',
                  run([sys.executable, query, 'lore', "Gate Lord's Eye"]).returncode == 0)
            check('seal lookup',
                  run([sys.executable, query, 'seal', 'Conqueror']).returncode == 0)
            check('MCP launcher',
                  os.access(os.path.join(lore, 'mcp-server', 'run.sh'), os.X_OK))

    # Read-only and CLI surface are archive-level, checked once.
    try:
        conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
        try:
            conn.execute('CREATE TABLE access_write_probe (x)')
            check('database rejects writes', False, 'write succeeded')
        except sqlite3.OperationalError:
            check('database rejects writes', True)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        check('database rejects writes', False, str(exc))
    stats = run([sys.executable, os.path.join(ROOT, 'db', 'query.py'), 'stats'])
    check('query CLI stats', stats.returncode == 0 and 'transcripts' in stats.stdout,
          stats.stderr.strip())

    # Old databases must degrade, not crash: stats reports missing tables.
    old_db = tempfile.mktemp(suffix='.db')
    sqlite3.connect(old_db).close()
    try:
        env = dict(os.environ, GRIMOIRE_DB=old_db)
        probe = run([sys.executable, '-c',
                     'import json, db.api as a; print(json.dumps(a.stats()))'],
                    env=env)
        check('old database stats report missing tables',
              probe.returncode == 0 and 'caption_sightings' in probe.stdout
              and 'missing_tables' in probe.stdout, probe.stderr.strip())
    finally:
        os.remove(old_db)

    # The public roster is published data; it must be the same registry, not a
    # second hand-maintained list.
    site = os.path.join(os.path.dirname(ROOT), 'destiny-agent-grimoire-site',
                        '_data', 'agents.js')
    if os.path.isfile(site):
        text = open(site, encoding='utf-8').read()
        site_ids = set(re.findall(r'^\s*id:\s*"([^"]+)"', text, re.M))
        registry = set(_roster.repos())
        check('site roster matches the registry', site_ids == registry,
              f'site={sorted(site_ids)} registry={sorted(registry)}')

    print(f'\nPassed: {PASS} | Failed: {FAIL}')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main())
