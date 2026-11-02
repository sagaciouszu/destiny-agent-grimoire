# Changelog

## v1.1.0 - Full coverage: Ishtar + web transcripts + cutscenes (2026-11-02)

### Coverage

- Verified full Ishtar Collective coverage: 0 missing item slugs, all 135 interaction pages, all 110 books, 2889 D1 cards, 71 records
- Scraped all 1130 additional Ishtar transcript pages (68 -> 1198 transcripts), incl. quest-step dialogue for every expansion
- Added 19 cutscene compilation transcripts (30-video archive, subtitle-only) with unique-match speaker attribution
- Database: 1219 transcripts, 60,847 transcript lines, 126,428 FTS entries

### Cleanup

- Removed redundant `source/items/` and `source/interactions/` markdown (items/interactions ingest from `archive/data/*.jsonl`)
- `source/` now contains exactly what `db/migrate.py` consumes: books, transcripts, cards, records
- RELEASE.md added with verified totals and test results

### Tests

- `drifter-quote-verify.sh`: sentence-level matching for dropped attributions; canon fragments split from raw lines (norm strips periods)
- `tests/lore-format.sh`: path fixed for `source/transcripts/` reorganization

## v1.0.0 - SQLite-first (2026-11-02)

### Highlights

- Migrated all lore from markdown to a single SQLite file: `db/grimoire.db`
- Added `norm_text` columns + indexes for SQL-based substring matching against all corpora
- 58,764 items, 2,699 interactions, 71 records complete
- FTS5 index over all tables
- Agents (Drifter, Eris) use `db/query.py` and `sqlite3 db/grimoire.db` for all lore lookups

### Database Tables (at release)

| Table | Rows | Purpose |
|-------|------|---------|
| books | 110 | Book metadata |
| book_entries | 1158 | Entries within books |
| transcripts | 68 | Quest transcript headers |
| transcript_lines | 1709 | Canon character dialogue |
| grimoire_cards | 2889 | Destiny 1 grimoire cards |
| interactions | 2699 | Character dialogue beats |
| items | 58764 | Weapons / armor / gear lore |
| records | 71 | Triumphs and seals |
| characters | 18 | Named characters |
| character_lines | 1054 | Character quotes |
| meta | 1 | DB version |

### Repository restructuring

- Markdown data moved to `source/` (books, cards, transcripts, records, items, interactions)
- `archive/` holds raw JSONL scraped output
- Legacy markdown indexes (`destiny-1-index.json`, `items-index.json`, `records-index.json`, `interactions/index.md`) removed
- Consolidated CHANGELOG (removed per-scrape entries)
- Reorganized test scripts: `tests/lore-integrity.sh` now 17/17 checks via SQLite

## Tests and audit

- `eris-master-audit.sh`: 6/6 pass
- `drifter-master-audit.sh`: 17/17 pass
- `tests/test-db.sh`: 29/29 pass
- `tests/lore-integrity.sh`: 17/17 pass
- `tests/drifter-quote-verify.sh`: 0 unverified (DB-backed, ~3s)
- `tests/conversation-test.sh`: PASS
- `tests/eris-conversation-test.sh`: PASS

## Contents sourced

- https://www.ishtar-collective.net (Ishtar Collective)
- YouTube cutscene compilations (captions only, no video download)
- Bungie Inc owns all Destiny property

## Summary

The lore archive is a SQLite database. Agents no longer parse markdown.
