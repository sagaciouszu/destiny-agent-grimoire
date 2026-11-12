# v0.42.0 - verify_fts folded into fts.norm (schema 1.12.0)

**2026-11-12**

Schema **1.12.0** data and API release. The corpus is unchanged (9,229
transcripts / 125,324 lines / 63,359 sightings). The verification index
(verify_fts, 176,794 rows, ~56.8 MB) is folded into a normalized `norm`
column on `fts`. `fts` now carries six indexed columns (title, text, speaker,
body, source, norm); `bm25(fts, 3.0, 1.0, 1.0, 1.0, 0.0, 0.0)` keeps ranking
byte-identical.

## What's Changed
- Schema 1.12.0: `fts` gains indexed `norm` column; `verify_fts` dropped.
- `db/migrate.py`: `add_fts` passes normalized text; verify_fts INSERT removed.
- `db/enrich_lore.py`: verify_fts DELETE/INSERT removed; norm in fts INSERT.
- `db/api.py`: `bm25` 6-weight; verify queries `fts.norm`.
- `db/build-slim.py`: verify_fts DELETE/count removed.
- Tests: caption-test, db-source-crosscheck, sync-doc-counts, test-db updated.
- Docs: capabilities, README (Total 712,670), db/README, STANDARDS, SKILL, DISCOVERY, Builds.
- Database is 258 MB (was 271 MB), ~13 MB smaller, identical content.
- Query: `search` returns total from one pass; character-lines block merged.
- MCP: `Returns:` headings normalized; word-budget check (warn <15 or >80).
- docs-consistency: 10 checks (table counts, audit counts, roster, live-build).
- Fixture policy: all six agents' test fixtures replaced with synthetic text.

## Verification

Master audit 18/18; DB 67; query 97; caption 13; access 88; MCP 12/25/8;
six agent audits 20/20 (Drifter 27/27, Eris 22/22); site npm run check.
Rebuild parity: fts 176,794 rows, entity_links 33,578 identical by slug.

## Asset

`grimoire.db` plus `.xz`/`.gz` (SHA256SUMS). Schema 1.12.0.

# v0.41.0 - Smaller database, reproducible speaker split

> **Depends On:** INDEX.md
> **Token Estimate:** ~152 tokens
**2026-11-10**

## What's Changed

- Schema 1.11.0 drops seven unused normalized-text indexes
  (`book_entries`, `grimoire_cards`, `interactions`, `items`, `records`,
  `character_lines`, `lore_entries`). No query reads them; the transcript
  normalized index stays for caption dedupe joins.
- The release database is 271.3 MiB instead of 302.1 MiB, about 30.8 MiB
  smaller with the same content.
- The build chain now runs the owner's speaker split
  (`scripts/apply-queen-fold.py`) after migrate and before the entity web, so a
  fresh rebuild reproduces the shipped speaker assignment instead of drifting.
- The entity-web builder is deterministic; two independent builds produced an
  identical link hash.
- `apply-queen-fold.py` uses a repository-relative default database path rather
  than a machine-specific one.
- Build documentation names the fold and the entity-web step.

## Verification

- `bash grimoire-master-audit.sh`: 18/18.
- `bash tests/test-db.sh`: 67/67.
- `bash tests/query-interface-test.sh`: 97/97.
- `python3 tests/caption-test.py`: pass.
- `python3 tests/agent-access-test.py`: pass.
- MCP: 12/12 contract, 25/25 matrix, 8/8 optimization (161 calls).
- Six agent audits: 20/20 each, Drifter 27/27, Eris 22/22.
- Site `npm run check`: pass.
- Rebuild parity: 56/56 table counts, FTS rows 176,794, entity links identical
  by entity slug.

## Database

Content is unchanged from v0.40.3. The rebuild reproduces every table count,
the FTS row count and the entity-link set; only the index set and the schema
version change.

sha256 `c5001730…1450a3b39`, 284,528,640 bytes (271.3 MiB).

## Asset

`grimoire.db` (271.3 MiB) is attached with `SHA256SUMS`; the release workflow
adds `grimoire.db.xz` and `grimoire.db.gz` and refreshes the manifest.
