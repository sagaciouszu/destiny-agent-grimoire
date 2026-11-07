# Destiny Grimoire Database

SQLite database for the Destiny lore repository. Single file, no external connections, no APIs.

File: `grimoire.db` (SQLite, FTS5 full-text search enabled). Built from `source/` + `archive/` by `migrate.py`; not committed, prebuilt copies attached to releases.

## Quick start

```bash
# Stats
python3 db/query.py stats

# Full-text search
python3 db/query.py search "Crota" --limit 5     # relevance order (default)
python3 db/query.py search "Crota" --limit 5 --no-rank
python3 db/query.py search "Eris" --type transcripts --limit 10

# Character dialogue  
python3 db/query.py character "eris" --limit 20
python3 db/query.py character "drifter" --limit 20

# Item details
python3 db/query.py item "0a0x-nightmask"

# Quote verification (exit 1 when not found)
python3 db/query.py verify "Absolutely not." --speaker "Eris Morn" --exact

# Read a book, transcript, seal, or find items by title
python3 db/query.py book "a-man-with-no-name" --limit 5
python3 db/query.py transcript "savathuns-spire" --limit 20 --speaker "Eris Morn" --include-stage
python3 db/query.py find-item "nightmask" --limit 10
python3 db/query.py record "am-i-to-cast-a-shadow"

# Discovery listings (all read commands accept --offset)
python3 db/query.py list <books|characters|speakers|records|activities|seasons|events|lore|seals> [--limit N] [--offset N]

# Any command: --json for compact machine-readable output
```

Or raw SQL:

```bash
sqlite3 db/grimoire.db "SELECT title, text FROM fts WHERE fts MATCH 'hive' LIMIT 5"
sqlite3 db/grimoire.db "SELECT speaker, line FROM transcript_lines WHERE speaker LIKE '%Eris%' LIMIT 10"
sqlite3 db/grimoire.db "SELECT slug, title, item_type FROM items WHERE item_type LIKE '%Exotic%' AND text != '' LIMIT 20"
```

## Schema

### Content tables

| Table | Purpose |
|-------|---------|
| `books` | 110 lore books (slug, title, source_url, entry_count) |
| `book_entries` | 1158 entries within books (FK to books) |
| `transcripts` | 2422 transcript headers (quest + cutscene + web) |
| `transcript_lines` | Canonical dialogue by speaker |
| `grimoire_cards` | 2889 Destiny 1 grimoire cards |
| `interactions` | 2699 short character dialogue beats |
| `items` | Weapons, armor, gear lore + flavor text |
| `records` | 69 triumphs/seals with canonical text |
| `characters` | 20 named characters |
| `character_lines` | Canon character quotes ready for agent use |
| `fts` | FTS5 search over all tables |
| `verify_fts` | normalized text + provenance for fast quote verification |
| `item_title_fts` | item titles for fast name lookup |
| `meta` | DB version |

### Indexed columns

- `transcript_lines.speaker` for per-character queries
- `transcript_lines.norm_line` for `LIKE '%substring%'` lookups
- `items.item_type` for category lookups  
- `items.norm_text` for substring matching
- All FTS5 virtual table columns via `MATCH '<term>'`

## Schema version

`SCHEMA_VERSION` is the source of truth. `migrate.py` writes it to `meta.version`;
`tests/test-db.sh` fails when the database and the file disagree.

## Slim profile

`python3 db/build-slim.py [out]` builds a 95 MB core database with books,
transcripts, interactions and records, but without items or grimoire cards.

## Extras

- `api.py` - importable query layer shared by the CLI and the MCP server
- `../mcp-server/` - optional stdio MCP adapter (official SDK, read-only)
- `capabilities.json` - machine-readable interface manifest (tables, views, commands, contracts)
- `v_speakers` view - canonical speakers with line counts
- `speaker_aliases` table - alias -> canonical mapping applied at migration

## Query pattern for agents

The canonical interface is `db/query.py` which wraps common SQL patterns. All results are returned to stdout as plain text. Use `--limit N` to bound output.

If you need raw SQL, the `fts` table is the easiest - a single `MATCH` returns content back from the original source.

## Regenerate the database

```bash
python3 db/migrate.py
sqlite3 db/grimoire.db "SELECT key, value FROM meta;"
```

The migration reads `source/` markdown plus `archive/data/*.jsonl` scratch files.
