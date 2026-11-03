#!/usr/bin/env python3
"""Structural checks shared by both agent workspaces.

Usage: check-agent-structure.py <deps|tokens|dashes|index|paths> <workspace>
Exit 1 on violations; prints the offending files.
"""
import glob
import os
import re
import sys

RUNTIME = ('user-memory.md', 'journal.md', 'session-state.md',
           'cross-session-memory.md', 'DREAMS.md')
SKIP_MODULES = ('README.md', 'RELEASE.md', 'CHANGELOG.md') + RUNTIME


def modules(ws):
    files = [f for d in ('', 'voice', 'core', 'world', 'reference')
             for f in glob.glob(os.path.join(ws, d, '*.md'))]
    return [f for f in files if os.path.basename(f) not in RUNTIME]


def resolve(ws, from_file, dep):
    dep = dep.strip().strip('`')
    if not dep or dep.lower().startswith('none'):
        return True
    for cand in (dep, dep[:-3] + '.template.md' if dep.endswith('.md') else dep):
        if os.path.exists(os.path.join(ws, cand)):
            return True
        if os.path.exists(os.path.join(os.path.dirname(from_file), cand)):
            return True
    return False


def main():
    cmd, ws = sys.argv[1], sys.argv[2]
    files = modules(ws)
    bad = []

    if cmd == 'deps':
        for f in files:
            text = open(f, encoding='utf-8').read()
            m = re.search(r'\*\*Depends On:\*\*\s*(.+)', text)
            if not m:
                bad.append((f, 'no Depends On header'))
                continue
            for dep in m.group(1).split(','):
                if not resolve(ws, f, dep):
                    bad.append((f, f'unresolved dependency {dep.strip()}'))
    elif cmd == 'tokens':
        for f in files:
            if 'Token Estimate:' not in open(f, encoding='utf-8').read():
                bad.append((f, 'no Token Estimate header'))
        # load-tier claims in INDEX.md must match measured sizes (25% tolerance)
        idx_path = os.path.join(ws, 'INDEX.md')
        if os.path.exists(idx_path):
            idx_text = open(idx_path, encoding='utf-8').read()
            core = os.path.basename(glob.glob(os.path.join(ws, '*-core.md'))[0])
            def size(rel):
                p = os.path.join(ws, rel)
                return len(open(p, encoding='utf-8').read()) / 4 / 1000 if os.path.exists(p) else None
            minimal = size(core)
            voice_core = 'voice/' + core.replace('-core.md', '-voice-core.md')
            standard = (minimal + (size(voice_core) or 0) + (size('core/relationships.md') or 0))
            deep = sum(len(open(f, encoding='utf-8').read()) / 4 / 1000 for f in files)
            for tier, actual in (('Minimal', minimal), ('Standard', standard), ('Deep', deep)):
                m = re.search(rf'\| {tier} \|[^\n]*?~([\d.]+)K', idx_text)
                if not m:
                    bad.append((idx_path, f'{tier} tier claim missing'))
                    continue
                claimed = float(m.group(1))
                if actual and abs(actual - claimed) / claimed > 0.25:
                    bad.append((idx_path, f'{tier} tier ~{claimed}K vs measured ~{actual:.1f}K'))
    elif cmd == 'dashes':
        for f in files:
            text = open(f, encoding='utf-8').read()
            if '\u2014' in text or '\u2013' in text:
                bad.append((f, 'em/en dash'))
    elif cmd == 'index':
        idx = open(os.path.join(ws, 'INDEX.md'), encoding='utf-8').read()
        for ref in set(re.findall(r'`([A-Za-z0-9_./-]+\.md)`', idx)):
            if not os.path.exists(os.path.join(ws, ref)):
                bad.append(('INDEX.md', f'broken ref {ref}'))
        for f in files:
            rel = os.path.relpath(f, ws)
            if os.path.basename(rel) in SKIP_MODULES:
                continue
            if os.path.basename(rel) not in idx:
                bad.append((rel, 'not listed in INDEX.md'))
    elif cmd == 'paths':
        pat = re.compile(r'/home/[a-z0-9._-]+/|/Users/[a-z0-9._-]+/', re.I)
        for f in glob.glob(os.path.join(ws, '**', '*.*'), recursive=True):
            if not f.endswith(('.md', '.sh', '.py')) or '/lore/' in f or '/.git/' in f:
                continue
            if pat.search(open(f, encoding='utf-8', errors='ignore').read()):
                bad.append((os.path.relpath(f, ws), 'personal path'))
    else:
        print(f'unknown check: {cmd}', file=sys.stderr)
        return 2

    if bad:
        print(f'{cmd}: {len(bad)} issue(s)')
        for f, why in bad[:20]:
            print(f'  {os.path.relpath(f, ws) if f.startswith(ws) else f}: {why}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
