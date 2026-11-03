# v1.3.0 - Standards and agent interface v2

**2026-11-02**

## What's Changed

- **Agent interface v2:** snippet-first search with `--full`, `--json` on every command, `verify` quote safety, `list` discovery, `character --about/--all`
- **Fixed:** `search --type` compared mismatched rowids; FTS now carries a `source` column so filters are exact
- **Standards:** `STANDARDS.md` defines schema, canonical speakers, provenance, quote policy and verification gates
- **Data integrity:** entity leakage eliminated, 135 quotes recovered, 108 dead book links fixed, one mislabeled transcript rebuilt
- **New:** `speaker_aliases` table, `v_speakers` view, `db/capabilities.json`, MIT license
- **Cutscene corpus:** 31 compilations from captions (auto-generated, corroboration verified)

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 35/35 database, 23/23 interface, conformance PASS.

## Asset

`grimoire.db` (128 MB, sha256 published with the asset). Rebuild with `python3 db/migrate.py`.
