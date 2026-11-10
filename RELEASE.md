# v0.35.0 - Beyond Light ingest: Season of Defiance corpus

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.8K tokens

**2026-11-10**

Data-only release. No schema change (still 1.6.0). grimoire.db is the
v0.34.0 database rebuilt from source with three new transcripts and the
speaker aliases that were already in the source (`f68e8a1`) but had not
shipped in a release.

## What's Changed

- **Three Season of Defiance transcripts ingested** (Ishtar Collective,
  verbatim): `awaken-queensguard`, `we-stand-unbroken`, `retribution`
  (Arc: Season of Defiance / quest names). 188 new canon lines;
  transcripts 2,422 -> 2,424, lines 78,740 -> 78,928, FTS entries
  130,210 -> 130,398.
- **STANDARDS.md scope policy (owner decision, 2026-11-11):** corpus
  expands from Shadowkeep/SoA to Destiny 2 launch through the current
  live build, with the per-content pre-vault sourcing rule and
  build-labeled provenance (see commit `1bb4a2d`). This release is a
  docs-only policy change; the BL data remains Vision of Vision
  unchanged in this tag (BL/WQ/Lightfall/TFS/RoElines already shipped).
- **Speaker aliases 23 -> 57** ship in this release: 34 folds added in
  `f68e8a1` (e.g. `? Exo Stranger` -> `Elsie Bray`, `Five` ->
  `The Nine`, `Devrim` -> `Devrim Kay`, `Reflection of Osiris` ->
  `Osiris`) now apply to every new rebuild.
- **The Queen split re-applied** (owner ruling 2026-11-09): the rebuild
  loses the in-place fold (DB-only by design); it was re-applied on the
  same row assignments: 22 lines -> Riven, 15 lines -> Mara Sov.
- **Entity web rebuilt**: entities 89, aliases 136, links 24,622
  (+27 from the new lines), relations 4. Document links re-derived
  against the same indexed corpus.

## Verification

Gates: test-db 61/61; lore-integrity 17/17; query-interface 89/89;
mcp-test 12/12; mcp-matrix 8/8; mcp-agent-optimization 25/25;
doc-counts in sync; readme-meta in sync.

## Notes

From-source rebuild re-derives all enrichment (lore, manifest, seals,
itemsets) and the entity web; `backups/grimoire-pre-entityswap-2026-11-11.db`
holds the pre-rebuild state for rollback. v0.33.1's DB-only The Queen
fold is documented in-place in the v0.33.1 release entry and re-applied
here. The captions (sunrise-pre-bl build) pipeline is unchanged.
build-25932352 (live-build) extraction is the next phase, tracked in
the STANDARDS.md scope entry.

# v0.34.0 - Entity web round 2: SIVA, Five alias

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.6K tokens

**2026-11-09**

Data-only release. No schema change (still 1.6.0). grimoire.db is the v0.33.2
database with the SIVA entity and Nine-facet alias folded in one rebuild.

## What's Changed

- **`SIVA` added as a `power` entity** (Rasputin's warmind-born nanomachine
  weapon, owner ruling). SIVA carries `related_to Rasputin` plus 177 links
  (177 documents: 45 item matches by title, 166 transcript lines with SIVA
  in text, etc., all re-derived). Owner-commissioned, reviewed=1.
- **`Five` alias added to `The Nine`** (owner ruling 2026-11-09: the
  Monument of Triumph "chapter Five" speaker label is a Nine-facet;
  see v0.33.2 for the speaker-side fold).
- **`entity_aliases` 134 -> 136, `entities` 88 -> 89, `entity_links`
  24,196 -> 24,595, `entity_relations` 3 -> 4.**
- Lexicon: `db/entity-lexicon-proposal.tsv` (owner-reviewed
  high-confidence pinned per owner manifesto for v0.34.0; SIVA from
  owner-ruling evidence). Gates: test-db 61/61; lore-integrity 17/17;
  query-interface 89/89; sync-doc-counts in sync.

## Notes

Build-by-temp-copy + atomic swap method used; books/lore byte-identical reads;
release hash in release notes; rollback via backups/grimoire-pre-swap-v0.34.0.db.
