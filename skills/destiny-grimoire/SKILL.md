---
name: destiny-grimoire
description: 'Query the Destiny Agent Grimoire for verified Destiny 2 lore, character dialogue, books, and transcripts. Use when an agent needs Destiny lore, character quotes, faction info, or transcript references. Triggers: destiny, lore, grimoire, character lines, transcript, book, quote, faction, location.'
license: MIT
metadata:
  tags: "Destiny, Lore, Grimoire, Characters, Transcripts, Books"
  category: "reference"
---

# Destiny Agent Grimoire

Agent-optimized archive of Destiny 2 lore (110 books, 68 transcripts, 473 verified Drifter lines, 1070 indexed character lines). Use this to pull verified lore on demand without scanning the full corpus.

## Location

- Repo root: `~/Work/destiny-agent-grimoire/` (or wherever cloned)
- Symlink in how-to-drift: `lore/` -> `~/Work/destiny-agent-grimoire/`

## Structure

- `index.md` - Repository overview (points to SQLite as source of truth).
- `db/grimoire.db` - SQLite database (primary data store, FTS5 search).
- `db/query.py` - Agent query interface.
- `compendium/index.md` - Markdown character line index (fallback).
- `source/` - Raw lore markdown (books, transcripts, cards, items, records, interactions).
- `tests/` - Validation scripts.

## How to query

Use `db/query.py` for all queries. It wraps SQLite with FTS5 full-text search.

### Full-text search
```bash
python3 db/query.py search "Crota" --limit 5
python3 db/query.py search "Eris" --type transcripts --limit 10
python3 db/query.py search "hive" --type books
```

### Character dialogue
```bash
python3 db/query.py character "eris" --limit 20
python3 db/query.py character "drifter" --limit 20
```

### Item details
```bash
python3 db/query.py item "0a0x-nightmask"
```

### Database stats
```bash
python3 db/query.py stats
```

### Direct SQL (advanced)
```bash
sqlite3 db/grimoire.db "SELECT title, text FROM fts WHERE fts MATCH 'hive' LIMIT 5"
sqlite3 db/grimoire.db "SELECT speaker, COUNT(*) FROM transcript_lines GROUP BY speaker ORDER BY 2 DESC LIMIT 10"
```

### Quote verification
- All quotes verified against canonical transcripts (473 Drifter lines) + lore books.
- Run `tests/drifter-quote-verify.sh` to re-verify.

## Rules

- Only use verified quotes. Unverified strings must be unquoted.
- Lore books are verbatim source text; do not paraphrase as quotes.
- Destiny 1 content is complete: all 2889 grimoire cards in the DB.
- Keep queries scoped: load only the file you need to save tokens.

## Sources

All content from https://www.ishtar-collective.net (Ishtar Collective). Fan-made, not affiliated with Bungie.
