#!/usr/bin/env python3
"""CI helper checks for the Drifter agent system."""
import glob, os, re, sys

def get_files(ws):
    files = []
    for root, _, fs in os.walk(ws):
        for f in fs:
            if f.endswith('.md'):
                files.append(os.path.join(root, f))
    return [f for f in files if 'DREAMS.md' not in f]

def check_stale(ws):
    old_names = ['drifter-brain.md','drifter-quick-ref.md','drifter-master.md','drifter-relationships.md',
                 'drifter-arcs.md','drifter-what-not-to-do.md','drifter-lore.md','core/relationship-web.md',
                 'core/timeline.md','core/examples.md','core/state-machine.md','core/response-cache.md',
                 'core/unreliable-narrator.md','world/items.md','world/gambit.md','world/crew.md',
                 'world/derelict.md','gameplay/terms.md']
    files = get_files(ws)
    for f in files:
        s = open(f, encoding='utf-8').read()
        for old in old_names:
            if old in s:
                print("STALE: %s in %s" % (old, f))
                sys.exit(1)
    print("OK: No stale references")
    sys.exit(0)

def check_circular(ws):
    files = get_files(ws)
    deps = {}
    for f in files:
        s = open(f, encoding='utf-8').read()
        m = re.search(r'Depends On:\*\* (.+)', s)
        if m:
            deps[f] = [d.strip().strip('`') for d in m.group(1).split(',')]
        else:
            deps[f] = []
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {f: WHITE for f in files}
    cycle = [None]
    def dfs(node):
        color[node] = GRAY
        for dep in deps.get(node, []):
            if dep in deps:
                if color.get(dep, WHITE) == GRAY:
                    cycle[0] = (node, dep)
                    return True
                if color.get(dep, WHITE) == WHITE and dfs(dep):
                    return True
        color[node] = BLACK
        return False
    for f in files:
        if color[f] == WHITE and dfs(f):
            break
    if cycle[0]:
        print("CYCLE: %s" % str(cycle[0]))
        sys.exit(1)
    print("OK: No circular dependencies")
    sys.exit(0)

def check_selfdeps(ws):
    files = get_files(ws)
    for f in files:
        s = open(f, encoding='utf-8').read()
        m = re.search(r'Depends On:\*\* (.+)', s)
        if m:
            deps = [d.strip().strip('`') for d in m.group(1).split(',')]
            if f in deps or os.path.basename(f) in deps:
                print("SELF-DEP: %s" % f)
                sys.exit(1)
    print("OK: No self-dependencies")
    sys.exit(0)

def check_emdashes(ws):
    files = get_files(ws)
    skip = ('/books/', '/transcripts/', '/destiny-1/cards/')
    for f in files:
        if any(seg in f.replace(os.sep, '/') for seg in skip):
            continue
        s = open(f, encoding='utf-8').read()
        if '—' in s or '–' in s:
            print("EM-DASH: %s" % f)
            sys.exit(1)
    print("OK: No em/en-dashes")
    sys.exit(0)

def check_personal(ws):
    files = get_files(ws)
    for f in files:
        s = open(f, encoding='utf-8').read()
        if '/home/sredshaw' in s:
            print("PERSONAL PATH: %s" % f)
            sys.exit(1)
    print("OK: No personal paths")
    sys.exit(0)

def check_gitignored(ws):
    candidates = ['INDEX.md', 'index.md', 'README.md', 'AGENTS.md', 'TOOLS.md']
    for f in candidates:
        path = os.path.join(ws, f)
        if not os.path.exists(path): continue
        s = open(path, encoding='utf-8').read()
        if 'memory/' in s or 'DREAMS.md' in s:
            print("GITIGNORED REF: %s" % f)
            sys.exit(1)
    print("OK: No gitignored refs in instructions")
    sys.exit(0)

def check_headers(ws):
    files = get_files(ws)
    # Headers required only for agent-facing modules (compendium/); lore source and
    # index files are exempt.
    for f in files:
        rel = f.replace(os.sep, '/')
        if '/books/' in rel or '/transcripts/' in rel or '/destiny-1/' in rel or '/skills/' in rel or '/items/' in rel or '/records/' in rel or '/interactions/' in rel:
            continue
        if rel.endswith('/index.md') or rel.endswith('/README.md') or rel.endswith('CHANGELOG.md') or rel.endswith('SKILL.md'):
            continue
        s = open(f, encoding='utf-8').read()
        if '**Depends On:**' not in s or 'Token Estimate:' not in s:
            print("MISSING HEADER: %s" % f)
            sys.exit(1)
    print("OK: All headers present")
    sys.exit(0)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: ci-checks.py <check> <workspace>")
        sys.exit(1)
    check_name = sys.argv[1]
    ws = sys.argv[2]
    checks = {
        'stale': check_stale,
        'circular': check_circular,
        'selfdeps': check_selfdeps,
        'emdashes': check_emdashes,
        'personal': check_personal,
        'gitignored': check_gitignored,
        'headers': check_headers,
    }
    if check_name in checks:
        checks[check_name](ws)
    else:
        print("Unknown check: %s" % check_name)
        sys.exit(1)
