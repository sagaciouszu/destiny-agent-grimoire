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
  - README contract: order, metadata, banner, version/last push (STANDARDS 12)
  - README commands point at existing scripts; agent repos stay structurally parallel
  - shared agent documents have identical section sequences (STANDARDS 13)
  - release notes stay short and follow the What's Changed / Verification shape

Usage: python3 tests/conformance.py [--fix-tokens]
Exit 1 when violations remain.
"""
import os
import re
import subprocess
import sys
import glob
import json

HERE = os.path.dirname(os.path.realpath(__file__))
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

SKIP_DIRS = {'.git', 'lore', '__pycache__', '.venv', 'node_modules', 'source', 'archive', 'docs'}
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

# README contract (STANDARDS section 12)
README_SECTIONS = {
    'grimoire': ['## Quick start for Guardians', '## Requirements', '## What is inside',
                 '## For agents', '## Repository layout', '## Maintenance',
                 '## Verification', '## License and attribution'],
    'drifter': ['## Quick start for Guardians', '## Requirements', '## For agents',
                '## Repository layout', '## Verification', '## Troubleshooting',
                '## License and attribution'],
}
README_SECTIONS['eris'] = README_SECTIONS['drifter']
README_META = re.compile(r'\*\*Version:\*\* \S+ \| \*\*Last push:\*\* \d{4}-\d{2}-\d{2} \| \*\*Status:\*\* Active')
agent_sequences = {}
for name, root in REPOS.items():
    path = os.path.join(root, 'README.md')
    if not os.path.exists(path):
        issues.append((name, 'README.md', 'missing'))
        continue
    text = open(path, encoding='utf-8').read()
    first = next((l for l in text.splitlines() if l.strip()), '')
    if not first.startswith('# '):
        issues.append((name, 'README.md', 'first line is not an H1 title'))
    if 'header.png' not in text or not os.path.exists(os.path.join(root, 'header.png')):
        issues.append((name, 'README.md', 'missing banner (header.png)'))
    if not README_META.search(text):
        issues.append((name, 'README.md', 'missing version/last push metadata line'))
    seq = [h for h in README_SECTIONS[name] if h in text]
    if seq != README_SECTIONS[name]:
        missing = [h for h in README_SECTIONS[name] if h not in text]
        issues.append((name, 'README.md', f'missing required sections: {missing}'))
    else:
        pos = [text.index(h) for h in README_SECTIONS[name]]
        if pos != sorted(pos):
            issues.append((name, 'README.md', 'sections out of order'))
    if name != 'grimoire':
        agent_sequences[name] = tuple(h for h in text.splitlines() if h.startswith('## '))
if len(agent_sequences) == 2 and len(set(agent_sequences.values())) > 1:
    issues.append(('agents', 'README.md', 'Drifter and Eris README section order differs'))

# README commands must point at real scripts
CMD_REF = re.compile(r'^(?:bash|sh|python3)\s+([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:sh|py))', re.M)
for name, root in REPOS.items():
    path = os.path.join(root, 'README.md')
    if not os.path.exists(path):
        continue
    text = open(path, encoding='utf-8').read()
    for ref in sorted(set(CMD_REF.findall(text))):
        cands = [os.path.join(root, ref), os.path.join(root, 'lore', ref)]
        for other in REPOS.values():
            cands += [os.path.join(other, ref), os.path.join(other, 'lore', ref)]
        if not any(os.path.exists(c) for c in cands):
            issues.append((name, 'README.md', f'command targets missing script `{ref}`'))

# Agent repositories stay structurally parallel
if 'drifter' in REPOS and 'eris' in REPOS:
    d_root, e_root = REPOS['drifter'], REPOS['eris']
    try:
        d_ig = open(os.path.join(d_root, '.gitignore'), encoding='utf-8').read()
        e_ig = open(os.path.join(e_root, '.gitignore'), encoding='utf-8').read()
        if d_ig != e_ig:
            issues.append(('agents', '.gitignore', 'Drifter and Eris .gitignore differ'))
    except FileNotFoundError:
        pass

    def norm_setup(text):
        text = text.replace('The Drifter', 'AGENT').replace('Eris Morn', 'AGENT')
        text = text.replace('Drifter', 'AGENT')
        return text.replace('drifter-core.md', 'CORE.md').replace('eris-core.md', 'CORE.md')

    try:
        d_sh = norm_setup(open(os.path.join(d_root, 'setup.sh'), encoding='utf-8').read())
        e_sh = norm_setup(open(os.path.join(e_root, 'setup.sh'), encoding='utf-8').read())
        if d_sh != e_sh:
            issues.append(('agents', 'setup.sh', 'setup scripts diverge beyond agent names'))
    except FileNotFoundError:
        pass

# Shared agent documents must keep the same section sequence (STANDARDS 13)
PARITY_DOCS = ('SOUL.md', 'AGENTS.md', 'INDEX.md', 'TOOLS.md', 'IDENTITY.md',
               'USER.template.md', 'RELEASE.md')
if 'drifter' in REPOS and 'eris' in REPOS:
    for doc in PARITY_DOCS:
        sequences = {}
        for name in ('drifter', 'eris'):
            path = os.path.join(REPOS[name], doc)
            if not os.path.exists(path):
                issues.append((name, doc, 'missing shared document'))
                continue
            text = open(path, encoding='utf-8').read()
            sequences[name] = tuple(l for l in text.splitlines() if l.startswith('## '))
        if len(sequences) == 2 and sequences['drifter'] != sequences['eris']:
            issues.append(('agents', doc, 'section sequence differs between agents'))
        if doc == 'IDENTITY.md' and len(sequences) == 2:
            fields = {}
            for name in ('drifter', 'eris'):
                text = open(os.path.join(REPOS[name], doc), encoding='utf-8').read()
                fields[name] = tuple(re.findall(r'^- \*\*([^*]+):\*\*', text, re.M))
            if fields['drifter'] != fields['eris']:
                issues.append(('agents', doc, 'identity fields differ between agents'))

# Release notes stay short and scannable (STANDARDS 14)
REL_SECTIONS = ["## What's Changed", '## Verification']
for name, root in REPOS.items():
    path = os.path.join(root, 'RELEASE.md')
    if not os.path.exists(path):
        issues.append((name, 'RELEASE.md', 'missing'))
        continue
    text = open(path, encoding='utf-8').read()
    lines = text.splitlines()
    if not lines or not lines[0].startswith('# v'):
        issues.append((name, 'RELEASE.md', 'first line must be `# vX.Y.Z - theme`'))
    if len(lines) > 40:
        issues.append((name, 'RELEASE.md', f'{len(lines)} lines (limit 40)'))
    required = REL_SECTIONS + (['## Asset'] if name == 'grimoire' else [])
    present = [h for h in required if h in text]
    if present != required:
        issues.append((name, 'RELEASE.md', f'missing sections: {[h for h in required if h not in text]}'))
    else:
        pos = [text.index(h) for h in required]
        if pos != sorted(pos):
            issues.append((name, 'RELEASE.md', 'sections out of order'))

# MCP contract stays in sync: manifest, server decorators, README table
if 'grimoire' in REPOS:
    gr = REPOS['grimoire']
    cap_path = os.path.join(gr, 'db', 'capabilities.json')
    srv_path = os.path.join(gr, 'mcp-server', 'server.py')
    readme_path = os.path.join(gr, 'mcp-server', 'README.md')
    try:
        manifest = set(json.load(open(cap_path, encoding='utf-8'))['mcp']['tools'])
        srv = open(srv_path, encoding='utf-8').read()
        implemented = set(re.findall(r'@server\.tool\([^)]*\)\s*\ndef (\w+)\(', srv))
        docs = set(re.findall(r'^\| `(\w+)` \|', open(readme_path, encoding='utf-8').read(), re.M))
        if not (manifest == implemented == docs):
            issues.append(('grimoire', 'mcp', f'tool drift: manifest={sorted(manifest)} '
                           f'server={sorted(implemented)} docs={sorted(docs)}'))
        req = open(os.path.join(gr, 'mcp-server', 'requirements.txt'), encoding='utf-8').read()
        lock_path = os.path.join(gr, 'mcp-server', 'requirements.lock.txt')
        installer = open(os.path.join(gr, 'mcp-server', 'install.sh'), encoding='utf-8').read()
        if 'mcp==' not in req:
            issues.append(('grimoire', 'mcp-server/requirements.txt', 'SDK is not pinned'))
        if not os.path.exists(lock_path) or '--hash=sha256:' not in open(lock_path, encoding='utf-8').read():
            issues.append(('grimoire', 'mcp-server/requirements.lock.txt', 'missing hash-locked dependencies'))
        if '--require-hashes' not in installer:
            issues.append(('grimoire', 'mcp-server/install.sh', 'does not enforce hashes'))
        skill_path = os.path.join(gr, 'skills', 'destiny-grimoire', 'SKILL.md')
        skill = open(skill_path, encoding='utf-8').read()
        skill_missing = [t for t in manifest if t not in skill]
        if skill_missing:
            issues.append(('grimoire', 'skills/destiny-grimoire/SKILL.md',
                           f'missing MCP tools: {sorted(skill_missing)}'))
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
        issues.append(('grimoire', 'mcp', f'cannot verify MCP contract: {e}'))

# Licensing split: LICENSE (MIT) plus NOTICE in every repo
for name, root in REPOS.items():
    lic = os.path.join(root, 'LICENSE')
    notice = os.path.join(root, 'NOTICE')
    if not os.path.exists(lic) or 'MIT License' not in open(lic, encoding='utf-8').read():
        issues.append((name, 'LICENSE', 'missing MIT license'))
    if not os.path.exists(notice):
        issues.append((name, 'NOTICE', 'missing'))
    else:
        text = open(notice, encoding='utf-8').read()
        if 'MIT License' not in text or 'Bungie' not in text:
            issues.append((name, 'NOTICE', 'must state MIT and Bungie IP ownership'))

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

META_SCRIPT = os.path.join(HERE, 'sync-readme-meta.py')
if os.path.exists(META_SCRIPT):
    r = subprocess.run([sys.executable, META_SCRIPT, '--check'], capture_output=True, text=True)
    if r.returncode != 0:
        for line in (r.stdout or r.stderr).strip().splitlines():
            issues.append(('README', 'metadata', line.strip()))

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
