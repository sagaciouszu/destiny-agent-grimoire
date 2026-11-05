# v0.27.3 - Database self-audit and MCP CLI parity

**2026-11-05**

## What's Changed

Everything since v0.27.2:

- **Database self-audit found three migration bugs, all fixed:**
  - the `meta` stamp reported `transcripts` as 58764 (the item-title counter
    was reused at write time); it now equals the live count, the build date is
    dynamic, and classification/coverage/alias keys were added,
  - the build date was hard-coded to 2026-11-04,
  - a leftover DEBUG print ran on every weblore ingest.
- **Normal forms are total.** The 14 punctuation-only canon lines keep their
  punctuation instead of normalizing to the empty string, so `verify` matches
  them; the query-side normalizer in `db/api.py` mirrors the same fallback.
- **Attribution purge, verified.** The empty normal form let one Destinypedia
  punctuation line's speaker (Failsafe) bleed onto 13 cutscene caption lines;
  those stay `Cutscene` now. Every other line is byte-identical to the previous
  build, and GAPS game dialogue counts corrected (D2 14,282 / D1 1,411).
- **`class_tag` normalized:** NULL or hunter/titan/warlock on every line
  (5,750 empty strings cleared).
- **MCP reaches full CLI parity: 21 tools** - new `seals`, `seal`, `lore` -
  plus corrected README argument lists, `search type=lore`, and complete tool
  and resource lists in the skill and wiki.
- **`db/capabilities.json` is schema-complete:** it documents `item_title_fts`
  and `meta`, and a new gate fails when it drifts from the live schema.
- **STANDARDS** source hierarchy now documents the accepted `ishtar_web` tier
  (the test always allowed it; the contract did not list it).
- **Gates grew:** test-db 51 -> 55, mcp-test 10 -> 12, matrix 21 tools /
  154 calls - every count citation in README, tests/README, the wiki and
  STANDARDS updated to match.

## Verification

11/11 archive suites, 55/55 database, 89/89 query interface, 17/17 taxonomy, 11/11 source crosscheck, MCP contract 12/12 and matrix 8/8 (154 calls), agent connections 36/36, parity 60/60, onboarding 60/60, 361 documented commands, link check 18/18, conformance PASS. Pre/post rebuild diff: every content table byte-identical, persona counts unchanged.

## Asset

`grimoire.db` with 1,314 transcripts, 69,217 canon lines and 20 speaker
aliases. SHA256 in `SHA256SUMS`.
