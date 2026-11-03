# Destiny Agent Grimoire

An agent-first lore archive for the Destiny universe. All content is served via a single SQLite database with FTS5 full-text search. No external services needed.

**Version:** 1.2.0

## Quick start

The database is a build artifact and is not committed. Bootstrap it once after cloning - pick one:

```bash
# Option 1: download the prebuilt release asset (seconds)
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db

# Option 2: build from your checkout (~2 minutes, matches this commit)
python3 db/migrate.py
```

Agent repos (`how-to-drift-for-agents`, `eris-morn`) present this choice in their own `setup.sh` on first run.

```bash
# Database stats
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

Or with raw SQL:

```bash
sqlite3 db/grimoire.db "SELECT title, text FROM fts WHERE fts MATCH 'hive' LIMIT 5"
sqlite3 db/grimoire.db "SELECT speaker, line FROM transcript_lines WHERE speaker LIKE '%Eris%' LIMIT 10"
sqlite3 db/grimoire.db "SELECT slug, title, item_type FROM items WHERE item_type LIKE '%Exotic%' LIMIT 20"
```

## Contents

| Table | Rows | Purpose |
|-------|------|---------|
| books | 110 | Book-level metadata (title, slug, release) |
| book_entries | 1158 | Individual lore entries within the books |
| transcripts | 1229 | Quest transcript headers |
| transcript_lines | 69499 | Canon dialogue (speaker, line, norm_line) |
| grimoire_cards | 2889 | Destiny 1 grimoire cards |
| interactions | 2699 | Single/short dialogue beats by character |
| items | 58764 | Weapons, armor, gear lore + flavor text |
| records | 71 | Triumphs/seals with canonical text |
| characters | 18 | Named characters extracted from dialogue |
| character_lines | 1189 | Character-quotes ready for agent use |
| fts | 135080 | FTS5 full-text search over all tables |
| meta | 1 | DB version + last updated |

## Repository layout

```
db/  - query.py + schema.sql + README.md + migrate.py (grimoire.db is built, not committed)
source/  - raw markdown source (books/, cards/, transcripts/, records/, items/, interactions/)
compendium/  - character quote index; feeds the characters/character_lines tables at migration (agents should prefer the database)
archive/  - raw scraper data (JSONL)
scripts/  - ingestion scripts
tests/  - audit + CI scripts (DB-backed)
skills/  - agent-facing SKILL.md
index.md  - brief overview pointing to the database
destiny-1-legacy-card-index.md  - archived pre-database D1 card index (historical)
```

## How agents should use this

1. Load `skills/destiny-grimoire/SKILL.md` into your agent registry.
2. Query via `db/query.py` for all structured lookups. Tiny context footprint.
3. Only load `compendium/characters/<slug>.md` if you need quote-arrays as plain markdown fallback.
4. Never parse raw markdown of `source/` unless strictly necessary.
5. The DB lives in one file. No external connections, no web scraping needed at runtime.

## Database schema

See `db/schema.sql`. Tables that matter to agents:

### `transcript_lines`
```sql
SELECT t.title, tl.speaker, tl.line
FROM transcript_lines tl
JOIN transcripts t ON t.id = tl.transcript_id
WHERE tl.speaker LIKE '%Eris%';
```

### `items` (by category)
```sql
SELECT slug, title, text, item_type FROM items 
WHERE item_type LIKE '%Exoth%' AND text != '' LIMIT 20;
```

### `fts` (full-text search across all tables)
```sql
SELECT title, text FROM fts WHERE fts MATCH 'crota' LIMIT 5;
```

## Repo philosophy

- **Database first.** The markdown corpus in `source/` is the ingestion source. Query via database.
- **Token-minimal.** Agents should query rather than read files. One database call gives canonical lore.
- **Agnostic.** No specific agent persona lives here. Drifter and Eris agents reference this DB via `lore/` symlink.

## Update procedure

```bash
# scrape more content from Ishtar Collective
python3 archive/scrape.py interactions <start> <end>
python3 archive/scrape.py items <start> <end>

# re-run the database migration
python3 db/migrate.py

# sync documentation count claims to the database
python3 tests/sync-doc-counts.py

# verify
bash tests/test-db.sh
bash eris-master-audit.sh
bash drifter-master-audit.sh
```

## Rules

1. No em-dashes or en-dashes anywhere in agent files.
2. No unverified quotes: everything in `character_lines` traces to canonical transcript lines.
3. Do not paraphrase lore as quotes. Use the verbatim text from the DB.
4. Do not edit the markdown source unless adding new Ishtar data.
5. Content sourced from https://www.ishtar-collective.net (Ishtar Collective).

## Attribution

Fan-made archive. Not affiliated with or endorsed by Bungie.

- **Destiny 2** and Destiny 1: © Bungie, Inc. All lore, characters, locations are Bungie's property.
- **Ishtar Collective** (https://www.ishtar-collective.net): Primary source for all ingested text.
- **Destiny Lore Vault** (YouTube) and **Destinypedia**: Bootstrap sources for specific transcripts.
