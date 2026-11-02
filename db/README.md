# Destiny Grimoire Database

SQLite database for agent-optimized Destiny lore queries. Single file, no external dependencies.

## Quick Start

```bash
# Stats
python3 db/query.py stats

# Full-text search
python3 db/query.py search "Crota" --limit 5
python3 db/query.py search "Eris" --type transcripts --limit 10

# Character lines
python3 db/query.py character "eris" --limit 20

# Item details
python3 db/query.py item "0a0x-nightmask"
```

## Direct SQL

```bash
sqlite3 db/grimoire.db "SELECT title, text FROM fts WHERE fts MATCH 'hive' LIMIT 5"
sqlite3 db/grimoire.db "SELECT speaker, COUNT(*) FROM transcript_lines GROUP BY speaker ORDER BY 2 DESC LIMIT 10"
sqlite3 db/grimoire.db "SELECT slug, title FROM items WHERE item_type LIKE '%Exotic%' LIMIT 20"
```

## Tables

| Table | Description |
|-------|-------------|
| books | 110 lore books |
| book_entries | 1158 book sections |
| transcripts | 68 quest transcripts |
| transcript_lines | 1070 dialogue lines with speakers |
| grimoire_cards | 2889 Destiny 1 grimoire cards |
| interactions | 2699+ character interactions |
| items | 5601+ gear/weapon/armor items |
| records | 71 triumphs/seals |
| characters | 18 named characters |
| character_lines | 1054 verified character lines |
| fts | FTS5 full-text search index |
| meta | Database metadata |

## Schema

See `db/schema.sql` for full DDL.
