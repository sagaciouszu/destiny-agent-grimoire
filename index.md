# Destiny Agent Grimoire

Master Index. The canonical source of truth for all lore is the SQLite database:

- `db/grimoire.db` - SQLite database with FTS5 full-text search
- `python3 db/query.py stats` - full row counts by table
- `python3 db/query.py search "<keyword>" --limit 5` - full-text search
- `python3 db/query.py character "<name>" --limit 20` - character dialogue
- `python3 db/query.py item "<slug>"` - item details

## Database Totals

| Table | Rows |
|-------|------|
| books | 110 |
| book_entries | 1158 |
| transcripts | 68 |
| transcript_lines | 1709 |
| grimoire_cards | 2889 |
| interactions | 2699 |
| items | 58764 |
| records | 71 |
| characters | 18 |
| character_lines | 1054 |
| fts | 67290 |

## Repository Layout

| Directory | Purpose |
|-----------|---------|
| `db/` | SQLite database + query interface |
| `compendium/` | Markdown character line index (agent fallback) |
| `source/` | Raw lore markdown (books, cards, transcripts, records, items, interactions) |
| `tests/` | CI tests (DB-backed) |
| `scripts/` | Ingestion scripts |
| `archive/` | Raw scraper data (JSONL) |
| `skills/` | Agent-facing skill markdown |

## Legacy / Additional

- `destiny-1-legacy-card-index.md` - the pre-DB markdown index for Destiny 1 grimoire cards (archived reference only)
- All lore is now in `db/grimoire.db`. Markdown exists as source-of-truth for the migration script.
