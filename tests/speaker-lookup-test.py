#!/usr/bin/env python3
"""Check indexed exact-speaker lookup preserves legacy substring behavior.

Rows are compared only in memory; no canon text is printed.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "db"))
import api


def legacy_lookup(conn, name, pattern, limit, offset, canon_only=False,
                  class_tag=None, tiers=None, exclude_tiers=None):
    for variant in api._speaker_variants(name):
        params = [f"%{api._like(variant)}%"]
        sql = (
            "SELECT line AS text, speaker, '' AS source_slug, t.timeline, "
            "t.source_tier AS source_tier "
            "FROM transcript_lines "
            "JOIN transcripts t ON t.id = transcript_lines.transcript_id "
            "WHERE speaker LIKE ? ESCAPE '\\' AND is_stage_dir=0"
        )
        if canon_only:
            sql += " AND is_optional=0"
        if class_tag:
            sql += " AND (class_tag IS NULL OR class_tag='' OR class_tag=?)"
            params.append(str(class_tag).lower())
        tier_clauses, tier_params = api._tier_sql(tiers, exclude_tiers)
        for clause in tier_clauses:
            sql += " AND " + clause
        params.extend(tier_params)
        if pattern:
            sql += " AND LOWER(line) LIKE ? ESCAPE '\\'"
            params.append(pattern)
        sql += " ORDER BY transcript_lines.rowid LIMIT ? OFFSET ?"
        params.extend((api._limit(limit, 20), api._offset(offset)))
        rows = conn.execute(sql, params).fetchall()
        if rows:
            return [dict(row) for row in rows]
    return []


CASES = [
    ("exact-first-name", "Eris", None, 20, 0, {}),
    ("surname-fragment-with-about", "Morn", "%hive%", 10, 5, {}),
    ("leading-the-and-class", "The Drifter", None, 12, 2,
     {"class_tag": "hunter"}),
    ("caption-only-tier", "Lord Shaxx", None, 10, 0,
     {"tiers": ["game_caption"]}),
    ("stage-label", "Narration", None, 8, 0, {}),
    ("mid-name-fragment", "ris", None, 8, 0, {}),
    ("escaped-wildcard", "%", None, 8, 0, {}),
]


def main():
    conn = api.connect()
    try:
        for label, name, pattern, limit, offset, options in CASES:
            expected = legacy_lookup(
                conn, name, pattern, limit, offset, **options)
            actual = api._transcript_lines(
                conn, name, pattern, limit, offset, **options)
            if actual != expected:
                raise SystemExit(f"FAIL: speaker lookup differs for {label}")
    finally:
        conn.close()
    print(f"speaker lookup parity: {len(CASES)} cases pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
