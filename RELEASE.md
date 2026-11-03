# v1.8.0 - Leaner index and operations tooling

**2026-11-03**

## What's Changed

- **Search index:** stat-only items are no longer indexed; FTS drops from 136,802 to 120,731 rows with no loss of searchable lore
- **Schema version:** `db/SCHEMA_VERSION` plus a database gate; migration writes 1.0.1
- **Quality:** item provenance audit, retrieval evaluation, and DB/source cross-check
- **Slim profile:** `db/build-slim.py` produces a 95 MB core database without items or cards
- **Ops scripts:** release staging, rolling backup, and live-agent sync
- **CI:** workflow builds the database and runs conformance, database, interface, retrieval and MCP checks

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 38/38 database, 29/29 interface, 6/6 MCP, 141-call matrix, extended 5/5, conformance PASS.

## Asset

`grimoire.db` (169 MB) with `verify_fts` and `item_title_fts`. sha256 `a3957e1e5f82c38be40baa54038e35734c492d442a8621f727dee55bb89cc226`. `SHA256SUMS` is attached.
