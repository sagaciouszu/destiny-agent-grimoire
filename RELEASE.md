# v0.42.2 - Corpus rebuilt from the private vault (schema 1.13.0)

**2026-11-17**

Rebuild release. The database was regenerated end-to-end from the operator vault
using the documented runbook, then compared against v0.42.1. Schema, queries,
MCP surface and corpus counts are unchanged; this artifact is republished to
record rebuild provenance and the gates it passed.

## What's Changed
- `scripts/rebuild-from-vault.sh` rebuilt the database from the private vault;
  every manifest input was hash-verified and the run closed with
  `vault untouched: OK`.
- The gitignored Bungie manifest cache was staged locally for `enrich_lore`;
  no raw archive or manifest dump was added to Git.
- Captions were staged from the vault: 7,911 transcripts, 55,678 lines, 56,119
  provenance rows, 63,359 sightings, 64 activity facets, 0 unresolved.
- The isolated rebuild root recreated the live workspace shape (per-agent
  `lore` links, personal `core/` files, template checkout) so conformance ran
  against the real layout instead of a bare checkout.
- Counts unchanged from v0.42.1: 9,229 transcripts / 125,324 lines / 2,889
  cards / 2,699 interactions / 58,764 items / 20 characters / 176,794 FTS rows
  across 48 tables at schema 1.13.0.
- Profile README metadata refreshed for the new tag and HEAD date.
- No schema, query, MCP-tool or documentation-claim changes.

## Verification
- Full chain: migrate → queen-fold → enrich_lore → enrich_seals →
  enrich_itemsets → build_entity_web.
- Master audit 18/18 suites, 0 failed, 0 skipped; DB tests 68; caption tests 13;
  MCP contract 12; MCP agent optimization 25; permission audit 1,584 checks.
- Conformance: all files conform in the rebuilt workspace layout.
- Release parity against v0.42.1: 15/15 (table-name set, 13 table counts, and
  the game-caption transcript count). The check compares counts, not row
  contents.
- Candidate and current database `stats` identical on every table; live
  post-promotion `PRAGMA integrity_check` returned `ok`.
- Site check: 71 pages (links, metadata, sitemap, robots), 39 axe renders,
  162 transcripts, 24 demo lines, 30/30 samples across 12 agents, roster
  current.
- Vault dry-run verified every manifest file (`OK`) before the build.

## Asset
- `grimoire.db` — 269,242,368 bytes (~269 MB), schema 1.13.0, 48 tables.
- `SHA256SUMS` carries the artifact hash.
