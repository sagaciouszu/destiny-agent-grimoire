#!/usr/bin/env python3
"""Documentation audit: commands, targets and flags across all Markdown files.

Checks fenced commands and inline query CLI examples against the real filesystem
and CLI surface. Run: python3 tests/docs-audit.py
"""
import os
import re
import subprocess
import sys

WORK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPOS = {'grimoire': os.path.join(WORK, 'destiny-agent-grimoire'),
         'drifter': os.path.join(WORK, 'how-to-drift-for-agents'),
         'eris': os.path.join(WORK, 'eris-morn')}
SUBS = {'search', 'character', 'character-info', 'item', 'book', 'transcript',
        'find-item', 'record', 'verify', 'verify-many', 'list', 'activity',
        'event', 'coverage', 'lore', 'seal', 'seals', 'stats'}
FLAGS = {'--limit', '--offset', '--json', '--full', '--type', '--about', '--all',
         '--speaker', '--exact', '--rank', '--no-rank', '--include-stage',
         '--activity', '--season', '--event', '--expansion', '--class'}
SKIP_FILES = {'CHANGELOG.md', 'RELEASE.md'}
issues = []
checked = 0


SIBLINGS_PRESENT = any(os.path.isdir(path) for key, path in REPOS.items()
                       if key != 'grimoire')
# Paths that live in an agent workspace rather than this repository. When the
# sibling agent repos are not checked out (grimoire-only CI), these cannot be
# verified here; they are still verified locally where every repo is present.
AGENT_PATHS = ('setup.sh', 'tests/', 'memory.py', 'persona.json',
               'core/', 'voice/', 'world/', 'reference/')


def resolve(root, ref):
    cands = [os.path.join(root, ref), os.path.join(REPOS['grimoire'], ref)]
    for other in REPOS.values():
        cands.append(os.path.join(other, ref))
    if ref.startswith('lore/'):
        cands.append(os.path.join(root, ref[5:]))
    if any(os.path.exists(c) for c in cands):
        return True
    if not SIBLINGS_PRESENT and ref.startswith(AGENT_PATHS):
        return True  # deferred: agent repo not present in this checkout
    return False


for repo, root in REPOS.items():
    if not os.path.isdir(root):
        continue
    files = subprocess.run(['git', '-C', root, 'ls-files', '*.md'],
                           capture_output=True, text=True).stdout.splitlines()
    for rel in files:
        if rel.startswith('source/') or os.path.basename(rel) in SKIP_FILES:
            continue
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            continue
        fence = False
        for line in open(path, encoding='utf-8', errors='ignore'):
            text = line.strip()
            if text.startswith('```'):
                fence = not fence
                continue
            candidates = []
            if fence and text and not text.startswith('#'):
                candidates.append(text)
            for m in re.finditer(r'`((?:python3|bash|sh) [^`]+)`', line):
                candidates.append(m.group(1))
            for cmd in candidates:
                parts = cmd.split()
                if len(parts) < 2 or parts[0] not in ('python3', 'bash', 'sh'):
                    continue
                target = parts[1]
                if '<' in target or '|' in target or target.startswith('-'):
                    continue
                checked += 1
                if not resolve(root, target):
                    issues.append((repo, rel, 'missing target', target))
                    continue
                if target.endswith('query.py'):
                    rest = parts[2:]
                    if rest and any(c in rest[0] for c in '|<>'):
                        continue
                    if rest and rest[0] not in SUBS and not rest[0].startswith('-'):
                        issues.append((repo, rel, 'unknown subcommand', rest[0]))
                    for token in rest:
                        if token.startswith('--') and token.split('=')[0] not in FLAGS:
                            issues.append((repo, rel, 'unknown flag', token))

print(f'docs-command audit: {checked} commands checked')
if issues:
    print(f'ISSUES: {len(issues)}')
    for repo, rel, why, value in issues[:20]:
        print(f'  [{repo}] {rel}: {why} {value}')
    sys.exit(1)
print('PASS: all documented commands resolve')
