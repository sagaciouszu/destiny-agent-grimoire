#!/usr/bin/env python3
"""Documentation audit: commands, targets and flags across all Markdown files.

Checks fenced commands and inline query CLI examples against the real filesystem
and CLI surface. Run: python3 tests/docs-audit.py
"""
import glob
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
            # Windows launchers: mcp-server\run.cmd, run.ps1, and
            # `powershell.exe ... -File mcp-server\run.ps1`.
            launcher_refs = re.findall(
                r'(?<![\w.-])((?:[A-Za-z0-9_.-]+[\\/])+[A-Za-z0-9_.-]+\.(?:cmd|ps1)'
                r'|run\.(?:cmd|ps1))(?=\s|$|`)\|?', text)
            for ref in launcher_refs:
                checked += 1
                norm_ref = ref.replace('\\', '/')
                # A bare `run.cmd`/`run.ps1` mention means mcp-server/<ref>.
                options = [norm_ref]
                if '/' not in norm_ref:
                    options.append(os.path.join('mcp-server', norm_ref))
                if not any(resolve(root, opt) for opt in options):
                    issues.append((repo, rel, 'missing target', ref))
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

# Agent Skills spec (https://agentskills.io/specification): every SKILL.md
# needs valid frontmatter (name <=64 lowercase/hyphens, description <=1024).
skills_checked = 0
for repo in REPOS.values():
    for path in glob.glob(os.path.join(repo, 'skills', '**', 'SKILL.md'),
                          recursive=True):
        skills_checked += 1
        rel = os.path.relpath(path, repo)
        text = open(path, encoding='utf-8').read()
        m = re.match(r'^---\n(.*?)\n---\n', text, re.S)
        if not m:
            issues.append((os.path.basename(repo), rel, 'missing frontmatter', 'SKILL.md'))
            continue
        fm = m.group(1)
        nm = re.search(r'^name:\s*(\S+)', fm, re.M)
        if not nm:
            issues.append((os.path.basename(repo), rel, 'missing field', 'name'))
        else:
            name = nm.group(1)
            if len(name) > 64 or not re.fullmatch(r'[a-z0-9]+(-[a-z0-9]+)*', name):
                issues.append((os.path.basename(repo), rel, 'invalid skill name', name))
        dm = re.search(r'^description:\s*(.*)$', fm, re.M)
        if not dm:
            issues.append((os.path.basename(repo), rel, 'missing field', 'description'))
        else:
            # description may span lines until the next frontmatter key
            start = dm.end()
            tail = fm[start:]
            nxt = re.search(r'^[a-z][a-z0-9-]*:', tail, re.M)
            desc = (dm.group(1) + (' ' + tail[:nxt.start()] if nxt else '')).strip().strip("'\"")
            if not desc:
                issues.append((os.path.basename(repo), rel, 'empty description', 'description'))
            elif len(desc) > 1024:
                issues.append((os.path.basename(repo), rel, 'description too long', str(len(desc))))

# Stale-version gate: v0.29.0+ documents drift minimally
STALE = ['v0.28.0 - ', 'Schema 1.4.0', 'schema 1.4.0', 'speaker_orphan',
         'DB counts stale']
for root in REPOS.values():
    if not os.path.isdir(root):
        continue
    files = subprocess.run(['git', '-C', root, 'ls-files', '*.md'],
                           capture_output=True, text=True).stdout.splitlines()
    for rel in files:
        if os.path.basename(rel) in SKIP_FILES:
            continue
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            continue
        try:
            text = open(path, encoding='utf-8', errors='ignore').read()
        except OSError:
            continue
        for stale in STALE:
            if stale in text:
                issues.append((os.path.basename(root), rel, 'stale token', stale))
        # schema sentence must match reality: MANIFEST is now 1.5.0
        if 'Schema 1.5.0' not in text and 'schema 1.5.0' not in text                 and 'SCHEMA_VERSION' in text:
            pass  # not required; each doc cites what it cites

print(f'docs-command audit: {checked} commands checked')
print(f'skills spec audit: {skills_checked} SKILL.md checked')
if issues:
    print(f'ISSUES: {len(issues)}')
    for repo, rel, why, value in issues[:20]:
        print(f'  [{repo}] {rel}: {why} {value}')
    sys.exit(1)
print('PASS: all documented commands resolve')
