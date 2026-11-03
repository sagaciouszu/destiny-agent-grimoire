---
name: destiny-grimoire
description: 'Query the Destiny Agent Grimoire for verified Destiny lore, character dialogue, seal/triumph records, item flavor text, Hive/Oryx/Savathûn canon, grimoire cards and more. Use when an agent needs to pull canonical Destiny lore, look up character quotes, search factions, get item flavor text, check book transcripts, or complete conversations involving specific characters. Triggers: destiny, lore, grimoire, character lines, transcript, book, quote, faction, location, Obelisk, Hive, Crota, Oryx, Savathûn, Eris Morn, Drifter, Gambit.'
license: MIT
metadata:
  tags: "Destiny, Lore, Grimoire, Characters, Transcripts, Books, Items, Records"
  category: "reference"
---

# Destiny Agent Grimoire

Agent-optimized Destiny lore archive. Query via SQLite. Single file, no external APIs.
Use this when you need canonical Destiny lore for storytelling, lore check, agent persona, or fact-checking.

## Location

- Repo root: wherever you cloned `destiny-agent-grimoire`
- **Primary:** `db/grimoire.db` (SQLite + FTS5; if missing, bootstrap: `curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db` for the prebuilt asset, or `python3 db/migrate.py` to build from checkout)
- **Consumed by:** the Drifter and Eris agents via `lore/` (symlink or clone)

## Data covering

| Table | Rows | Content |
|-------|------|---------|
| books | 110 | Book metadata |
| book_entries | 1158 | Lore entries within books |
| transcripts | 1229 | Quest transcript headers |
| transcript_lines | 71221 | Canon character dialogue |
| grimoire_cards | 2889 | Destiny 1 grimoire cards |
| interactions | 2699 | Short character dialogue beats |
| items | 58764 | Weapons / armor / gear lore + flavor |
| records | 71 | Triumphs / seals |
| characters | 18 | Named characters |
| character_lines | 1189 | Canon character quotes for agents |
| fts | 136802 | FTS5 search index |

## How to query

Use `db/query.py` for everything. Interface wraps common patterns.

```bash
# Full-text search
python3 db/query.py search "Crota" --limit 5
python3 db/query.py search "Eris" --type transcripts --limit 10
python3 db/query.py search "hive" --type books

# Character dialogue
python3 db/query.py character "eris" --limit 20
python3 db/query.py character "drifter" --limit 20
python3 db/query.py character "saint-14" --limit 20

# Item details
python3 db/query.py item "0a0x-nightmask"

# Database stats
python3 db/query.py stats

# Discovery (cheap)
python3 db/query.py list books --limit 50
python3 db/query.py list characters
python3 db/query.py list speakers --limit 20

# Quote safety: verify before quoting
python3 db/query.py verify "I am Eris Morn."
```

## Interface flags

- `--json` on every command (compact, parse-friendly)
- `search` returns snippets by default; `--full` for complete text
- `search --type books|transcripts|grimoire|interactions|items|records`
- `character --about <term>` filters, `character --all` uses raw transcript lines
- `verify` exits 1 when the quote is not in canon

## MCP server (optional)

For clients that cannot run shell commands, the same tools are available over
the Model Context Protocol:

```bash
bash mcp-server/install.sh     # once: venv + official SDK
# register mcp-server/run.sh in the client (install.sh prints the snippet)
```

It ships with this archive, so one install serves every agent that mounts it.

Tools: `search`, `character`, `item`, `verify`, `list_records`, `stats`. The
server is read-only, exposes no arbitrary SQL, clamps limits to 1-100 and trims
full text to 4000 characters. Full details: `mcp-server/README.md`.

## Extras

- `db/capabilities.json` - interface manifest (tables, commands, contracts)
- `SELECT * FROM v_speakers;` - canonical speakers with line counts
- `SELECT * FROM speaker_aliases;` - alias -> canonical mapping

## Direct SQL (advanced)

```bash
sqlite3 db/grimoire.db "SELECT title, text FROM fts WHERE fts MATCH 'hive' LIMIT 5"
sqlite3 db/grimoire.db "SELECT speaker, line FROM transcript_lines WHERE speaker LIKE '%Eris%' LIMIT 10"
sqlite3 db/grimoire.db "SELECT slug, title, item_type, text FROM items WHERE item_type LIKE '%Exotic%' AND text != '' LIMIT 20"
```

## Rules

1. **Only use verified quotes.** Canon is what lives in `transcript_lines` and `character_lines`. Do not paraphrase lore as quotes.
2. **SQLite-first.** Do not read raw markdown from `source/` at query time; it is only the ingestion source.
3. **Keep queries scoped.** Small `--limit N` values preserve token budget.
4. **Do not edit this data directly.** The migration reads `source/` markdown + `archive/data/*.jsonl` and rebuilds the DB.
5. **Eris Morn and The Drifter agents** both consume this database via `lore/` (a symlink to or a clone of this repo).

## Sources

Text content sourced from https://www.ishtar-collective.net (Ishtar Collective).
Cutscene transcripts come from YouTube captions (auto-generated; corroboration-verified).
Bungie Inc owns all Destiny property. Fan-built, not affiliated.
