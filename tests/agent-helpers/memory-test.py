#!/usr/bin/env python3
"""Verify per-user memory isolation and hashing."""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HELPER = os.path.join(REPO, 'memory.py')
PY = sys.executable


def run(root, *args, text=None):
    return subprocess.run([PY, HELPER, *args], input=text,
                          capture_output=True, text=True,
                          env=dict(os.environ, MEMORY_ROOT=root))


def main():
    root = tempfile.mkdtemp(prefix='memory-test-')
    a, b = 'platform-user-aaaa', 'platform-user-bbbb'
    assert run(root, 'set', '--user', a, text='alpha note').returncode == 0
    assert run(root, 'get', '--user', a).stdout.strip() == 'alpha note'
    assert run(root, 'get', '--user', b).stdout.strip() == ''
    assert run(root, 'set', '--user', b, text='beta note').returncode == 0
    assert run(root, 'get', '--user', a).stdout.strip() == 'alpha note'
    assert run(root, 'get', '--user', b).stdout.strip() == 'beta note'

    users = os.path.join(root, 'users')
    files = sorted(os.listdir(users))
    assert len(files) == 2, files
    for name in files:
        stem = os.path.splitext(name)[0]
        assert len(stem) == 32 and all(c in '0123456789abcdef' for c in stem), name
        assert a not in name and b not in name
        assert oct(os.stat(os.path.join(users, name)).st_mode & 0o777) == '0o600'
    assert oct(os.stat(os.path.join(root, '.salt')).st_mode & 0o777) == '0o600'

    assert run(root, 'prefs-set', '--user', a, '--class', 'hunter').returncode == 0
    assert run(root, 'prefs-get', '--user', a).stdout.strip() == '{\n  "class": "hunter"\n}'
    assert run(root, 'prefs-get', '--user', b).stdout.strip() == '{}'
    assert run(root, 'prefs-set', '--user', b, '--class', 'warlock').returncode == 0
    assert run(root, 'prefs-set', '--user', b, '--class', 'rogue').returncode != 0
    prefs = os.path.join(root, 'prefs')
    assert len(os.listdir(prefs)) == 2, os.listdir(prefs)
    for name in os.listdir(prefs):
        assert oct(os.stat(os.path.join(prefs, name)).st_mode & 0o777) == '0o600'

    assert run(root, 'forget', '--user', a).returncode == 0
    assert run(root, 'prefs-get', '--user', a).stdout.strip() == '{}'
    assert run(root, 'get', '--user', a).stdout.strip() == ''
    assert run(root, 'get', '--user', b).stdout.strip() == 'beta note'

    assert run(root, 'set', '--user', a, text='x' * 9000).returncode != 0
    assert run(root, 'get', '--user', 'bad\nuser').returncode != 0

    procs = [subprocess.Popen([PY, HELPER, 'set', '--user', f'parallel-{i}',
                               '--text', f'note-{i}'],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              env=dict(os.environ, MEMORY_ROOT=root))
             for i in range(6)]
    assert all(p.wait() == 0 for p in procs)
    for i in range(6):
        assert run(root, 'get', '--user', f'parallel-{i}').stdout.strip() == f'note-{i}'
    print('memory isolation: hashed, scoped, forgettable, concurrent')
    return 0


if __name__ == '__main__':
    sys.exit(main())
