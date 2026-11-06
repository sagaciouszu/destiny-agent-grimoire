# v0.27.5 - Immolant transcript ingestion and standards reconciliation

**2026-11-05**

## What's Changed

Everything since v0.27.4:

- **Immolant Pt. 1-2 ingested as transcripts.** Dialogue scenes that had been
  filed under the lore corpus (`source/records/`) now live in the transcript
  corpus (`source/transcripts/`) with Ishtar transcript provenance; the
  database was rebuilt through the full pipeline (migrate plus lore, manifest,
  seals and item-set enrichment). Immolant dialogue is now queryable (241
  lines; story chapter `the_rise_of_stasis`).

- **Standards reconciliation.** `STANDARDS.md` refreshed and ratified with
  every rule tied to a verification gate; Eris canon-count query corrected to
  an exact speaker match; database and doc counts re-synced after the rebuild;
  source and capability cross-checks updated.

## Verification

Conformance 163/163 clean; test-db 61/61; query interface 89/89; lore
integrity 17/17; lore format 155/155; db-source-crosscheck 11/11; sync
doc-counts and README metadata in sync; suite manifests 5/5 pass; MCP
contract green; Immolant transcripts present with timeline set.

## Asset

`grimoire.db` rebuilt from tracked sources plus local enrichment dumps;
companions `grimoire.db.xz` / `grimoire.db.gz` and refreshed `SHA256SUMS` are
attached by the release-assets workflow on publish.
