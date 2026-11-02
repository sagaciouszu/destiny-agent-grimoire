# Release v1.1.0 - Destiny Agent Grimoire

**Date:** 2026-11-02

## What is this

SQLite-backed Destiny lore archive for agent consumption. Single file (`db/grimoire.db`, 93 MB), no external connections. All content ingested from the Ishtar Collective across every content type they host.

## Data totals (db/grimoire.db)

| Table | Rows | Coverage |
|-------|------|----------|
| books | 110 | All 110 Ishtar lore books (complete) |
| book_entries | 1158 | 1-51 entries per book |
| transcripts | 68 | 68 quest transcripts |
| transcript_lines | 1709 | Every dialogue line, including narration |
| grimoire_cards | 2889 | All 2889 Destiny 1 grimoire cards (complete) |
| interactions | 2699 | All 135 Ishtar interaction pages |
| items | 58764 | All Ishtar items; 42693 with flavor text |
| records | 71 | All 71 triumphs/seals |
| characters | 18 | Named characters extracted from dialogue |
| character_lines | 1054 | Verified canon dialogue for queries |
| fts | 67290 | FTS5 full-text search over all tables |

Coverage verified by diffing scraped slugs against Ishtar's live pages: no missing slugs.

## What changed since v1.0.0

### db/
- `db/migrate.py` widened parsers: quoted-source books, YT/weblore transcripts as speaker rows, prose as `Narration`
- `norm_text` / `norm_line` / `norm_body` columns + indexes for SQL substring matching
- Quote verification scripts are DB-backed (~2s for 2893 quotes)

### cleanup
- `source/items/` and `source/interactions/` removed (items live in `archive/data/items.jsonl`; interactions in `archive/data/interactions.jsonl`)
- `source/` trimmed to exactly what `db/migrate.py` consumes: books, transcripts, cards, records
- Legacy JSON indices and markdown card index already removed in v1.0.0

### docs
- README, index.md, db/README.md, SKILL.md rewritten DB-first with current counts
- CHANGELOG consolidated

## Agents consuming this database

- **how-to-drift-for-agents** (v0.4.0): Drifter persona, 75 files, `lore/` symlink
- **eris-morn** (v0.2.0): Eris persona, 51 files, `lore/` symlink

Both agents query `db/query.py` or raw SQL; neither parses `source/` markdown at runtime.

## Test results

- drifter-master-audit.sh: 17/17 PASS
- eris-master-audit.sh (this repo): 6/6 PASS
- eris-master-audit.sh (eris-morn): 3/3 PASS
- test-db.sh: 29/29 PASS
- lore-integrity.sh: 17/17 PASS
- conversation tests: 2/2 PASS (all queries hit SQLite)
- drifter-quote-verify.sh: 2893 checked, 0 unverified, ~2s
- eris-quote-verify.sh: 0 unverified

## Attribution

All content sourced from https://www.ishtar-collective.net (Ishtar Collective).
Fan-made. Not affiliated with or endorsed by Bungie.
