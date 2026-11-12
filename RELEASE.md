# v0.42.1 - Dead tables removed (schema 1.13.0)

**2026-11-12**

Schema **1.13.0** release. Four derived tables with zero application readers
are dropped: `manifest_activities`, `manifest_links`, `item_sets` and
`item_set_members`. The database goes from 52 to 48 tables. The corpus is
unchanged (9,229 transcripts / 125,324 lines / 63,359 sightings / 176,794 FTS
rows).

## What's Changed
- Schema 1.13.0: drop `manifest_activities`, `manifest_links`, `item_sets`,
  `item_set_members`; 52 → 48 tables.
- `db/enrich_manifest.py`: no longer creates or fills tables; keeps manifest
  conflict reporting (`enrich_seals.py` is now the only table-creating enrich).
- `db/enrich_itemsets.py`: keeps `item_classification` updates; no table writes.
- `db/schema.sql`: already carried none of the four tables; no change needed.
- `db/capabilities.json`: four removed entries.
- `tests/taxonomy-deep-test.py`: `manifest()` check and registration removed;
  16 checks remain.
- Tests: `test-db.sh` gains one real check (68 total).
- Docs: README build chain, `db/README`, `STANDARDS`, `SKILL`, `Database.md`,
  `Testing-and-Auditing.md`, `Builds.md` schema history.
- Database: 269,221,888 bytes (~269 MB / 260 MiB-rounded), ~0.4 MB smaller.

## Test fix
`tests/test-db.sh` line 88 opened `""/path""` because `\"$DB\"` was nested in a
pre-expanded string, so `sqlite3` failed and the `-z` assertion passed
vacuously. The query now runs into a variable first; a negative control
confirms the check fails when `verify_fts` is present.

## Verify
- Full from-source rebuild: migrate → queen-fold → enrich_lore →
  enrich_seals → enrich_itemsets → build_entity_web.
- Master audit 18/18; DB 68; query 97; caption 13; access 88; MCP 12/25/8
  (161 calls); taxonomy 16; robustness 26; containment 11; item audit 0
  failures; retrieval eval ranked; docs audit pass; conformance 405 files.
- Consistency: docs-consistency 10/10, doc counts in sync, readme-meta in sync.
- 48 tables, schema 1.13.0, fts 176,794, entity_links 33,578.

## Asset
`grimoire.db` plus `.xz`/`.gz` (SHA256SUMS). Schema 1.13.0.
