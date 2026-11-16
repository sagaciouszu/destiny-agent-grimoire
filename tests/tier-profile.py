#!/usr/bin/env python3
"""32K small-context profile (Q-04): measure what each load tier actually costs.

For every agent repo, resolves the always-loaded Core file set named by the
INDEX and AGENTS tier tables, and reports the Deep module total as an
ungated reference. Uses the repo's chars/4 estimator. Runtime overhead
(system text, tool schemas, history, retrieval output) cannot be measured
statically and is reported as unmeasured reserve. Flags (not fails) Core sets
above MONITOR_K.

Report-only: exit 0 always.
"""
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.dirname(ROOT)
sys.path.insert(0, HERE)
import _roster

ROW = re.compile(r'\|\s*(Core|Task-loaded)\s*\|([^\n|]*\|)?([^\n]*?~\s*[\d.]+K[^\n]*)')
REFS = re.compile(r'`([^`]+)`')
CLAIM = re.compile(r'~([\d.]+)K')


def files_of(ws):
    out = [f for d in ('', 'voice', 'core', 'world', 'reference')
           for f in glob.glob(os.path.join(ws, d, '*.md'))]
    base = {os.path.basename(f) for f in out}
    # WS13: project docs are not modules and never load as persona context.
    return [f for f in out if os.path.basename(f) not in
            ('USER.md', 'user-memory.md', 'journal.md', 'session-state.md',
             'cross-session-memory.md', 'DREAMS.md', 'README.md',
             'RELEASE.md', 'CHANGELOG.md')]


def size(ws, rel):
    p = os.path.join(ws, rel.strip().strip('`'))
    if os.path.isdir(p) or not os.path.exists(p):
        return None
    return len(open(p, encoding='utf-8').read()) / 4 / 1000


def parse_tier(ws, fname):
    path = os.path.join(ws, fname)
    if not os.path.isfile(path):
        return {}
    text = open(path, encoding='utf-8').read()
    tiers = {}
    for m in ROW.finditer(text):
        tier, files = m.group(1), (m.group(2) or '') + ' ' + m.group(3)
        refs = [r for r in REFS.findall(files) if r.endswith('.md')]
        if tier == 'Core' and 'this file' in files:
            refs = [fname] + refs
        claim = CLAIM.search(files)
        tiers[tier] = (refs, float(claim.group(1)) if claim else None)
    return tiers


MONITOR_K = 8.0  # Q-04: flag (don't fail) always-loaded sets above this


def main():
    print(f'{"agent":<12} {"table":<7} {"tier":<9} {"claimed":>8} {"measured":>9} {"drift":>7}  files')
    worst = 0
    for ident, repo in sorted(_roster.repos().items()):
        ws = os.path.join(WORK, repo)
        if not os.path.isdir(ws):
            continue
        deep_files = files_of(ws)
        deep_k = sum(size(ws, os.path.relpath(f, ws)) or 0 for f in deep_files)
        for table in ('INDEX.md', 'AGENTS.md'):
            tiers = parse_tier(ws, table)
            if 'Core' not in tiers:
                print(f'{ident:<12} {table[:-3]:<7} {"Core":<9} {"?":>8} {"?":>8} {"":>6}  <-- no Core row')
                continue
            refs, claim = tiers['Core']
            vals = [(r, size(ws, r)) for r in refs]
            missing = [r for r, v in vals if v is None]
            total = sum(v for _, v in vals if v is not None)
            drift = (abs(total - claim) / claim) if claim else 0
            worst = max(worst, drift)
            flag = '  <-- MISSING ' + ','.join(missing) if missing else ''
            if total > MONITOR_K:
                flag += f'  <-- MONITOR: above {MONITOR_K:.0f}K reference'
            print(f'{ident:<12} {table[:-3]:<7} {"Core":<9} '
                  f'{claim if claim is not None else "?":>8} {total:>8.1f}K '
                  f'{drift:>6.0%}{flag}')
            _, dclaim = tiers.get('Task-loaded', (None, None))
            print(f'{ident:<12} {"INDEX" if table=="INDEX.md" else "AGENTS":<7} '
                  f'{"task-loaded":<9} {dclaim if dclaim is not None else "?":>8} '
                  f'{deep_k:>8.1f}K (ref, ungated)')
    print(f'\nmax Core drift: {worst:.0%} (gate tolerance is 25%; Deep/task-loaded '
          f'is reference only; runtime overhead unmeasured)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
