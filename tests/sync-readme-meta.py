#!/usr/bin/env python3
"""Stamp README metadata from git: version from the latest tag, last push from HEAD.

Usage: python3 tests/sync-readme-meta.py [--check]
Exit 1 under --check when a README is missing the metadata or is out of date.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
GR = os.path.dirname(HERE)
WORK = os.path.dirname(GR)
sys.path.insert(0, HERE)
import _roster
REPOS = {'grimoire': GR}
REPOS.update(_roster.repos())
META = re.compile(r'\*\*Version:\*\* (\S+) \| \*\*Last push:\*\* (\d{4}-\d{2}-\d{2}) \| \*\*Status:\*\* (\S+)')


def git(repo, *args):
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True,
                          check=True).stdout.strip()


def version_of(repo):
    try:
        return git(repo, 'describe', '--tags', '--abbrev=0').lstrip('v')
    except Exception:
        return None


def last_push(repo):
    try:
        return git(repo, 'log', '-1', '--format=%cs')
    except Exception:
        return None


def main():
    check = '--check' in sys.argv
    bad = []
    for name, repo in REPOS.items():
        if not os.path.isdir(repo):
            continue  # single-repo checkout or CI
        path = os.path.join(repo, 'README.md')
        if not os.path.exists(path):
            bad.append((name, 'README.md missing'))
            continue
        text = open(path, encoding='utf-8').read()
        m = META.search(text)
        want_v, want_d = version_of(repo), last_push(repo)
        if not m:
            bad.append((name, 'metadata line missing'))
            continue
        got_v, got_d, status = m.groups()
        if want_v and got_v != want_v:
            bad.append((name, f'version {got_v} != tag {want_v}'))
        if want_d and got_d != want_d:
            bad.append((name, f'last push {got_d} != HEAD {want_d}'))
        if status != 'Active':
            bad.append((name, f'status {status}'))
        if check:
            continue
        if (want_v and got_v != want_v) or (want_d and got_d != want_d):
            text = META.sub(f'**Version:** {want_v} | **Last push:** {want_d} | **Status:** Active',
                            text, count=1)
            open(path, 'w', encoding='utf-8').write(text)
            print(f'{name}: stamped {want_v} / {want_d}')

    if check:
        if bad:
            for name, why in bad:
                print(f'  [{name}] {why}')
            return 1
        print('README metadata in sync')
        return 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
