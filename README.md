# Destiny Agent Grimoire

<p align="center">
  <img src='https://img.shields.io/github/v/tag/sagaciouszu/destiny-agent-grimoire?label=version&color=blue' alt='Version'/>
  <img src='https://github.com/sagaciouszu/destiny-agent-grimoire/actions/workflows/ci.yml/badge.svg' alt='CI'/>
  <img src='https://img.shields.io/badge/books-110-orange' alt='Books'/>
  <img src='https://img.shields.io/badge/transcripts-68-orange' alt='Transcripts'/>
  <img src='https://img.shields.io/badge/quotes-473%20verified-orange' alt='Quotes'/>
  <img src='https://img.shields.io/badge/Made%20with-Motes-00FF00' alt='Made with Motes'/>
  <img src='https://img.shields.io/badge/Made%20with-Parts%20of%20Ghosts-FFFFFF' alt='Made with Parts of Ghosts'/>
</p>

<p align="center">
  <img src="header.png" alt="Destiny Agent Grimoire - Your Ghost Is Not An Agent" width="100%"/>
</p>

**Version:** 0.3.0 | **Status:** Development

> ⚠️ **WARNING:** This repository is under heavy development while the knowledge base is being constructed. Expect frequent changes, incomplete data, and shifting structure. The author's prowess is not to be trusted with anything important. Use at your own risk.

A shared, indexed repository of Destiny 2 lore ingested from the Ishtar Collective.
Any agent (Drifter persona, lore research, etc.) may reference these files at will.

## Structure

- `db/grimoire.db` - SQLite database (primary data store, FTS5 search).
- `db/query.py` - Agent query interface (search, character, item, stats).
- `db/schema.sql` - Database DDL.
- `db/README.md` - Query examples and table reference.
- `compendium/` - Agent-optimized character line index (markdown fallback).
- `destiny-1/` - Destiny 1 grimoire (complete, 2889 cards, markdown).
- `interactions/` - Character dialogue index (markdown).
- `items/` - Gear lore (markdown).
- `records/` - Triumphs and seals (markdown).
- `scripts/` - Ingestion scripts.
- `tests/` - Validation scripts.
- `archive/` - Raw scrape data (JSONL).
- `drifter-master-audit.sh` - Unified audit runner.

## How to use

1. Query the database: `python3 db/query.py search "keyword" --limit 5`
2. Character lines: `python3 db/query.py character "eris" --limit 20`
3. Item details: `python3 db/query.py item "<slug>"`
4. Database stats: `python3 db/query.py stats`
5. Direct SQL: `sqlite3 db/grimoire.db "SELECT ... FROM fts WHERE fts MATCH 'keyword'"`

## Ingestion rules

- Only lore body text is kept - site navigation, headers, footers, category lists, timeline widgets, and "Discuss this transcript" links are stripped.
- If an entry cannot be fetched, the book is marked `partial` with a note; nothing is invented.
- Capitalization matters: "Guardian" (capitalized) generally refers to the player character.

## Source & Attributions

All content sourced from https://www.ishtar-collective.net (Ishtar Collective).
Book list mirrored from https://www.ishtar-collective.net/books.

Fan-made collection. Not affiliated with or endorsed by Bungie.

- **Destiny 2** - © Bungie, Inc. All lore, characters, locations are Bungie's property.
- **Ishtar Collective** (https://www.ishtar-collective.net) - Primary source for all ingested lore text.
- **Destiny Lore Vault** (YouTube) - Audio recordings of key transcripts.

All content sourced from publicly available Destiny 2 lore. No original creative content is claimed.

## Progress

Database-first archive: 110 books, 68 transcripts, 2889 Destiny 1 cards, 2699+ interactions, 58764 items, 71 records, 18 characters (1054 lines). FTS5 search enabled.
Last scrape: 2026-10-30. Content through Renegades (Dec 2025).

## Audit Commands
- `bash tests/validate.sh` - consistency check (quotes, links, index)
- `bash tests/drifter-test-suite.sh` - voice validation (19 scenarios)
- `bash tests/drifter-module-test.sh` - module checks (201 checks)
- `bash drifter-master-audit.sh` - unified audit (17 suites)
- `bash tests/drifter-quote-verify.sh` - quote verification
- `bash tests/drifter-ci.sh` - full CI pipeline (25 checks)
- `bash tests/lore-integrity.sh` - archive integrity (8 checks)
- `bash tests/lore-quote-count.sh` - quote count (473 lines)
- `bash tests/lore-format.sh` - transcript format (68/68)
