# v1.7.0 - Retrieval quality and deeper MCP

**2026-11-03**

## What's Changed

- **Retrieval evaluation:** 15-query harness; relevance ordering is now the default (MRR 0.90 to 0.93, P@5 0.83 to 0.89)
- **Item lookup:** `item_title_fts` makes `find_item` an indexed title search across 58,764 items
- **Paging:** `total` and `next_offset` on search; every list command still accepts `offset`
- **Batch checks:** `verify_many` checks up to 20 quotes per call
- **Character metadata:** `character_info` reports aliases, quote totals and spoken lines
- **MCP resources and prompts:** per-book, per-transcript, per-character and per-record templates, plus `quote_safe_lookup` and `character_brief`
- **Caching:** repeated verification calls are cached (512 entries)

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 38/38 database, 29/29 interface, 6/6 MCP, 141-call matrix, extended 5/5, conformance PASS.

## Asset

`grimoire.db` (170 MB) with `verify_fts` and `item_title_fts`. sha256 `c7fa3acc80f63ed43f0b90acb1e9f09ddb5dbaffdd161d4100a7285c3354072b`. `SHA256SUMS` is attached.
