#!/usr/bin/env python3
"""Count consistency: persona.json, the database and derived prose must agree.

For every agent repo listed in series/agents.json (sibling directories, skip
when absent):
  1. persona.json canon_lines == DB count (exact speaker, is_stage_dir=0,
     is_optional=0, excluding game captions) and canon_variant_lines == optional
     variant count.
  2. Derived prose counts in <agent>-core.md ("N lines across"),
     <agent>-voice.md ("Canonical lines | N |") and entry/AGENTS prose
     ("(N <Speaker> lines)") must equal persona.json canon_lines.

Exit 0 pass / 1 fail. Missing repos are skipped with a note.
"""
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

WORK = os.environ.get('AGENT_REPOS_DIR') or os.path.dirname(ROOT)
MANIFEST = os.path.join(ROOT, 'series', 'agents.json')
DB = os.environ.get('GRIMOIRE_DB') or os.path.join(ROOT, 'db', 'grimoire.db')

PASSED = FAILED = 0


def check(name, ok, detail=''):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f'  PASS: {name}')
    else:
        FAILED += 1
        print(f'  FAIL: {name}' + (f' ({detail})' if detail else ''))


def prose_claims(path, patterns):
    """Yield (pattern_label, value) for every count claim found in a file."""
    if not os.path.isfile(path):
        return
    text = open(path, encoding='utf-8').read()
    for label, pattern in patterns:
        for match in re.finditer(pattern, text):
            yield label, int(match.group(1))


def main():
    if not os.path.isfile(DB):
        print('SKIP: grimoire.db missing - PASS')
        return 0
    conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    manifest = json.load(open(MANIFEST, encoding='utf-8'))
    checked = 0
    for agent in manifest.get('agents', []):
        ident = agent.get('id', '')
        repo = os.path.join(WORK, agent.get('source', ''))
        persona_path = os.path.join(repo, 'persona.json')
        if not os.path.isfile(persona_path):
            print(f'  SKIP: {ident} (repo or persona.json absent)')
            continue
        checked += 1
        persona = json.load(open(persona_path, encoding='utf-8'))
        speaker = persona.get('speaker')
        canon = persona.get('canon_lines')
        variants = persona.get('canon_variant_lines', 0)
        # Persona canon excludes game captions (source_tier='game_caption'):
        # captions are searchable canon but not part of a persona's curated
        # voice count. Same predicate as persona-freshness.py and
        # character_info.spoken_lines.
        actual = conn.execute(
            'SELECT COUNT(*) FROM transcript_lines tl '
            'JOIN transcripts t ON t.id = tl.transcript_id '
            'WHERE tl.speaker=? AND tl.is_stage_dir=0 AND tl.is_optional=0 '
            "AND COALESCE(t.source_tier, '') != 'game_caption'",
            (speaker,)).fetchone()[0]
        check(f'{ident}: persona canon_lines == DB ({actual})',
              canon == actual, f'persona={canon}')
        actual_variants = conn.execute(
            'SELECT COUNT(*) FROM transcript_lines tl '
            'JOIN transcripts t ON t.id = tl.transcript_id '
            'WHERE tl.speaker=? AND tl.is_stage_dir=0 AND tl.is_optional=1 '
            "AND COALESCE(t.source_tier, '') != 'game_caption'",
            (speaker,)).fetchone()[0]
        check(f'{ident}: persona canon_variant_lines == DB ({actual_variants})',
              variants == actual_variants, f'persona={variants}')

        patterns = [
            ('lines across', re.compile(r'(\d+) lines across \d+ transcripts')),
            ('Canonical lines table',
             re.compile(r'\|\s*Canonical lines\s*\|\s*(\d+)\s*\|')),
            (f'({speaker} lines)',
             re.compile(r'\((\d+) ' + re.escape(speaker) + r' lines\)')),
        ]
        for fname in (f'{ident}-core.md', f'{ident}-voice.md',
                      f'{ident}.md', 'AGENTS.md', 'INDEX.md'):
            for label, value in prose_claims(os.path.join(repo, fname), patterns):
                check(f'{ident}: {fname} {label} == canon_lines ({canon})',
                      value == canon, f'found {value}')
    conn.close()
    if not checked:
        print('  FAIL: no agent repos found next to the grimoire')
        print(f'Passed: {PASSED} | Failed: {FAILED}')
        return 1
    print(f'Passed: {PASSED} | Failed: {FAILED}')
    return 1 if FAILED else 0


if __name__ == '__main__':
    sys.exit(main())
