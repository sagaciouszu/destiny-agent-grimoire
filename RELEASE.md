# Release v1.2.0 - Destiny Agent Grimoire

**Date:** 2026-11-02

## What is this

SQLite-backed Destiny lore archive for agent consumption. Single file (`db/grimoire.db`, 121 MB), no external connections. Built from the committed sources via `python3 db/migrate.py`; the prebuilt database is attached to this release as an asset. All content ingested from the Ishtar Collective across every content type they host.

## Data totals (db/grimoire.db)

| Table | Rows | Coverage |
|-------|------|----------|
| books | 110 | All 110 Ishtar lore books (complete) |
| book_entries | 1158 | 1-51 entries per book |
| transcripts | 1225 | Quest + cutscene + web transcripts (complete) |
| transcript_lines | 69213 | Every dialogue line, including narration |
| grimoire_cards | 2889 | All 2889 Destiny 1 grimoire cards (complete) |
| interactions | 2699 | All 135 Ishtar interaction pages |
| items | 58764 | All Ishtar items; 42693 with flavor text |
| records | 71 | All 71 triumphs/seals |
| characters | 18 | Named characters extracted from dialogue |
| character_lines | 1189 | Verified canon dialogue for queries |
| fts | 134794 | FTS5 full-text search over all tables |

Coverage verified by diffing scraped slugs against Ishtar's live pages: no missing slugs.

## What changed since v1.0.0

### db/
- `db/migrate.py` widened parsers: quoted-source books, YT/weblore transcripts as speaker rows, prose as `Narration`
- `norm_text` / `norm_line` / `norm_body` columns + indexes for SQL substring matching
- Quote verification scripts are DB-backed (~3s for 2897 quotes), with sentence-level matching for quotes that drop mid-line attributions

### new sources
- All 1130 additional Ishtar transcript pages scraped (`archive/data/transcripts_web.jsonl`), junk footer rows filtered
- 19 cutscene compilation transcripts from a 30-video archive (`archive/data/cutscenes.jsonl`): captions only, no video download; unique-match speaker attribution against known dialogue

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
- eris-master-audit.sh (this repo): 7/7 PASS (incl. cutscene caption verification)
- eris-master-audit.sh (eris-morn): 8/8 PASS
- test-db.sh: 29/29 PASS
- lore-integrity.sh: 17/17 PASS
- conversation tests: 2/2 PASS (all queries hit SQLite)
- drifter-quote-verify.sh: 2897 checked, 0 unverified, ~3s
- eris-quote-verify.sh: 678 checked, 0 unverified

## Attribution

All content sourced from https://www.ishtar-collective.net (Ishtar Collective).
Fan-made. Not affiliated with or endorsed by Bungie.
