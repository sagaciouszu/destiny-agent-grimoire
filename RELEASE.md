# v0.22.0 - Manifest lore, Commons transcripts and source tiers

**2026-11-04**

## What's Changed

- **Manifest lore:** 2,962 `DestinyLoreDefinition` entries ingested; 1,962 are
  new after dedupe against books, items and cards. Item links included.
- **Manifest catalogue:** 3,744 activities and seasons 27-28 added to the
  reconciliation layer, with 314 curated-to-manifest links.
- **Ishtar Commons:** 862 topics crawled; 37 net-new transcripts after
  line-level dedupe, including strikes and patrol dialogue.
- **Source precedence:** `source_tier` records Ishtar > Destinypedia > captions.
- **Variants:** `section` and `is_optional` preserve locations, optional blocks
  and class callouts; `--canon-only` and `--section` expose them.
- **Seals:** 70 seals and 1,004 triumph records, exposed as `seal`/`seals`.
- **Discovery:** `list lore`, `lore <hash|title>`, `seal`, `seals` and `--type lore`.

## Verification

9/9 archive, 82/82 interface, 14/14 layout, 8/8 MCP, 141-call matrix, 8/8 extended, conformance PASS. Drifter 20/20 and Eris 15/15 in their repos.

## Asset

`grimoire.db` with lore, taxonomy and verification indexes. `SHA256SUMS` is attached.
