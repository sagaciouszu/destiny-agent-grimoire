#!/usr/bin/env python3
"""Check external URLs in the READMEs (badges, links). On-demand, network required.

Usage: python3 tests/link-check.py [--all]
Exit 1 when a URL fails. Badge URLs are skipped unless --all (shields rate limits).
"""
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
GR = os.path.dirname(HERE)
WORK = os.path.dirname(GR)
READMES = [os.path.join(GR, 'README.md'),
           os.path.join(WORK, 'how-to-drift-for-agents', 'README.md'),
           os.path.join(WORK, 'eris-morn', 'README.md')]
URL = re.compile(r'https?://[^\s\'"<>)]+')


def main():
    check_badges = '--all' in sys.argv
    bad, checked = [], 0
    for path in READMES:
        if not os.path.exists(path):
            continue
        for url in sorted(set(URL.findall(open(path, encoding='utf-8').read()))):
            url = url.rstrip('.,;')
            host = urllib.parse.urlsplit(url).netloc
            if host == 'img.shields.io' and not check_badges:
                continue
            checked += 1
            try:
                req = urllib.request.Request(url, method='HEAD',
                                             headers={'User-Agent': 'grimoire-link-check'})
                with urllib.request.urlopen(req, timeout=20) as r:
                    if r.status >= 400:
                        bad.append((os.path.basename(path), url, r.status))
            except urllib.error.HTTPError as e:
                if e.code == 404 and urllib.parse.urlsplit(url).netloc == 'github.com':
                    # private repository: unauthenticated HEAD reports 404
                    parts = urllib.parse.urlsplit(url).path.strip('/').split('/')
                    repo = [q.removesuffix('.git') for q in parts[:2]]
                    gh = subprocess.run(['gh', 'repo', 'view', '/'.join(repo),
                                         '--json', 'name'], capture_output=True, text=True)
                    if gh.returncode == 0:
                        continue
                if e.code >= 400:
                    bad.append((os.path.basename(path), url, e.code))
            except Exception as e:
                bad.append((os.path.basename(path), url, type(e).__name__))
    print(f'urls checked: {checked} | failures: {len(bad)}')
    for f, u, why in bad:
        print(f'  {f}: {why} {u}')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
