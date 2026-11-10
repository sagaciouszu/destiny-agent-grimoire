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
