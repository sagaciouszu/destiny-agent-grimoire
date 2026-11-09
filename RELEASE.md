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
- Lexicon: `/home/sredshaw/Work/entity-lexicon-proposal.tsv` (owner-reviewed
  high-confidence pinned per owner manifesto for v0.34.0; SIVA from
  owner-ruling evidence). Gates: test-db 61/61; lore-integrity 17/17;
  query-interface 89/89; sync-doc-counts in sync.

## Notes

Build-by-temp-copy + atomic swap method used; books/lore byte-identical reads;
release hash in release notes; rollback via backups/grimoire-pre-swap-v0.34.0.db.
