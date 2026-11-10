# v0.39.0 - Caption sighting log: schema 1.9.0

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~1.2K tokens

**2026-11-10**

Data + schema release. `caption_provenance` still holds one row per line; the
new `caption_sightings` table keeps every observation, including the builds and
packages whose provenance lost that race.

## What's Changed

- **Schema 1.9.0**: `caption_sightings` logs one row per processed caption
  record line, keyed by `(line_id, source_build, source_slug, line_ord)`.
  `source_slug` + ordinal is the identity because sunrise lines carry no record
  index; a physical-slot key collapsed 1,070 genuinely distinct lines.
- **Every sighting retained.** 63,359 rows: 51,735 live + 11,624 sunrise;
  7,681 merged lines, including 1,651 live lines that repeat 2020 canon and
  3,572 cross-package repeats. `caption_provenance` is unchanged at 56,119.
- **Cross-package repeats kept.** `scripts/combine-live-captions.py` no longer
  dedupes repeated text across packages by default (the loader still collapses
  it to one canon line). `--dedupe-cross-package` is available for a slim file.
- **Build registration moved before caption load**, so every sighting carries
  `captured_at` from `builds`; the column is NOT NULL and `source_build` is a
  foreign key. `INSERT OR REPLACE` on `builds` was left unchanged because the
  registry is written before any sighting exists.
- **Gate derives expectations from the source.** `tests/caption-test.py`
  compares per-record and per-build totals to the JSONL, not constants, and
  checks the dual-build line count against the JSONL text intersection (1,651),
  referential integrity, `PRAGMA foreign_key_check`, and timestamp truth.
- Counts after rebuild: transcripts 9,229, lines 125,324, FTS 176,794; caption
  tier 7,911 headers / 55,678 lines.

## Verification

Full from-source rebuild (migrate -> enrich -> Queen fold -> entity web).
Gates: test-db 65/65, lore-integrity 17/17, query-interface 89/89, caption
11/11, containment 11/11, mcp 12/12 + 8/8 + 25/25, conformance, source overlap,
cutscene verification, speaker audit, master audit 14/14.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release; rebuild with
`python3 db/migrate.py` and the enrich chain in `README.md`.

## Known limits

- The sighting log is per processed record line, not per physical slot. If two
  live records ever overlap the same bank slot, both are stored; today the
  overlap is zero.
- `caption_provenance.kind` remains first-writer-wins. 1,696 lines carry more
  than one `kind` across sightings; the per-package value lives in
  `caption_sightings`.
- 4,442 of 8,597 English entries contribute a line; 3,588 remain empty after
  filtering.

# v0.38.0 - Corpus widening: all live string-bank packages

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.9K tokens

**2026-11-10**

Data-only release (schema 1.8.0). The live caption tier grows from one package
to fifteen, and a speaker now requires the quoted `"..." —Name` evidence.

## What's Changed

- 15 of 16 `w64_sr_globals_*` packages (8,597 English entries); `0134` has no
  English entries and is skipped. 153,558 strings -> 51,737 package-local lines
  -> 48,163 after cross-package dedupe -> 46,512 provenance rows.
- Package patch layers are mounted before extraction; base-only text is stale.
- Language gate excludes six German tables in `029e`; independent lexicon check
  passes 40 tables per package across all 15 packages with 0 flags.
- Zero item-text fragments; speakers come only from quoted attributions.
- Counts: transcripts 9,229, lines 125,324, FTS 176,794.

## Verification

Full rebuild; master audit 14/14 (persona counts synced post-release).

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release.
