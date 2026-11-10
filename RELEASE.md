# v0.38.0 - Corpus widening: all live string-bank packages

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~1.2K tokens

**2026-11-10**

Data-only release (schema stays 1.8.0). The live-build caption tier grows from
one package to fifteen, and the speaker rule is tightened to the evidence the
standard actually names: a quoted attribution.

## What's Changed

- **15 of 16 `w64_sr_globals_*` packages ingested** (8,597 English entries).
  `0134` has no English string-bank entries and is skipped with a logged
  reason. 153,558 strings -> 51,737 package-local lines -> 48,163 after
  cross-package dedupe -> **46,512 live provenance rows** and 46,396 caption
  lines.
- **Package layers are mounted.** `scripts/merge-pkg-layers.py` overlays patch
  layers and drops stale class-replaced entries. Across the 15 families:
  6,665 added, 146,986 overlaid, 636 class replacements. Base-only text is
  stale and is not shipped.
- **Speaker rule tightened.** A speaker now requires the quoted evidence
  pattern `"..." —Name`; unquoted bylines (`Chapter 6 — Beguiled`, section
  headings, pipe artifacts) are no longer speakers. 257 named speakers remain,
  all queryable by `speaker_source='build-25932352'`.
- **Language gate.** `scripts/validate-live-language.py` rejects whole tables
  whose aggregate text is another language. Six German tables in `029e` are
  excluded; the tier has 0 Cyrillic, 0 CJK and 0 Polish-diacritic lines.
- **Zero item-text fragments.** `scripts/combine-live-captions.py` applies
  cross-package dedupe (3,572 lines) and a final containment pass against
  `items.jsonl`; the shipped tier has 0 fragments.
- Counts after rebuild: transcripts 9,229, lines 125,324, FTS 176,794,
  caption tier 7,911 headers / 55,678 lines, entities 89, entity links 33,578.

## Verification

Full from-source rebuild (migrate -> enrich -> Queen fold -> entity web).
Gates: test-db 61/61, lore-integrity 17/17, query-interface 89/89, caption
10/10, containment 11/11, mcp-test 12/12, mcp-matrix 8/8,
mcp-agent-optimization 25/25, file conformance, source overlap, cutscene
verification, speaker audit, master audit 13/14 (only the pre-existing
persona-count drift remains).

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release; rebuild with
`python3 db/migrate.py` and the enrich chain in `README.md`.

## Known limits

- 4,442 of 8,597 English entries (52%) contribute a kept line; 3,588 yield
  nothing after label/duplicate/fragment filtering. This is logged, not
  loosened.
- `caption_provenance` is one row per line: 1,651 emitted live lines merged
  into existing canon (116 onto non-caption web/cutscene lines).
- The resolver emits only anchored tables; 13 of 15 packages are
  `medium` confidence with unanchored blocks skipped. The language gate covers
  whole-table misassignment, not missing tables.
- `tests/count-consistency.py` still reports the pre-existing persona-count
  drift (zavala, ghost, mara-sov); persona canon is unchanged by this release.

# v0.37.1 - Mounted package layers for the live tier

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.9K tokens

**2026-11-10**

Corrective release. v0.37.0 ingested the base layer (`_0`) of package
`w64_sr_globals_0294` only; the patch layer carries current-build text.

## What's Changed

- `scripts/merge-pkg-layers.py` mounts base + patches (0294: 8,179 overlaid,
  13 class replacements) and the extractor skips an unsupported patch class
  instead of aborting.
- Current text replaces stale base text (`Gambit Ops`, `Buildcraft Stakes`);
  the tier becomes 3,492 lines -> 3,335 provenance rows.
- Extractor hardening: unparseable entries are logged and skipped; item
  fragment exclusion is on by default.

## Verification

Full rebuild. Gates: test-db 61/61, lore-integrity 17/17, query-interface
89/89, caption 10/10, containment 11/11, mcp 12/12 + 8/8 + 25/25.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release.
