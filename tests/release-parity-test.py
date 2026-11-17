#!/usr/bin/env python3
"""Release parity test: certify a rebuilt database against the published
release asset by row counts, never by file bytes (build timestamps differ).

Usage: python3 tests/release-parity-test.py --local PATH --ref PATH|vX.Y.Z

Compares table-name sets, then row counts for every corpus table, then the
game-caption transcript count. Prints PASS/FAIL per check; exit 0 all-pass,
exit 1 any mismatch. A tag ref downloads grimoire.db from that GitHub
release; without network/auth it prints SKIP and exits 0. Only counts are
printed, never row text.
"""

import argparse
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TABLES = [
    "books",
    "book_entries",
    "transcripts",
    "transcript_lines",
    "grimoire_cards",
    "interactions",
    "items",
    "records",
    "characters",
    "character_lines",
    "caption_provenance",
    "caption_sightings",
    "fts",
]
CAPTION_COUNT = "SELECT COUNT(*) FROM transcripts WHERE source_tier='game_caption'"

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  ✓ {name}")
        PASS += 1
    else:
        print(f"  ✗ {name}: {detail}")
        FAIL += 1


def tables(conn):
    return {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def count(conn, table):
    try:
        return conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    except sqlite3.OperationalError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", required=True)
    ap.add_argument("--ref", required=True)
    args = ap.parse_args()

    ref = args.ref
    tmpdir = None
    if os.path.exists(ref):
        pass  # local file wins over tag-shaped names
    elif re.match(r"^v\d+\.\d+(\.\d+)?$", ref):
        tmpdir = tempfile.mkdtemp(prefix="parity-ref-")
        dl = [
            "gh",
            "release",
            "download",
            ref,
            "--pattern",
            "grimoire.db",
            "--dir",
            tmpdir,
            "--clobber",
        ]
        try:
            subprocess.run(dl, capture_output=True, check=True, cwd=ROOT, timeout=300)
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            print("SKIP: no network/auth for release download (local-only run)")
            shutil.rmtree(tmpdir, ignore_errors=True)
            return 0
        ref = os.path.join(tmpdir, "grimoire.db")
    else:
        print(f"FAIL: ref is neither an existing file nor a release tag: {ref}")
        return 1

    try:
        for label, path in (("local", args.local), ("ref", ref)):
            if not os.path.exists(path):
                print(f"FAIL: {label} database not found: {path}")
                return 1

        try:
            local = sqlite3.connect(f"file:{args.local}?mode=ro", uri=True)
            local.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except sqlite3.DatabaseError as e:
            print(f"FAIL: local database unreadable: {args.local} ({e})")
            return 1
        try:
            published = sqlite3.connect(f"file:{ref}?mode=ro", uri=True)
            published.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except sqlite3.DatabaseError as e:
            print(f"FAIL: ref database unreadable: {ref} ({e})")
            return 1

        print("=== RELEASE PARITY ===")
        lt, pt = tables(local), tables(published)
        check(
            "table sets match",
            lt == pt,
            f"local-only={sorted(lt - pt)} ref-only={sorted(pt - lt)}",
        )

        for table in TABLES:
            ln, pn = count(local, table), count(published, table)
            check(
                f"{table} rows match",
                ln is not None and ln == pn,
                f"local={ln} ref={pn}",
            )

        try:
            lc = local.execute(CAPTION_COUNT).fetchone()[0]
        except sqlite3.OperationalError:
            lc = None
        try:
            pc = published.execute(CAPTION_COUNT).fetchone()[0]
        except sqlite3.OperationalError:
            pc = None
        check(
            "game_caption transcripts match",
            lc is not None and lc == pc,
            f"local={lc} ref={pc}",
        )

    finally:
        if tmpdir is not None:
            shutil.rmtree(tmpdir, ignore_errors=True)
    print(f"\nPassed: {PASS} | Failed: {FAIL}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
