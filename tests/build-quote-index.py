#!/usr/bin/env python3
"""Build reference/quote-inverted-index.json from the canon database.

The index maps lowercase words (4+ chars) to 160-char snippets of the Drifter
lines containing them (full text stays in the database).
Generated, never hand-edited: rerun after any database rebuild.

Usage:
    python3 tests/build-quote-index.py            # rebuild
    python3 tests/build-quote-index.py --check    # exit 1 if stale
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def workspace():
    ws = os.environ.get("WORKSPACE")
    if ws:
        return ws
    try:
        out = subprocess.run(
            ["bash", os.path.join(HERE, "resolve-workspace.sh"),
             os.path.join(HERE, "drifter-master-audit.sh")],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return os.path.abspath(os.path.join(HERE, "..", "..", "how-to-drift-for-agents"))


def db_path(ws):
    for p in (os.path.join(ws, "lore", "db", "grimoire.db"),
              os.path.join(os.path.dirname(HERE), "db", "grimoire.db")):
        if os.path.exists(p):
            return p
    sys.exit("database not found: bootstrap lore/db/grimoire.db first")


def snippet(text, limit=160):
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(",;:-")
    return cut


def build(db):
    import sqlite3
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT cl.text FROM character_lines cl "
        "JOIN characters c ON c.id = cl.character_id WHERE c.name = 'Drifter'"
    ).fetchall()
    conn.close()

    index = {}
    for (text,) in rows:
        seen = set()
        for tok in re.findall(r"[a-z0-9']+", text.lower()):
            tok = tok.strip("'")
            if len(tok) < 4 or tok in seen:
                continue
            seen.add(tok)
            index.setdefault(tok, set()).add(snippet(text))
    return {k: sorted(v) for k, v in sorted(index.items())}


def main():
    ws = workspace()
    out_path = os.path.join(ws, "reference", "quote-inverted-index.json")
    built = build(db_path(ws))

    if "--check" in sys.argv:
        try:
            current = json.load(open(out_path, encoding="utf-8"))
        except FileNotFoundError:
            print(f"STALE: {out_path} missing (run tests/build-quote-index.py)")
            return 1
        current = {k: sorted(set(v)) for k, v in current.items()}
        if current != built:
            n_old = sum(len(v) for v in current.values())
            n_new = sum(len(v) for v in built.values())
            print(f"STALE: index has {n_old} refs, canon has {n_new} "
                  f"(run tests/build-quote-index.py)")
            return 1
        if "--quiet" not in sys.argv:
            print(f"index fresh: {len(built)} keys, "
                  f"{sum(len(v) for v in built.values())} refs")
        return 0

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(built, fh, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        fh.write("\n")
    print(f"wrote {out_path}: {len(built)} keys, "
          f"{sum(len(v) for v in built.values())} refs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
