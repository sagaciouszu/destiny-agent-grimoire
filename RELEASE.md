# Release v1.3.0 - Standards + Agent Interface v2

**Date:** 2026-11-02

## What this is

SQLite-backed Destiny lore archive for agent consumption. Single file
(`db/grimoire.db`), built from the committed sources (`python3 db/migrate.py`)
and attached to this release as an asset.

## Data totals

| Table | Rows |
|-------|------|
| books | 110 |
| book_entries | 1158 |
| transcripts | 1229 |
| transcript_lines | 71221 |
| grimoire_cards | 2889 |
| interactions | 2699 |
| items | 58764 |
| records | 71 |
| characters | 18 |
| character_lines | 1189 |
| fts | 136802 |

## What changed since v1.2.0

### Standards
- STANDARDS.md defines the schema contract, canonical speaker names, provenance,
  quote policy, verification gates and the connection matrix
- speaker_aliases table + v_speakers view; alias variants canonicalized at migration
- Every grimoire card carries source_url; HTML entity leakage eliminated

### Agent interface v2
- `search` returns snippets by default (`--full` for text); `--json` on every command
- fixed: `search --type` was comparing FTS rowids against table rowids; FTS now
  carries a source column, filters are exact
- `verify "<quote>"` - quote-safety primitive (exit 1 when absent)
- `list books|characters|speakers|records` - cheap discovery
- `character --about <term>` / `--all`
- `db/capabilities.json` - machine-readable interface manifest

### Data integrity
- compendium multi-quote parser: 15 broken provenance rows -> 0, 135 quotes recovered
- book slugs/source_urls aligned with the live site (108 dead links fixed)
- one mislabeled transcript rebuilt from live (visit-8 held visit-9 content)
- 31 cutscene compilations (auto-generated captions; corroboration verified)

## Test results

- drifter-master-audit.sh: 17/17
- eris-master-audit.sh (this repo): 11/11 (incl. conformance, overlap, speaker gate)
- eris-morn master-audit: 8/8
- test-db.sh: 35/35
- query-interface-test.sh: 23/23
- cutscene-verify.sh: 6/6

## Attribution

All content sourced from https://www.ishtar-collective.net (Ishtar Collective) and
YouTube cutscene captions. Fan-made. Not affiliated with or endorsed by Bungie.
