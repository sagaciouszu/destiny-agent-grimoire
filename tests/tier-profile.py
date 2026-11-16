#!/usr/bin/env python3
"""32K small-context profile (Q-04): measure what each load tier actually costs.

For every agent repo, resolves the file sets named by the INDEX and AGENTS
tier tables (Minimal, Standard) plus the Deep module set, measures them with
the repo's chars/4 estimator, and compares against the claimed ~XK budgets.
Deep is measured over check-agent-structure modules(); runtime overhead
(system text, tool schemas, history, retrieval output) cannot be measured
statically and is reported as unmeasured reserve.

Report-only: exit 0 always. Use the table to decide whether a compact
persona-instruction target is appropriate; no cap is enforced here.
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

ROW = re.compile(r'\|\s*(Minimal|Standard|Deep)\s*\|([^\n|]*\|)?([^\n]*?~\s*[\d.]+K[^\n]*)')
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
        if tier == 'Minimal' and 'this file' in files:
            refs = [fname] + refs
        claim = CLAIM.search(files)
        tiers[tier] = (refs, float(claim.group(1)) if claim else None)
    return tiers


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
            acc = []
            for tier in ('Minimal', 'Standard'):
                if tier not in tiers:
                    continue
                refs, claim = tiers[tier]
                if tier == 'Standard' and 'Minimal' in tiers:
                    refs = tiers['Minimal'][0] + [r for r in refs
                                                  if r not in tiers['Minimal'][0]]
                vals = [(r, size(ws, r)) for r in refs]
                missing = [r for r, v in vals if v is None]
                total = sum(v for _, v in vals if v is not None)
                drift = (abs(total - claim) / claim) if claim else 0
                worst = max(worst, drift)
                flag = '  <-- MISSING ' + ','.join(missing) if missing else ''
                print(f'{ident:<12} {table[:-3]:<7} {tier:<9} '
                      f'{claim if claim is not None else "?":>8} {total:>8.1f}K '
                      f'{drift:>6.0%}{flag}')
                if tier == 'Standard' and 'Deep' in tiers:
                    _, dclaim = tiers['Deep']
                    ddrift = abs(deep_k - dclaim) / dclaim if dclaim else 0
                    worst = max(worst, ddrift)
                    print(f'{ident:<12} {"INDEX" if table=="INDEX.md" else "AGENTS":<7} '
                          f'{"Deep":<9} {dclaim:>8} {deep_k:>8.1f}K {ddrift:>6.0%}')
    print(f'\nmax drift: {worst:.0%} (gate tolerance elsewhere is 25%; runtime '
          f'overhead unmeasured)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
