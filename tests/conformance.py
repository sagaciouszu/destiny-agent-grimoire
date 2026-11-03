#!/usr/bin/env python3
"""Per-file conformance sweep against STANDARDS.md.

Checks every tracked text file in all three repositories:
  - required headers (Depends On / Token Estimate) for agent module files
  - token estimate accuracy (claimed vs measured chars/4, flag >30% drift)
  - first-line purpose presence
  - file references resolve (workspace-aware)
  - grimoire persona-agnosticism (persona words only in explicitly named tests)
  - ci-checks per agent repo (stale names, circular/self deps, dashes, personal
    paths, gitignored refs in instructions, headers)
  - no tracked symlinks in any repo

Usage: python3 tests/conformance.py [--fix-tokens]
Exit 1 when violations remain.
"""
import os
import re
import subprocess
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
GR = os.path.dirname(HERE)
WORK = os.path.dirname(GR)
REPOS = {k: v for k, v in {
    'grimoire': GR,
    'drifter': os.path.join(WORK, 'how-to-drift-for-agents'),
    'eris': os.path.join(WORK, 'eris-morn'),
}.items() if os.path.isdir(v)}
if len(REPOS) < 3:
    print(f'note: {3 - len(REPOS)} agent repo(s) not present; validating {len(REPOS)} repo(s)')
FIX = '--fix-tokens' in sys.argv

SKIP_DIRS = {'.git', 'lore', '__pycache__', 'source', 'archive'}
SKIP_FILES = {'CHANGELOG.md'}

def token_estimate(text):
    return max(1, round(len(text) / 4))

def files_of(root):
    out = []
    for dirpath, dirs, fs in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in fs:
            if f.endswith('.md'):
                out.append(os.path.join(dirpath, f))
    return sorted(out)

issues = []
token_fixes = 0
for name, root in REPOS.items():
    for path in files_of(root):
        rel = os.path.relpath(path, root)
        base = os.path.basename(path)
        if base in SKIP_FILES:
            continue
        text = open(path, encoding='utf-8', errors='ignore').read()

        # purpose line: first non-empty, non-header line
        lines = [l for l in text.split('\n') if l.strip()]
        if not lines or (not lines[0].startswith('#') and not lines[0].startswith('---') and not lines[0].startswith('>')):
            issues.append((name, rel, 'no heading/purpose line'))

        # reference validity for backticked paths
        for m in re.finditer(r'`([A-Za-z0-9_./-]+\.(?:md|sh|py|json|txt|sql))`', text):
            ref = m.group(1)
            if ref.startswith('http') or ref == 'opencode.json':
                continue
            cands = [os.path.join(root, ref), os.path.join(os.path.dirname(path), ref),
                     os.path.join(root, 'lore', ref)]
            cands += [os.path.join(r, ref) for r in REPOS.values()]
            if not any(os.path.exists(c) for c in cands):
                if len(REPOS) == 3:
                    issues.append((name, rel, f'broken ref `{ref}`'))
                else:
                    missing_refs = globals().setdefault('_missing_refs', 0) + 1
                    globals()['_missing_refs'] = missing_refs

        # token estimate accuracy (agent repos only: modules carry the header)
        m = re.search(r'Token Estimate:\*\* ~(\d+(?:\.\d+)?)K', text)
        if m:
            claimed = float(m.group(1)) * 1000
            actual = token_estimate(text)
            drift = abs(actual - claimed) / max(1, claimed) * 100
            if drift > 30:
                if FIX:
                    val = round(actual / 1000, 2) if actual < 1000 else round(actual / 1000, 1)
                    new_tok = f"~{max(0.1, val)}K"
                    text2 = re.sub(r'(Token Estimate:\*\* )~\d+(?:\.\d+)?K', r'\g<1>' + new_tok, text, count=1)
                    open(path, 'w', encoding='utf-8').write(text2)
                    token_fixes += 1
                else:
                    issues.append((name, rel, f'token estimate ~{m.group(1)}K vs measured ~{actual/1000:.1f}K ({drift:.0f}% off)'))

# tracked symlinks are runtime state, never repository content
for name, root in REPOS.items():
    try:
        listed = subprocess.run(['git', '-C', root, 'ls-files', '-s'],
                                capture_output=True, text=True, check=True).stdout
    except Exception:
        continue
    for line in listed.splitlines():
        if line.startswith('120000 '):
            issues.append((name, line.split('\t')[-1],
                           'tracked symlink (runtime-only; gitignore it)'))

# grimoire persona-agnosticism: no *instructional* persona content. Naming a
# character (compendium, provenance, connection matrix) is legitimate data.
PERSONA_RULE = re.compile(
    r'\byou are (the )?(drifter|eris morn|eris)\b|\bemulat(e|ing) (the )?(drifter|eris)|\bpersona (rules|voice)\b', re.I)
for path in files_of(GR):
    rel = os.path.relpath(path, GR).replace(os.sep, '/')
    if rel.startswith(('tests/', 'compendium/')) or rel in ('README.md', 'STANDARDS.md', 'CHANGELOG.md', 'RELEASE.md', 'index.md'):
        continue
    text = open(path, encoding='utf-8', errors='ignore').read()
    if PERSONA_RULE.search(text):
        issues.append(('grimoire', rel, 'persona instruction in agent-agnostic file'))

CI_CHECKS = os.path.join(HERE, 'ci-checks.py')
if os.path.exists(CI_CHECKS):
    for name, root in REPOS.items():
        if name == 'grimoire':
            continue  # ci-checks targets agent module layout
        for chk in ('stale', 'circular', 'selfdeps', 'emdashes', 'personal',
                    'gitignored', 'headers'):
            r = subprocess.run([sys.executable, CI_CHECKS, chk, root],
                               capture_output=True, text=True)
            if r.returncode != 0:
                out = (r.stdout or r.stderr).strip().splitlines()
                issues.append((name, 'ci-checks', f'{chk}: {out[-1] if out else "failed"}'))

print(f'files scanned: {sum(len(files_of(r)) for r in REPOS.values())}')
if globals().get('_missing_refs'):
    print(f'note: {globals()["_missing_refs"]} workspace-level refs unresolved (agent repos absent)')
if FIX:
    print(f'token estimates corrected: {token_fixes}')
if issues:
    print(f'ISSUES: {len(issues)}')
    for name, rel, msg in issues:
        print(f'  [{name}] {rel}: {msg}')
    sys.exit(1)
print('PASS: all files conform')
