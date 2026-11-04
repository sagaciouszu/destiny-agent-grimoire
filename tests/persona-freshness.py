#!/usr/bin/env python3
"""Fail when persona.json canon_lines no longer matches the database.

Usage: persona-freshness.py <persona.json> <grimoire.db>
Exits 0 when fresh or when the persona has no recorded count.
"""
import json
import sqlite3
import sys


def main():
    if len(sys.argv) != 3:
        print('usage: persona-freshness.py <persona.json> <grimoire.db>', file=sys.stderr)
        return 2
    persona = json.load(open(sys.argv[1], encoding='utf-8'))
    speaker = persona.get('speaker')
    expected = persona.get('canon_lines')
    if not speaker or not isinstance(expected, int):
        return 0
    conn = sqlite3.connect(f'file:{sys.argv[2]}?mode=ro', uri=True)
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
