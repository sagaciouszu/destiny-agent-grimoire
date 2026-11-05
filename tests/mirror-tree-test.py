#!/usr/bin/env python3
"""Verify scripts/mirror-tree.py (the rsync replacement used by agent sync)."""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
MIRROR = os.path.join(ROOT, 'scripts', 'mirror-tree.py')

EXCLUDES = ['--exclude', '.git', '--exclude', 'USER.md', '--exclude',
            'memory/', '--exclude', 'core/journal.md']

PASS = FAIL = 0


def check(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f'  ✓ {name}')
        PASS += 1
    except Exception as exc:  # noqa: BLE001
        print(f'  ✗ {name}: {exc}')
        FAIL += 1


def run(*args):
    return subprocess.run([sys.executable, MIRROR, *args],
                          capture_output=True, text=True)


def build_trees(root):
    src = os.path.join(root, 'src')
    dst = os.path.join(root, 'dst')
    for rel in ('agent.md', 'core/voice.md', 'core/journal.md', 'memory/notes.md',
                '.git/config'):
        path = os.path.join(src, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(f'source {rel}\n')
    for rel in ('agent.md', 'stale.md', 'USER.md', 'memory/local.md',
                'core/journal.md'):
        path = os.path.join(dst, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(f'dest {rel}\n')
    # Read-only file: Windows marks files read-only; deletion must clear it.
    stale_ro = os.path.join(dst, 'read-only-stale.md')
    with open(stale_ro, 'w', encoding='utf-8') as fh:
        fh.write('ro\n')
    os.chmod(stale_ro, 0o444)
    return src, dst


def main():
    tmp = tempfile.mkdtemp(prefix='mirror-tree-')
    try:
        src, dst = build_trees(tmp)

        def mirrors():
            result = run('--delete', *EXCLUDES, src, dst)
            assert result.returncode == 0, result.stderr

        check('mirror copies, deletes and respects excludes', mirrors)
        check('source file copied',
              lambda: (_ for _ in ()).throw(AssertionError('agent.md not updated'))
              if open(os.path.join(dst, 'agent.md')).read() != 'source agent.md\n' else None)
        check('stale file removed',
              lambda: (_ for _ in ()).throw(AssertionError('stale.md kept'))
              if os.path.exists(os.path.join(dst, 'stale.md')) else None)
        check('read-only stale file removed',
              lambda: (_ for _ in ()).throw(AssertionError('read-only-stale.md kept'))
              if os.path.exists(os.path.join(dst, 'read-only-stale.md')) else None)
        check('excluded USER.md preserved',
              lambda: (_ for _ in ()).throw(AssertionError('USER.md deleted'))
              if not os.path.exists(os.path.join(dst, 'USER.md')) else None)
        check('excluded memory preserved',
              lambda: (_ for _ in ()).throw(AssertionError('memory/local.md deleted'))
              if not os.path.exists(os.path.join(dst, 'memory', 'local.md')) else None)
        check('excluded .git not mirrored',
              lambda: (_ for _ in ()).throw(AssertionError('.git mirrored'))
              if os.path.exists(os.path.join(dst, '.git')) else None)

        # Dry run must change nothing.
        with open(os.path.join(src, 'agent.md'), 'w', encoding='utf-8') as fh:
            fh.write('changed\n')
        dry = run('--delete', '--dry-run', *EXCLUDES, src, dst)
        check('dry run exits 0',
              lambda: (_ for _ in ()).throw(AssertionError(dry.stderr))
              if dry.returncode != 0 else None)
        check('dry run changes nothing',
              lambda: (_ for _ in ()).throw(AssertionError('dry run copied'))
              if open(os.path.join(dst, 'agent.md')).read() != 'source agent.md\n' else None)

        print(f'\nPassed: {PASS} | Failed: {FAIL}')
        return 1 if FAIL else 0
    finally:
        for root, dirs, files in os.walk(tmp, topdown=False):
            for name in files:
                try:
                    os.chmod(os.path.join(root, name), 0o644)
                except OSError:
                    pass
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
