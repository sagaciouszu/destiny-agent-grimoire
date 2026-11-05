#!/usr/bin/env python3
"""Fail when persona.json canon_lines no longer matches the database.

Usage: persona-freshness.py [<persona.json> <grimoire.db>]
With no arguments it checks this repo's persona.json against
lore/db/grimoire.db (GRIMOIRE_DB/LORE overridable).
Exits 0 when fresh or when the persona has no recorded count.
"""
import json
import os
import sqlite3
import sys


def resolve_paths():
    """Explicit <persona.json> <grimoire.db> arguments, or this repo's defaults."""
    if len(sys.argv) == 3:
        return sys.argv[1], sys.argv[2]
    if len(sys.argv) == 1:
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        lore = os.environ.get('LORE') or os.path.join(repo, 'lore')
        db = os.environ.get('GRIMOIRE_DB') or os.path.join(lore, 'db', 'grimoire.db')
        return os.path.join(repo, 'persona.json'), db
    return None, None


def main():
    persona_path, db_path = resolve_paths()
    if persona_path is None:
        print('usage: persona-freshness.py [<persona.json> <grimoire.db>]', file=sys.stderr)
        return 2
    if len(sys.argv) == 1 and not os.path.isfile(persona_path):
        # Bare invocation outside an agent repo (e.g. the canonical copy in the
        # grimoire tests/ dir): nothing to check, stay dependency-free.
        print(f'SKIP: no persona.json at {persona_path}')
        return 0
    persona = json.load(open(persona_path, encoding='utf-8'))
    speaker = persona.get('speaker')
    expected = persona.get('canon_lines')
    if not speaker or not isinstance(expected, int):
        return 0
    conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
    actual = conn.execute(
        'SELECT COUNT(*) FROM transcript_lines '
        'WHERE speaker=? AND is_stage_dir=0 AND is_optional=0', (speaker,)).fetchone()[0]
    conn.close()
    if actual != expected:
        print(f'{speaker}: canon_lines {expected} != database {actual}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
