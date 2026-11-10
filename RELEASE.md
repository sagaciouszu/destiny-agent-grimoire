# v0.39.1 - Ecosystem pass: caption-tier surfaces and docs

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~1.2K tokens

**2026-11-10**

Code + docs patch. The database is unchanged from v0.39.0 (same schema 1.9.0,
same 9,229 transcripts / 125,324 lines / 63,359 sightings); this release aligns
every consumer and adds the missing caption-tier surfaces.

## What's Changed

- **`character` names the tier.** `character(all_lines=True)` and the speaker
  fallback now return `source_tier` per row and label the page `caption lines`
  or `transcript + caption lines` when the returned rows include captions.
  `--canon-only` still means "exclude optional/variant lines", not "exclude
  captions"; agent docs now say so explicitly.
- **`0134` closed.** Its entries use non-StringBank classes (`0x80809a81`,
  `0x80809b23`); the `0x808099f1` resolver correctly finds 0 tables, so the
  package is skipped with a reason rather than treated as missing English.
- **One site stats source.** `scripts/export-site-stats.py` writes the counts,
  schema, release and sizes the public site consumes as the site stats JSON;
  the site's stat grid, install sizes and MCP tool list render from it.
- **Cross-repo docs gate.** `tests/docs-consistency.py` checks stale counts and
  sizes, the site snapshot, agent README metadata, MCP tool names and relative
  links; it is wired into CI and skips absent siblings.
- **Generators corrected.** `coverage-report.py` and `speaker-audit.py` now use
  the persona predicate (`is_stage_dir=0`, `is_optional=0`,
  `source_tier != 'game_caption'`); `v_speakers` is described everywhere as a
  discovery view, not a curated list.
- **Template + agents + wiki.** `source-persona.py` resolves names and lines
  through one caption-excluded predicate and rejects caption-only names with a
  clear error; a regression test covers it. Six agent repos and the wiki had
  their rosters, suite counts, tool lists, `speaker_source` counts and database
  sizes synced. Persona canon was not changed.

## Verification

Master audit 14/14; test-db 65/65; caption 12/12; query interface 91/91;
docs-consistency 5/5; MCP 12/12, matrix 8/8, optimization 25/25. Six agent
audits pass (25/25, 20/20 ×5), persona freshness green. Template tests and the
new caption-only resolver test pass. Site `npm run check` passes (stats, links,
accessibility, axe, tapes, roster).

## Asset

`grimoire.db` (plus `.xz`/`.gz`) is byte-identical to v0.39.0; it is attached
again so `releases/latest/download/grimoire.db` keeps working. Rebuild with
`python3 db/migrate.py` and the enrich chain in `README.md`.

## Known limits

- Q2 (`0x808099ef` parser) and Q3 (live-build refresh automation) remain queued;
  both change the DB and need a count re-sync afterwards.
- `v_speakers` intentionally includes 191 caption-only speakers. A separate
  canon-speaker view would be a schema change.
- `--canon-only` does not exclude caption rows; filter `source_tier` explicitly
  when you need persona-canon text.

# v0.39.0 - Caption sighting log: schema 1.9.0

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.9K tokens

**2026-11-10**

Schema release. `caption_provenance` remains one row per line; the new
`caption_sightings` table retains every observation, keyed by
`(line_id, source_build, source_slug, line_ord)`. 63,359 rows: 51,735 live +
11,624 sunrise, including 7,681 merged lines. Counts: 9,229 transcripts,
125,324 lines, 176,794 FTS entries.

## Verification

Full from-source rebuild; master audit 14/14; test-db 65/65; caption 11/11;
query 89/89; MCP suites green.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release.
