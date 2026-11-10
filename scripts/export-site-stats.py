#!/usr/bin/env python3
"""Export the numbers the public site is allowed to display.

The site must not hand-maintain counts. This writes one JSON snapshot from the
live database; the site reads it as `_data/grimoire.json` and every stat block
uses that source.

Usage:
    python3 scripts/export-site-stats.py --out ../destiny-agent-grimoire-site/_data/grimoire.json
"""
import argparse
import json
import os
import sqlite3
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DB = os.environ.get("GRIMOIRE_DB") or os.path.join(ROOT, "db", "grimoire.db")

TABLES = {
    "books": "books",
    "book_entries": "book_entries",
    "transcripts": "transcripts",
    "transcript_lines": "transcript_lines",
    "fts": "fts",
    "grimoire_cards": "grimoire_cards",
    "items": "items",
    "expansions": "expansions",
    "seasons": "seasons",
    "events": "events",
    "activities": "activities",
    "seals": "seals",
    "characters": "characters",
    "caption_provenance": "caption_provenance",
    "caption_sightings": "caption_sightings",
}


def release_tag():
    try:
        return subprocess.run(
            ["git", "-C", ROOT, "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--db", default=DB)
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    counts = {key: conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
              for key, table in TABLES.items()}
    meta = dict(conn.execute("SELECT key,value FROM meta").fetchall())
    caption = conn.execute(
        "SELECT COUNT(*) FROM transcripts WHERE source_tier='game_caption'"
    ).fetchone()[0]
    caption_lines = conn.execute(
        "SELECT COUNT(*) FROM transcript_lines tl JOIN transcripts t "
        "ON t.id=tl.transcript_id WHERE t.source_tier='game_caption'"
    ).fetchone()[0]
    speakers = conn.execute('SELECT COUNT(*) FROM v_speakers').fetchone()[0]
    canon_speakers = conn.execute(
        'SELECT COUNT(*) FROM v_canon_speakers').fetchone()[0]
    timeline_unknown = conn.execute(
        'SELECT COUNT(*) FROM transcripts WHERE timeline IS NULL').fetchone()[0]
    source_url_missing = conn.execute(
        "SELECT COUNT(*) FROM transcripts WHERE source_url IS NULL "
        "OR source_url = ''").fetchone()[0]
    coverage = dict(conn.execute(
        'SELECT status, COUNT(*) FROM coverage_notes GROUP BY status').fetchall())
    conn.close()

    capabilities = json.load(open(os.path.join(ROOT, "db", "capabilities.json"),
                                  encoding="utf-8"))
    mcp_tools = capabilities["mcp"]["tools"]

    size = os.path.getsize(args.db)
    payload = {
        "schema_version": meta.get("version"),
        "release": release_tag(),
        "generated_from": os.path.basename(args.db),
        "last_updated": meta.get("last_updated"),
        "counts": {
            **counts,
            "caption_headers": caption,
            "caption_lines": caption_lines,
            "speakers": speakers,
            "canon_speakers": canon_speakers,
            "timeline_unknown": timeline_unknown,
            "source_url_missing": source_url_missing,
            "coverage_no_dialogue": coverage.get('no_dialogue', 0),
            "coverage_partial": coverage.get('partial_transcript', 0),
        },
        "mcp_tools": len(mcp_tools),
        "mcp_tool_names": sorted(mcp_tools),
        "sizes": {
            "db_bytes": size,
            "db_mb": int(round(size / (1024 * 1024), -1)),
            "slim_mb": 224,
        },
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"wrote {args.out} ({payload['release']}, {payload['schema_version']})")


if __name__ == "__main__":
    main()
