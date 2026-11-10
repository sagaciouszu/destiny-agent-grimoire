---
name: destiny-grimoire
description: 'Query verified Destiny lore: quotes, seasons, raids, seals, items; Calus, Zavala, Ghost, Eris, Drifter. Triggers: lore, grimoire, quote, hive, gambit.'
license: MIT
metadata:
  tags: "Destiny, Lore, Grimoire, Characters, Transcripts, Books, Items, Records, Raids, Dungeons, Seasons, Events"
  category: "reference"
---

# Destiny Agent Grimoire

Agent-optimized Destiny lore archive. Query via SQLite; no network calls at
query time. Use this when you need canonical Destiny lore,
activity/season/event coverage, storytelling, lore checks, agent personas, or
fact-checking.

<details>
<summary>Extended trigger terms (keep in mind while deciding to activate)</summary>

destiny, lore, grimoire, character lines, transcript, book, quote, faction,
raid, dungeon, season, episode, Festival of the Lost, Dawning, Solstice,
Guardian Games, Iron Banner, Menagerie, Hive, Crota, Oryx, Savathûn,
Eris Morn, Drifter, Calus, Zavala, Ghost, Gambit, seal, triumph, item,
flavor text, verify.

</details>

## Location

- Repo root: wherever you cloned `destiny-agent-grimoire`
- **Primary:** `db/grimoire.db` (SQLite + FTS5; if missing, bootstrap: `curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db` for the prebuilt asset (smaller: same endpoint with `.xz` / `.gz`, decompress with `xz -d` / `gzip -d`), or `python3 db/migrate.py` to build from checkout)
- **Consumed by:** all six agents (Drifter, Eris Morn, Calus, Zavala, Ghost, Mara Sov) via `lore/` (symlink, Windows junction or clone)

## Data covering

| Table | Rows | Content |
|-------|------|---------|
| books | 110 | Book metadata |
| book_entries | 1158 | Lore entries within books |
| transcripts | 9229 | Transcript headers (quests, web, cutscenes, game captions) |
| transcript_lines | 125324 | Canon dialogue and game captions by speaker |
| grimoire_cards | 2889 | Destiny 1 grimoire cards |
| interactions | 2699 | Short character dialogue beats |
| items | 58764 | Weapons / armor / gear lore + flavor |
| records | 69 | Triumphs / seals |
| characters | 20 | Named characters |
| character_lines | 1229 | Canon character quotes for agents |
| caption_provenance | 56119 | Caption line provenance (StringReference hash, package) |
| speaker_source | 206 | Attribution provenance on caption lines (ishtar_containment/dialogue_node/line_prefix) |
| fts | 176794 | FTS5 search index |
| verify_fts | 176794 | Fast quote verification index |
| item_title_fts | 58764 | Item title lookup index |
| entities | 89 | Named entities (char/power/faction/place) |
| entity_aliases | 136 | Attested name variants per entity |
| entity_links | 33578 | Entity to document links with weights |
| entity_relations | 4 | Entity to entity links (adjacency, primevals) |

Taxonomy tables (additive; canon tables are never rewritten):

| Table | Rows | Content |
|-------|------|---------|
| expansions | 18 | Destiny 1 through Renegades |
| seasons | 28 | Official numeric seasons; 24-26 are episodes |
| activities | 71 | Raids, dungeons, seasonal activities, missions |
| events | 9 | Festival, Dawning, Solstice, Guardian Games, Crimson Days, Revelry, Moments of Triumph, Bungie Day, Iron Banner |
| event_occurrences | 72 | Event year, dates and season |
| transcript_classification | 9229 | Activity/season/event per transcript with confidence |
| item_classification | 58764 | Season/event per item |
| document_classification | 179 | Season/event per book or record |
| lore_entries | 2962 | Bungie manifest lore entries |
| manifest_activities | 3744 | Full manifest activity catalogue |
| seals | 70 | Manifest seals |
| seal_records | 1004 | Triumph records per seal |

## How to query

Use `db/query.py` for everything. Interface wraps common patterns.

```bash
# Full-text search
python3 db/query.py search "Crota" --limit 5
python3 db/query.py search "Eris" --type transcripts --limit 10
python3 db/query.py search "hive" --type books
python3 db/query.py search "bank under attack" --type captions --limit 5

# Faceted discovery
python3 db/query.py search "calus" --season 7 --limit 5
python3 db/query.py search "nightmare" --activity nightmare-containment
python3 db/query.py search "crucible" --event "Iron Banner"
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
python3 db/query.py find-item "Riskrunner"          # search items by name
python3 db/query.py character-info "Eris Morn"      # curated vs spoken line counts

# Books, transcripts, records and seals
python3 db/query.py book book-a-drifters-gambit --limit 5
python3 db/query.py transcript contact-io --speaker "Eris Morn" --limit 20
python3 db/query.py record am-i-to-cast-a-shadow
python3 db/query.py seals
python3 db/query.py seal 2185719388

# Database stats
python3 db/query.py stats

# Entity web (schema 1.7.0): resolve any attested name to its entity
python3 db/query.py entity "Saint-14"
python3 db/query.py entity "Elsie Bray"
python3 db/query.py entity "Xivu Arath" --json
python3 db/query.py search "witness" --entity "The Witness" --limit 5

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
- `search --type books|transcripts|grimoire|interactions|items|records|lore|captions`
- `search --lang <code>` filters by document language (every row is `en` today;
  caption languages drop in later as data)
- `seals` / `seal <hash-or-name>` / `record <slug>` for seals, triumphs and records
- `search --activity`, `--season`, `--event`, `--expansion` filter by taxonomy
- `--class hunter|titan|warlock` adds class variants to base lines (`search`,
  `character`, `transcript`); `--canon-only` excludes optional and class
  variants (`character`, `transcript` only)
- `--offset` pages paged reads (`search`, `list`, `character`, `transcript`,
  `book`, `find-item`, `activity`); `verify-many` checks several quotes in one
  call
- `--season` accepts a number (`7`), a slug (`season-of-opulence`) or a name
  fragment (`opulence`); episodes work the same way (`24`, `echoes`)
- `character --about <term>` filters, `character --all` uses raw transcript lines
- `transcript <slug>` adds `--section`, `--include-stage`, `--full`
- `verify` exits 1 when the quote is not in canon
- `search` accepts unquoted multi-word input; punctuation is treated literally
  when it is not valid FTS5 syntax
- `verify --speaker` matches on name boundaries and ignores a leading "The":
  `Eris` and `Drifter` pass, `ris` and `Morn` do not

## Taxonomy

Four independent axes, documented in `docs/TAXONOMY.md`:

- **expansion:** Forsaken, Shadowkeep, Beyond Light, The Witch Queen, Lightfall,
  The Final Shape, The Edge of Fate, Renegades
- **season:** Bungie's official number 1-28; episodes 24-26 keep their numeric
  slot with acts, and seasons resume at 27
- **activity:** raid, dungeon, seasonal, story, patrol, exotic mission and more
- **event:** rotating events with one row per year

Classification carries `explicit`, `derived`, `manual` or `unknown`. `unknown`
means the source did not say; it is never guessed. Vaulted content is tagged and
stays searchable.

Coverage gaps carry a `coverage_notes` row instead of silence: `no_dialogue`,
`narration_only`, `dialogue_source_missing`, `partial_transcript` or
`unverified`. `partial_transcript` means the lines are real but the transcript
is not exhaustive — do not present it as complete.

## MCP server (optional)

For clients that cannot run shell commands, the same tools are available over
the Model Context Protocol:

```bash
bash mcp-server/install.sh     # once: venv + official SDK
# register mcp-server/run.sh in the client (install.sh prints the snippet)
```

It ships with this archive, so one install serves every agent that mounts it.

Tools: `search`, `entity`, `character`, `item`, `verify`, `list_records`, `stats`,
`book`, `transcript`, `find_item`, `record`, `verify_many`, `character_info`,
`activities`, `activity`, `seasons`, `events`, `event`, `coverage`, `seals`,
`seal`, `lore` — the same reads the CLI offers.
`search` also takes `activity`, `season`, `event`, `expansion` and `entity`.
`entity` resolves a name to its entity (aliases, relations, document counts,
fuzzy-flagged candidates when nothing matches exactly).
Resources: `grimoire://books`,
`grimoire://characters`, `grimoire://records`, `grimoire://stats`,
`grimoire://entities`, `grimoire://activities`, `grimoire://seasons`,
`grimoire://events`, `grimoire://coverage`, plus `grimoire://book/{slug}`,
`grimoire://transcript/{slug}`, `grimoire://character/{slug}` and
`grimoire://record/{slug}` templates. The
server is read-only, exposes no arbitrary SQL, clamps limits to 1-100 and trims
full text to 4000 characters. Full details: `mcp-server/README.md`.

## Extras

- `db/capabilities.json` - interface manifest (tables, commands, contracts)
- `SELECT * FROM v_speakers;` - canonical speakers with line counts
- `SELECT * FROM v_entity_resolve;` - alias + norm lookup to entities
- `SELECT * FROM v_entity_documents;` - entity to ranked document list
- `SELECT * FROM v_entity_coverage;` - per-kind entity web coverage
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
5. **All six agents** (`destiny-agent-drifter`, `destiny-agent-eris-morn`, `destiny-agent-calus`, `destiny-agent-zavala`, `destiny-agent-ghost`, `destiny-agent-mara-sov`) consume this database via `lore/` (a symlink, Windows junction or clone of this repo).
6. **Respect confidence.** Treat `unknown` classification as unknown; do not present a guessed season or activity as fact.
7. **Mind coverage status.** `coverage_notes` says what the archive lacks: `partial_transcript` lines are real but incomplete, `no_dialogue` activities have none. Never fill a gap with an invented line.

## Sources

- **Ishtar Collective** (https://www.ishtar-collective.net): the archival
  primary — main-site transcripts plus tagged and untagged Commons topics.
- **Destinypedia** (https://www.destinypedia.com): verbatim transcripts used as
  corroboration and for specific activity dialogue.
- **Captions**: reviewed captions, auto-captions and cutscene compilations from
  YouTube (corroboration-verified; video credits in `README.md`).

`transcripts.source_tier` records precedence; lower tiers stay searchable and
are not promoted without a better source, and a caption-tier transcript is
never presented as verbatim. Full provenance rules: `STANDARDS.md`.
Bungie Inc owns all Destiny property. Fan-built, not affiliated.
