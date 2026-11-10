# v0.39.2 - Live-build refresh tooling

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.77K tokens

**2026-11-10**

Tooling release, no schema change (still 1.9.0). The live caption tier can now
be refreshed from a new build without hand-running the pipeline or rewriting an
earlier build's text.

## What's Changed

- **Data-driven build registry.** `archive/data/builds.json` is now the source
  of truth; `db/migrate.py` reads it, so a refreshed build survives a
  from-source rebuild. `builds` still has the two current rows.
- **Per-build live tiers.** New builds write to
  `archive/data/live-builds/<build>.jsonl` with build-scoped slugs; the current
  build stays in `archive/data/captions-live.jsonl`. `db/migrate.py` loads both,
  and a changed line becomes a new `caption_sightings` row, never an inline
  rewrite.
- **`scripts/refresh-live-build.py`** automates source validation, layer
  unpack/merge, locale resolution, extraction, language validation, combine,
  drift report, build registration, rebuild and gates.
- **Safe defaults.** The registered current build is a no-op (exit 0);
  `--dry-run` plans every stage and writes nothing; `--self-test` proves a
  changed line appears in the drift report.
- **Extractor option** `--build-scoped-slug` writes
  `caption-live-<build>-<package>-<entry>-<kind>` slugs for multi-build tiers.
- Docs: `docs/wiki/Builds.md` refresh section and `scripts/README.md` entry.

## Verification

Master audit 14/14; test-db 65/65; caption 12/12; query interface 91/91;
docs-consistency 5/5; MCP 12/12, 8/8, 25/25. Refresh self-test passes; current
build dry-run/no-op passes. From-source rebuild reproduces the same counts:
9,229 transcripts, 125,324 lines, 63,359 sightings.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached. Counts are unchanged; the build
registry text in the artifact is now sourced from `archive/data/builds.json`.

## Known limits

- No real second live build was available in this environment; the synthetic
  drift self-test and current-build no-op are the exercised paths. SteamCMD
  exposes only the public branch, so a private branch cannot be fetched.
- Q2 is closed as non-prose; `0294/5892` remains skipped with evidence.
- `v_speakers` remains a discovery view (423, including caption-only names).

# v0.39.1 - Ecosystem pass: caption-tier surfaces and docs

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.9K tokens

**2026-11-10**

Code + docs patch; database unchanged from v0.39.0. `character(all_lines)`
rows carry `source_tier` and label the caption tier; `0134` closed as a
non-StringBank family; `scripts/export-site-stats.py` is the site's single
stats source; `tests/docs-consistency.py` gates counts, site data, agent
metadata, MCP tools and links. Template, six agents, wiki and site aligned;
persona canon untouched.

## Verification

Master audit 14/14; test-db 65/65; caption 12/12; query 91/91; MCP suites green;
docs-consistency 5/5; six agent audits green; site `npm run check` green.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) byte-identical to v0.39.0.
