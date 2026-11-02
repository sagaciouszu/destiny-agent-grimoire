# Destiny Agent Grimoire

This repository is a canonical Destiny lore archive, indexed via SQLite. Canonical data lives in `db/grimoire.db`.

## Database tables

| Table | Rows | Purpose |
|-------|------|---------|
| books | 110 | Book metadata |
| book_entries | 1158 | Lore entries within books |
| transcripts | 68 | Quest transcript headers |
| transcript_lines | 1709 | Canonical character dialogue |
| grimoire_cards | 2889 | Destiny 1 grimoire cards |
| interactions | 2699 | Character dialogue beats |
| items | 58764 | Gear/weapon/armor lore |
| records | 71 | Triumphs & seals |
| characters | 18 | Named characters by dialogue |
| character_lines | 1054 | Character quotes for agent use |
| fts | 67290 | FTS5 search index |

## How agents should use this

- Query via `python3 db/query.py [search|character|item|stats]` for everything.
- Markdown files under `source/` exist only as the ingestion source and are not canonical post-ingestion.
- If the database is missing or wrong, fix it by re-running `python3 db/migrate.py`.
