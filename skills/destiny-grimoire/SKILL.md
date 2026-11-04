---
name: destiny-grimoire
description: 'Query the Destiny Agent Grimoire for verified Destiny lore, character dialogue, raids, dungeons, seasonal activities, seasons and rotating events, seal/triumph records, item flavor text, Hive/Oryx/Savathûn canon and grimoire cards. Use when an agent needs canonical Destiny lore, activity or season coverage, character quotes, factions, item flavor text, book transcripts, or conversations involving specific characters. Triggers: destiny, lore, grimoire, character lines, transcript, book, quote, faction, raid, dungeon, season, episode, Festival of the Lost, Dawning, Solstice, Guardian Games, Iron Banner, Menagerie, Hive, Crota, Oryx, Savathûn, Eris Morn, Drifter, Gambit.'
license: MIT
metadata:
  tags: "Destiny, Lore, Grimoire, Characters, Transcripts, Books, Items, Records, Raids, Dungeons, Seasons, Events"
  category: "reference"
---

# Destiny Agent Grimoire

Agent-optimized Destiny lore archive. Query via SQLite. Single file, no external APIs.
Use this when you need canonical Destiny lore, activity/season/event coverage,
storytelling, lore checks, agent personas, or fact-checking.

## Location

- Repo root: wherever you cloned `destiny-agent-grimoire`
- **Primary:** `db/grimoire.db` (SQLite + FTS5; if missing, bootstrap: `curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db` for the prebuilt asset, or `python3 db/migrate.py` to build from checkout)
- **Consumed by:** the Drifter, Eris Morn and Calus agents via `lore/` (symlink or clone)

## Data covering

| Table | Rows | Content |
|-------|------|---------|
| books | 110 | Book metadata |
| book_entries | 1158 | Lore entries within books |
| transcripts | 1230 | Quest transcript headers |
| transcript_lines | 71466 | Canon character dialogue |
| grimoire_cards | 2889 | Destiny 1 grimoire cards |
| interactions | 2699 | Short character dialogue beats |
| items | 58764 | Weapons / armor / gear lore + flavor |
| records | 71 | Triumphs / seals |
| characters | 20 | Named characters |
| character_lines | 1229 | Canon character quotes for agents |
| fts | 120976 | FTS5 search index |
| verify_fts | 120731 | Fast quote verification index |
| item_title_fts | 58764 | Item title lookup index |

Taxonomy tables (additive; canon tables are never rewritten):

| Table | Rows | Content |
|-------|------|---------|
| expansions | 18 | Destiny 1 through Renegades |
| seasons | 26 | Official numeric seasons; 24-26 are episodes |
| activities | 65 | Raids, dungeons, seasonal activities, missions |
| events | 9 | Festival, Dawning, Solstice, Guardian Games, Crimson Days, Revelry, Moments of Triumph, Bungie Day, Iron Banner |
| event_occurrences | 72 | Event year, dates and season |
| transcript_classification | 1229 | Activity/season/event per transcript with confidence |
| item_classification | 58764 | Season/event per item |
| document_classification | 181 | Season/event per book or record |

## How to query

Use `db/query.py` for everything. Interface wraps common patterns.

```bash
# Full-text search
python3 db/query.py search "Crota" --limit 5
python3 db/query.py search "Eris" --type transcripts --limit 10
python3 db/query.py search "hive" --type books

# Faceted discovery
python3 db/query.py search "calus" --season 7 --limit 5
python3 db/query.py search "nightmare" --activity nightmare-containment
python3 db/query.py search "shaxx" --event "Iron Banner"
python3 db/query.py search "witness" --expansion "The Final Shape"

# Activity / season / event browsing
python3 db/query.py coverage
python3 db/query.py list activities --limit 30
python3 db/query.py list seasons
python3 db/query.py list events
python3 db/query.py activity menagerie
python3 db/query.py event festival-of-the-lost

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
python3 db/query.py verify "Absolutely not." --speaker "Eris Morn" --exact
```

## Interface flags

- `--json` on every command (compact, parse-friendly)
- `search` returns snippets by default; `--full` for complete text
- `search --type books|transcripts|grimoire|interactions|items|records`
- `search --activity`, `--season`, `--event`, `--expansion` filter by taxonomy
- `--season` accepts a number (`7`), a slug (`season-of-opulence`) or a name
  fragment (`opulence`); episodes work the same way (`24`, `echoes`)
- `character --about <term>` filters, `character --all` uses raw transcript lines
- `verify` exits 1 when the quote is not in canon
- `search` accepts unquoted multi-word input; punctuation is treated literally
  when it is not valid FTS5 syntax
- `verify --speaker` matches on name boundaries and ignores a leading "The":
  `Eris` and `Drifter` pass, `ris` and `Morn` do not

## Taxonomy

Four independent axes, documented in `docs/TAXONOMY.md`:

- **expansion:** Forsaken, Shadowkeep, Beyond Light, The Witch Queen, Lightfall,
  The Final Shape, The Edge of Fate, Renegades
- **season:** Bungie's official number 1-23; episodes 24-26 with acts
- **activity:** raid, dungeon, seasonal, story, patrol, exotic mission and more
- **event:** rotating events with one row per year

Classification carries `explicit`, `derived`, `manual` or `unknown`. `unknown`
means the source did not say; it is never guessed. Vaulted content is tagged and
stays searchable.

## MCP server (optional)

For clients that cannot run shell commands, the same tools are available over
the Model Context Protocol:

```bash
bash mcp-server/install.sh     # once: venv + official SDK
# register mcp-server/run.sh in the client (install.sh prints the snippet)
```

It ships with this archive, so one install serves every agent that mounts it.

Tools: `search`, `character`, `item`, `verify`, `list_records`, `stats`,
`book`, `transcript`, `find_item`, `record`, `verify_many`, `character_info`,
`activities`, `activity`, `seasons`, `events`, `event`, `coverage`.
`search` also takes `activity`, `season`, `event` and `expansion`.
Resources: `grimoire://books`,
`grimoire://characters`, `grimoire://records`, `grimoire://stats`, plus
`grimoire://book/{slug}` templates. The
server is read-only, exposes no arbitrary SQL, clamps limits to 1-100 and trims
full text to 4000 characters. Full details: `mcp-server/README.md`.

## Extras

- `db/capabilities.json` - interface manifest (tables, commands, contracts)
- `SELECT * FROM v_speakers;` - canonical speakers with line counts
- `SELECT * FROM v_activity_coverage;` - activity coverage and gaps
- `SELECT * FROM v_season_coverage;` - season coverage
- `SELECT * FROM v_event_coverage;` - event coverage
- `SELECT * FROM v_transcript_taxonomy;` - transcript classification
- `SELECT * FROM speaker_aliases;` - alias -> canonical mapping

## Direct SQL (advanced)

```bash
sqlite3 db/grimoire.db "SELECT title, text FROM fts WHERE fts MATCH 'hive' LIMIT 5"
sqlite3 db/grimoire.db "SELECT speaker, line FROM transcript_lines WHERE speaker LIKE '%Eris%' LIMIT 10"
sqlite3 db/grimoire.db "SELECT slug, title, item_type, text FROM items WHERE item_type LIKE '%Exotic%' AND text != '' LIMIT 20"
sqlite3 db/grimoire.db "SELECT * FROM v_activity_coverage ORDER BY lines DESC LIMIT 20"
```

## Rules

1. **Only use verified quotes.** Canon is what lives in `transcript_lines` and `character_lines`. Do not paraphrase lore as quotes. Run `verify` with the speaker and `--exact` before quoting; if it fails, do not quote the line.
2. **SQLite-first.** Do not read raw markdown from `source/` at query time; it is only the ingestion source.
3. **Keep queries scoped.** Small `--limit N` values preserve token budget.
4. **Do not edit this data directly.** The migration reads `source/` markdown + `archive/data/*.jsonl` and rebuilds the DB.
5. **Eris Morn, The Drifter and Calus** consume this database via `lore/` (a symlink to or a clone of this repo).
6. **Respect confidence.** Treat `unknown` classification as unknown; do not present a guessed season or activity as fact.

## Sources

Text content sourced from https://www.ishtar-collective.net (Ishtar Collective).
Cutscene transcripts come from YouTube captions (auto-generated; corroboration-verified).
Bungie Inc owns all Destiny property. Fan-built, not affiliated.
