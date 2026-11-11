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
