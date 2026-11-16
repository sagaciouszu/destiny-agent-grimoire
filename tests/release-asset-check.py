#!/usr/bin/env python3
"""Dynamic release asset-size guard (Q-02).

Compares the documented compressed database sizes (MiB literals in README.md,
STANDARDS.md, docs/wiki/*.md) against actual published release asset bytes,
instead of trusting a stale literal list.

Sources actual bytes from (first available):
  1. --xz-bytes / --gz-bytes flags (CI injection, offline-friendly)
  2. `gh release view` for --tag (default: latest release; needs network/gh)

Fails when any documented literal differs from actual by more than --tolerance
(default 5%). Docs checked are the same prose surfaces users read; the
denylist in docs-consistency.py only blocks superseded values.
"""
import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = ['README.md', 'STANDARDS.md',
        'docs/wiki/Getting-Started.md', 'docs/wiki/Troubleshooting.md']
MIB = 1024 * 1024


def documented():
    found = {}
    for rel in DOCS:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        lines = open(path, encoding='utf-8').read().splitlines()
        direct = re.compile(r'grimoire\.db\.(xz|gz)`?\s*\(?~?([\d.]+)\s*MiB')
        anchor = re.compile(r'grimoire\.db\.(xz|gz)\b')
        windowed = set()
        for i, line in enumerate(lines):
            for m in direct.finditer(line):
                found.setdefault(m.group(1), []).append((rel, float(m.group(2))))
            for a in anchor.finditer(line):
                asset, start = a.group(1), a.start()
                if not direct.match(line, start):
                    key = (rel, asset, i)
                    if key in windowed:
                        continue
                    windowed.add(key)
                    # Shape B (code blocks): a `# NN.N MiB` comment directly
                    # above the download line names that asset's size.
                    prev = ''
                    for j in range(i - 1, max(-1, i - 3), -1):
                        if lines[j].strip():
                            prev = lines[j]
                            break
                    cm = re.match(r'\s*#\s*~?([\d.]+)\s*MiB', prev)
                    if cm:
                        found.setdefault(asset, []).append((rel, float(cm.group(1))))
                        continue
                    # Otherwise take the first size stated after the anchor.
                    after_text = line[start:] + '\n' + '\n'.join(lines[i + 1:i + 3])
                    b = re.search(r'#?\s*~?([\d.]+)\s*MiB', after_text)
                    if b:
                        found.setdefault(asset, []).append((rel, float(b.group(1))))
    # de-duplicate repeated prose (same file/asset/value)
    for key in found:
        seen = set()
        uniq = []
        for rel, val in found[key]:
            if (rel, val) not in seen:
                seen.add((rel, val))
                uniq.append((rel, val))
        found[key] = uniq
    return found


def release_bytes(tag):
    out = subprocess.run(
        ['gh', 'release', 'view', tag, '--json', 'assets',
         '--jq', '.assets[] | "\\(.name) \\(.size)"'],
        capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f'gh release view failed: {out.stderr.strip()}')
    sizes = {}
    for line in out.stdout.splitlines():
        name, size = line.split()
        if name in ('grimoire.db.xz', 'grimoire.db.gz'):
            sizes[name] = int(size)
    if len(sizes) != 2:
        raise RuntimeError(f'expected xz+gz assets on {tag}, got: {sizes}')
    return sizes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tag', default=None,
                    help='release tag (default: latest release)')
    ap.add_argument('--xz-bytes', type=int, default=None)
    ap.add_argument('--gz-bytes', type=int, default=None)
    ap.add_argument('--tolerance', type=float, default=0.05)
    args = ap.parse_args()
    if args.xz_bytes is not None and args.gz_bytes is not None:
        actual = {'grimoire.db.xz': args.xz_bytes,
                  'grimoire.db.gz': args.gz_bytes}
        source = 'flags'
    else:
        tag = args.tag
        if not tag:
            out = subprocess.run(
                ['gh', 'release', 'view', '--json', 'tagName',
                 '--jq', '.tagName'],
                capture_output=True, text=True)
            if out.returncode != 0:
                raise SystemExit(f'cannot resolve latest release: {out.stderr.strip()}')
            tag = out.stdout.strip()
        actual = release_bytes(tag)
        source = f'release {tag}'
    docs = documented()
    if not docs:
        raise SystemExit('no documented MiB literals found')
    failures = []
    print(f'actual ({source}): xz={actual["grimoire.db.xz"]} '
          f'({actual["grimoire.db.xz"]/MIB:.1f} MiB), '
          f'gz={actual["grimoire.db.gz"]} ({actual["grimoire.db.gz"]/MIB:.1f} MiB)')
    for asset, entries in sorted(docs.items()):
        want = actual[f'grimoire.db.{asset}'] / MIB
        for rel, claimed in entries:
            drift = abs(claimed - want) / want
            status = 'OK' if drift <= args.tolerance else 'DRIFT'
            print(f'  [{status}] {rel}: documented {claimed} MiB vs '
                  f'actual {want:.1f} MiB (drift {drift:.1%})')
            if drift > args.tolerance:
                failures.append(f'{rel} {asset}: {claimed} vs {want:.1f}')
    if failures:
        print('FAIL: ' + '; '.join(failures))
        return 1
    print('PASS: documented compressed sizes match published assets')
    return 0


if __name__ == '__main__':
    sys.exit(main())
