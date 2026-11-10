# v0.37.1 - Mounted package layers for the live tier

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.93K tokens

**2026-11-10**

Corrective release. v0.37.0 ingested the base layer (`_0`) of package
`w64_sr_globals_0294` only. A package family mounts a base plus patch layers,
and the patch carries current-build text; base-only was stale.

## What's Changed

- **Layer merging.** `scripts/merge-pkg-layers.py` builds the mounted view:
  same-class entries overlay, class-replaced entries drop the stale base.
  Package `0294` mounts 8,179 overlaid entries and 13 class replacements.
- **Current text.** The mounted extraction replaces `Gambit` with
  `Gambit Ops`, `Stakes` with `Buildcraft/Gameplay Stakes`, and adds 37 lines
  while dropping 29 stale ones. Final tier: 3,492 emitted lines -> 3,335
  provenance rows (517 headers; 3,329 caption lines, 6 on pre-existing
  non-caption lines).
- **One honest gap.** Entry `5892` is replaced by a patch class (`0x808099ef`)
  this parser does not understand. It is skipped and logged in the stats
  sidecar, never back-filled from the stale base.
- **Extractor hardening.** Unparseable entries are skipped with a recorded
  reason instead of aborting the run; item-fragment exclusion is on by default.
- Counts after rebuild: transcripts 2,935, lines 82,257, FTS 133,727,
  `caption_provenance` 12,942 (live 3,335).

## Verification

Full from-source rebuild (migrate -> enrich -> Queen fold -> entity web).
Gates: test-db 61/61, lore-integrity 17/17, query-interface 89/89, caption
10/10, containment 11/11, mcp-test 12/12, mcp-matrix 8/8,
mcp-agent-optimization 25/25, doc-counts and readme-meta in sync.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release; rebuild with
`python3 db/migrate.py` and the enrich chain in `README.md`.

## Known limits

- One of 16 globals packages is ingested; the rest need extraction, layer
  merging and locale resolution before they can be added.
- 258 of 633 parsed entries yield no kept line (labels, noise, duplicates,
  item fragments); logged, not loosened.
- 157 emitted live lines repeat 2020 canon text and merged into the existing
  row; `caption_provenance` is one row per line.
- `tests/count-consistency.py` reports pre-existing persona-count drift
  (zavala, ghost, mara-sov); persona counts are canon and are not changed.

# v0.37.0 - Live-build caption tier: schema 1.8.0

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~1.4K tokens

**2026-11-10**

First live-build caption tier (`build-25932352`, package
`w64_sr_globals_0294`). The text is cleartext UTF-8 in class `0x808099f1`;
the earlier "rotated keys" verdict covered encrypted block classes.

## What's Changed

- 634 English entries, 17,990 base-layer strings, 3,327 provenance rows
  (this release used the base layer; v0.37.1 mounts the patch).
- 736 `dialogue`, 1,823 `narration`, 768 `objective`; 38 named speakers, all
  from `"..." —Name`. No season or act inferred.
- Extractor excludes labels (13,614), mechanical copy (91), item-text
  fragments (911) and duplicates; `scripts/containment.py` enforces dedupe.
- Schema 1.8.0: `caption_provenance.record_index` + `record_part` join
  `source_build`/`source_pkg`/`bank_entry`.
- `scripts/resolve-locales.py` reproduces the verified EN list for `0294`
  exactly (634/634, zero false positives).
- Docs: `docs/wiki/Builds.md`, `docs/wiki/Captions.md` and `STANDARDS.md`
  define the two-build tier, its heuristics and its limits.

## Verification

Gates: test-db 61/61, lore-integrity 17/17, query-interface 89/89, caption
10/10, containment 11/11, mcp-test 12/12, mcp-matrix 8/8,
mcp-agent-optimization 25/25.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release.
