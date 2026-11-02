# Destiny Grimoire Database

SQLite database for the Destiny lore repository. Single file, no external connections, no APIs.

File: `grimoire.db` (SQLite, FTS5 full-text search enabled)

## Quick start

```bash
# Stats
python3 db/query.py stats

# Full-text search
python3 db/query.py search "Crota" --limit 5
python3 db/query.py search "Eris" --type transcripts --limit 10

# Character dialogue  
python3 db/query.py character "eris" --limit 20
python3 db/query.py character "drifter" --limit 20

# Item details
python3 db/query.py item "0a0x-nightmask"
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
| `transcripts` | 68 quest transcript headers |
| `transcript_lines` | Canonical dialogue by speaker |
| `grimoire_cards` | 2889 Destiny 1 grimoire cards |
| `interactions` | 2699 short character dialogue beats |
| `items` | Weapons, armor, gear lore + flavor text |
| `records` | 71 triumphs/seals with canonical text |
| `characters` | 18 named characters |
| `character_lines` | Canon character quotes ready for agent use |
| `fts` | FTS5 search over all tables |
| `meta` | DB version |

### Indexed columns

- `transcript_lines.speaker` for per-character queries
- `transcript_lines.norm_line` for `LIKE '%substring%'` lookups
- `items.item_type` for category lookups  
- `items.norm_text` for substring matching
- All FTS5 virtual table columns via `MATCH '<term>'`

## Query pattern for agents

The canonical interface is `db/query.py` which wraps common SQL patterns. All results are returned to stdout as plain text. Use `--limit N` to bound output.

If you need raw SQL, the `fts` table is the easiest - a single `MATCH` returns content back from the original source.

## Regenerate the database

```bash
python3 db/migrate.py
sqlite3 db/grimoire.db "SELECT key, value FROM meta;"
```

The migration reads `source/` markdown plus `archive/data/*.jsonl` scratch files.
