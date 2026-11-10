# Destiny Grimoire Database

SQLite database for the Destiny lore repository. Single file, no external connections, no APIs.

File: `grimoire.db` (SQLite, FTS5 full-text search enabled). Built from `source/` + `archive/` by `migrate.py`; not committed, prebuilt copies attached to releases.

Full build/provenance matrix: [`docs/wiki/Builds.md`](../docs/wiki/Builds.md).

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

# Entity web (schema 1.7.0): resolve any attested alias to its entity
python3 db/query.py entity "Saint-14"
python3 db/query.py entity "Elsie Bray" --json
python3 db/query.py search "witness" --entity "The Witness" --limit 5

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
| `transcripts` | 9229 transcript headers (quest + cutscene + web) |
| `transcript_lines` | Canonical dialogue by speaker; `speaker_source` set for attributed caption lines |
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

### Entity web (additive, schema 1.7.0)

| Table | Purpose |
|-------|---------|
| `entities` | 89 named entities: characters, powers, factions, places |
| `entity_aliases` | 136 attested name variants; `norm_alias` is the resolver key |
| `entity_links` | 33578 entity to document links with weights and match classes |
| `entity_relations` | 4 entity to entity links (adjacency, primeval pairs) |
| `entity_build_meta` | build audit trail (build_id, source hashes, timings) |

| View | Purpose |
|-------|---------|
| `v_entity_resolve` | resolver path: alias + norm lookup to entities |
| `v_entity_documents` | entity to ranked document list (weight DESC, ref) |
| `v_entity_coverage` | per-kind coverage (entities, linked, links) |

Build order: `python3 db/build_entity_web.py --db <copy>` creates and fills the
tables on a copy of the database (see v0.33.0 release notes for the swap
protocol and the books/cards SHA256 evidence). No existing table, view or
row is touched; books/lore/transcripts are read-only build input.

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
- `v_entity_resolve` / `v_entity_documents` / `v_entity_coverage` views - the entity web's public API
- `speaker_aliases` table - alias -> canonical mapping applied at migration
- `db/build_entity_web.py` - the entity web builder (temp copy, never the live file)

## Query pattern for agents

The canonical interface is `db/query.py` which wraps common SQL patterns. All results are returned to stdout as plain text. Use `--limit N` to bound output.

If you need raw SQL, the `fts` table is the easiest - a single `MATCH` returns content back from the original source.

## Regenerate the database

```bash
python3 db/migrate.py
sqlite3 db/grimoire.db "SELECT key, value FROM meta;"
```

The migration reads `source/` markdown plus `archive/data/*.jsonl` scratch files.
It **does not** build the manifest-derived tables (or the lore index); those
come from `python3 db/enrich_lore.py`, `enrich_manifest.py`, `enrich_seals.py`
and `enrich_itemsets.py --apply` after fetching the manifest with
`python3 archive/data/fetch_manifest.py --fetch --extract`. The full chain is
the release recipe documented in `docs/wiki/Testing-and-Auditing.md`.
