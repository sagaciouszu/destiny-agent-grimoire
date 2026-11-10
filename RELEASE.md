# v0.37.0 - Live-build caption tier: schema 1.8.0

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~1.4K tokens

**2026-11-10**

Data + schema release. The caption tier now spans two game builds, and every
live line traces to the build, package, bank entry and record slot that
shipped it.

## What's Changed

- **Live-build caption tier (`build-25932352`).** `w64_sr_globals_0294`, one
  of 16 v53 StringBank packages, contributes 634 English entries: 17,990
  strings -> 3,484 emitted lines -> 3,327 provenance rows (512 headers). The
  text is cleartext UTF-8 in class `0x808099f1`; the earlier "rotated keys"
  verdict covered encrypted block classes, not these banks.
- **Kinds and speakers.** 736 `dialogue`, 1,823 `narration`, 768 `objective`
  (heuristic from punctuation and in-string attribution). 38 named speakers,
  every one from a `"..." —Name` attribution; no season or act is inferred.
- **Extractor** (`scripts/extract-live-captions.py`): an attributed string is
  always dialogue; mechanical perk/modifier copy is excluded (91); lines that
  are fragments of an existing item entry are dropped by normalised
  containment (`scripts/containment.py`, 911); short labels and UI headings
  stay out (13,614). Each package's drop/keep counts ship as a stats sidecar.
- **Schema 1.8.0**: `caption_provenance.record_index` + `record_part`, joining
  `source_build`/`source_pkg`/`bank_entry`. The live build exposes no per-line
  StringReference hash, so identity is the slot, not a hash.
- **Locale resolver** (`scripts/resolve-locales.py`): script-anchored dynamic
  program; reproduces the verified EN entry list for package `0294` exactly
  (634/634, zero false positives). Packages it cannot pin are skipped, not
  guessed.
- **Docs**: `docs/wiki/Builds.md` registers the live tier and its limits;
  `docs/wiki/Captions.md` and `STANDARDS.md` define string-bank text vs
  subtitle captions.

## Verification

From-source rebuild: migrate -> enrich (lore, manifest, seals, itemsets) ->
Queen fold -> entity web. Gates: test-db 61/61, lore-integrity 17/17,
query-interface 89/89, caption 10/10, containment 11/11, mcp-test 12/12,
mcp-matrix 8/8, mcp-agent-optimization 25/25, doc-counts and readme-meta in
sync.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release; rebuild with
`python3 db/migrate.py` and the enrich chain in `README.md`.

## Known limits

- One of 16 globals packages is ingested; the rest need extraction and locale
  resolution before they can be added.
- 259 of 634 entries yield no kept line (labels, noise, duplicates, item
  fragments); this is logged, not loosened.
- 157 emitted live lines repeat 2020 canon text and merged into the existing
  row; `caption_provenance` is one row per line, so the live sighting is in
  the audit report, not the table.
- `tests/count-consistency.py` reports pre-existing persona-count drift
  (zavala, ghost, mara-sov); persona counts are canon and are not changed.

# v0.36.0 - Build registry: schema 1.7.0

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.9K tokens

**2026-11-10**

- **New `builds` table** (registry): `sunrise-pre-bl` (2020 client, package
  format v38) and `build-25932352` (live Update 9.7.0.6, package format v53).
- **`caption_provenance.source_build`** (NOT NULL): every caption row names
  its build; 9,607 provenance rows tagged.
- **Build registry chain**: `docs/wiki/Builds.md` is the single map of builds
  and extraction tiers; STANDARDS and Captions point to it.
- **Fresh rebuild**: enrich chain re-run; `scripts/apply-queen-fold.py`
  replaces the inline fold; entity web rebuilt (24,622 links).

## Verification

Gates: test-db 61/61, lore-integrity 17/17, query-interface 89/89,
mcp-test 12/12, mcp-matrix 8/8, mcp-agent-optimization 25/25, doc-sync clean.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release.

## Notes

Schema 1.6.0 -> 1.7.0 is additive; fresh builds derive it from `db/schema.sql`.
