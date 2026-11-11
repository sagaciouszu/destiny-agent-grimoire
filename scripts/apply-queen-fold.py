#!/usr/bin/env python3
"""Re-apply the v0.33.1 The Queen split (owner ruling 2026-11-09).

The Queen never existed as a person in Destiny: the Throne World "Mara Sov and
Riven" slot. 22 lines go to Riven (Throne World / Forsaken / Nothing Left to
Say), 15 lines go to Mara Sov (Queen's Court, The Machinist seq 4/6). The
split is DB-only by design: a from-source `db/migrate.py` re-creates the
originals; this script re-applies the ruling identically to any build.

Idempotent. Run after migrate() and before the entity-web build:

    python3 scripts/apply-queen-fold.py [--dry-run]
"""
import argparse
import os
import sqlite3
import sys

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'db', 'grimoire.db')

RIVEN = [
    ('caption-w64-globals-03d1-5760', None),
    ('cutscene-destiny-2-forsaken-all-cutscenes-season-4', None),
    ('high-plains-blues', None),
    ('nothing-left-to-say', None),
]
MARA = [
    ('queens-court-loop-1', None),
    ('queens-court-loop-2', None),
    ('queens-court-loop-3', None),
    ('queens-court-loop-4', None),
    ('queens-court-loop-6', None),
    ('queens-court-loop-7', None),
]


def sel(conn, slugs):
    out = []
    for slug, _ in slugs:
        out += [r[0] for r in conn.execute(
            "SELECT rowid FROM transcript_lines WHERE transcript_id = "
            "(SELECT id FROM transcripts WHERE slug = ?) AND speaker = 'The Queen'",
            (slug,))]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--db', default=DB)
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    before = {s: conn.execute(
        "SELECT COUNT(*) FROM transcript_lines WHERE transcript_id = "
        "(SELECT id FROM transcripts WHERE slug = ?) AND speaker = 'The Queen'", (s,)).fetchone()[0]
        for s, _ in RIVEN + MARA}
    total_before = conn.execute("SELECT COUNT(*) FROM transcript_lines WHERE speaker = 'The Queen'").fetchone()[0]

    riven_ids = sel(conn, RIVEN)
    mara_ids = sel(conn, MARA)
    mara_machinist = [r[0] for r in conn.execute(
        "SELECT rowid FROM transcript_lines WHERE transcript_id = "
        "(SELECT id FROM transcripts WHERE slug = 'the-machinist') "
        "AND speaker = 'The Queen' AND seq IN (4, 6)")]
    riven_machinist = [r[0] for r in conn.execute(
        "SELECT rowid FROM transcript_lines WHERE transcript_id = "
        "(SELECT id FROM transcripts WHERE slug = 'the-machinist') "
        "AND speaker = 'The Queen' AND seq = 8")]

    plan = [('Riven', riven_ids + riven_machinist), ('Mara Sov', mara_ids + mara_machinist)]
    planned = sum(len(ids) for _, ids in plan)
    print(f'the_queen before: {total_before}; planned reassignment rows: {planned}')
    print(f'  -> Riven     {len(riven_ids) + len(riven_machinist)}')
    print(f'  -> Mara Sov  {len(mara_ids) + len(mara_machinist)}')
    for s, n in sorted(before.items()):
        if n:
            print(f'  {s}: {n}')
    if planned != 37:
        print(f'FATAL: expected 37, plan covers {planned}; refusing to proceed', file=sys.stderr)
        return 2
    if args.dry_run:
        print('dry-run: nothing written')
        return 0
    for name, ids in plan:
        if not ids:
            continue
        q = "UPDATE transcript_lines SET speaker = ? WHERE rowid IN (%s) AND speaker = 'The Queen'" % ','.join('?' * len(ids))
        conn.execute(q, (name, *ids))
    left = conn.execute("SELECT COUNT(*) FROM transcript_lines WHERE speaker = 'The Queen'").fetchone()[0]
    riv = conn.execute("SELECT COUNT(*) FROM transcript_lines WHERE speaker = 'Riven'").fetchone()[0]
    marv = conn.execute("SELECT COUNT(*) FROM transcript_lines WHERE speaker = 'Mara Sov'").fetchone()[0]
    print(f'after: The Queen={left}  Riven={riv}  Mara Sov={marv}')
    conn.commit()
    conn.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
