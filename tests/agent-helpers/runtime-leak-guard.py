#!/usr/bin/env python3
"""Guard: runtime memory content must not leak into published prompt material.

Scans gitignored runtime files (journal, USER.md, memory, session state) for
substantive lines and fails if any long line appears verbatim in committed
prompt files (entry, core/voice/world/reference modules, AGENTS.md, SOUL.md).
Short phrases are ignored to avoid false positives on common words.
Only file paths and match counts are reported, never file contents.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

RUNTIME = ['core/journal.md', 'USER.md', 'DREAMS.md',
           'core/user-memory.md', 'core/session-state.md',
           'core/cross-session-memory.md']
MIN_NORM = 40


def norm(s):
    s = s.lower().replace('\u2019', "'").replace('\u2014', '-').replace('\u2013', '-')
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def prompt_files():
    out = []
    for root, dirs, fs in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in ('.git', 'lore', 'tests', '__pycache__',
                                                'memory', '.venv')]
        for f in fs:
            if not f.endswith('.md'):
                continue
            rel = os.path.relpath(os.path.join(root, f), REPO)
            if rel in RUNTIME or f.endswith('.template.md'):
                continue
            out.append(os.path.join(root, f))
    return sorted(out)


def main():
    prompts = prompt_files()
    corpus = []
    for p in prompts:
        try:
            corpus.append(norm(open(p, encoding='utf-8', errors='ignore').read()))
        except OSError:
            pass
    big = '\n'.join(corpus)
    leaks = []
    scanned = 0
    runtime_blob = []
    for rel in RUNTIME:
        path = os.path.join(REPO, rel)
        if not os.path.isfile(path):
            continue
        # A pristine seed is committed template content, not a leak: only
        # scan runtime files the user (or a session) actually changed.
        template = os.path.join(REPO, rel[:-3] + '.template.md')
        if os.path.isfile(template):
            try:
                same = (open(path, encoding='utf-8', errors='ignore').read()
                        == open(template, encoding='utf-8', errors='ignore').read())
            except OSError:
                same = False
            if same:
                continue
        text = open(path, encoding='utf-8', errors='ignore').read()
        runtime_blob.append(norm(text))
        for line in text.splitlines():
            nq = norm(line.strip().strip('"'))
            if len(nq) < MIN_NORM:
                continue
            scanned += 1
            if nq in big:
                leaks.append(rel)
                break
    # Reverse direction: a verbatim prompt line pasted into runtime notes with
    # surrounding user text. Check long prompt lines against runtime content.
    combined = '\n'.join(runtime_blob)
    if combined.strip():
        for prompt in prompts:
            for line in open(prompt, encoding='utf-8', errors='ignore').read().splitlines():
                nq = norm(line.strip().strip('"'))
                if len(nq) < MIN_NORM:
                    continue
                if nq in combined:
                    leaks.append(os.path.relpath(prompt, REPO) + ' echoed in runtime notes')
                    break
            if leaks:
                break
    print(f'runtime files scanned for long lines; prompt files checked: {len(prompts)}')
    if leaks:
        print(f'FAIL: runtime content leaked into published prompts: {sorted(set(leaks))}')
        return 1
    print('PASS: no runtime leaks into published prompt material')
    return 0


if __name__ == '__main__':
    sys.exit(main())
