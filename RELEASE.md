# Release v1.3.0 - Standards + Agent Interface v2

**Date:** 2026-11-02

## Highlights

- **STANDARDS.md** - the contract: schema rules, canonical speaker names, provenance, quote policy, verification gates, connection matrix
- **Agent interface v2** - snippet-first search with `--full` escape, `--json` on every command, `verify` quote-safety primitive, `list` discovery, `character --about/--all`
- **Fixed:** `search --type` compared FTS rowids against table rowids; FTS now carries a source column so filters are exact
- **Database to standards** - speaker aliases canonicalized at migration (0 variants), `speaker_aliases` table, `v_speakers` view, `db/capabilities.json` manifest, every card has a source URL
- **Data integrity** - HTML entity leakage eliminated, compendium multi-quote parser fixed (+135 recovered quotes, 0 broken provenance), 108 dead book links gone, one mislabeled transcript rebuilt from live
- **Verification** - conformance sweep across all three repos, source-overlap and speaker audits gated into the master audit, 35 database checks, 23 interface checks
- **Cutscene corpus** - 31 compilations, auto-generated captions (disclosed), corroboration-verified

## Verification

| Suite | Result |
|-------|--------|
| drifter-master-audit | 17/17 |
| grimoire master-audit | 11/11 |
| eris-morn master-audit | 8/8 |
| test-db / query-interface | 35/35, 23/23 |
| cutscene-verify | 6/6 |

## Asset

`grimoire.db` - 1229 transcripts, 71,221 lines, 136,802 FTS rows, 1,189 character quotes.
Digest is published with the asset; rebuild with `python3 db/migrate.py`.

Fan-made. Not affiliated with or endorsed by Bungie. Content sourced from Ishtar
Collective and YouTube captions.
