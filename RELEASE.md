# v0.40.1 - Honesty and provenance pass

**2026-11-10**

Documentation and site patch. The database is byte-identical to v0.40.0.

## What's Changed

- The site publishes a **Limits and provenance** page and a plain-text facts
  file: scope, caption tier, timeline and source gaps, speaker rules and AI caveats.
- Site samples are gated by the site's sample check: 18 samples across 6 agents
  pass `verify --exact`.
- README claims are precise: "verified" means present in this library, not
  officially published; the corpus is not described as complete.
- `scripts/export-site-stats.py` exports caption, speaker, timeline, source-URL
  and coverage counts so the honesty page cannot drift.

## Verification

Master audit 18/18; six agent audits 20/20 (Drifter 25/25); site `npm run check`
(42 pages, 18 samples, 83 tapes); docs-consistency 5/5; conformance pass.

## Asset
`grimoire.db` plus `.xz`/`.gz` is byte-identical to v0.40.0.

# v0.40.0 - Tier filters and canon speakers

**2026-11-10**

Schema **1.10.0** data and API release. The corpus is unchanged at 9,229
transcripts / 125,324 lines / 63,359 caption sightings.

## What's Changed

- **`v_canon_speakers` view.** 230 speakers with at least one persona-canon
  line (non-stage, non-optional, non-caption). `v_speakers` remains the 423-row
  discovery view. New `list canon-speakers` / MCP `list_records("canon_speakers")`.
- **Explicit tier filters.** `character` and `transcript` accept `--tier` and
  `--exclude-tier` (repeatable or comma-separated), in the CLI and MCP.
  `--canon-only` still means optional/variant only; persona canon is
  `--canon-only --exclude-tier game_caption`.
- **Clear transcript mismatch.** A tier filter that excludes a transcript
  returns its metadata with `tier_match: false` and zero lines, not "not found".
- **Schema stamping.** `db/build_entity_web.py` and the MCP server read
  `db/SCHEMA_VERSION` instead of hardcoding 1.9.0.
- **Access gate consolidated.** The per-agent checks from the legacy
  shell access test moved into `tests/agent-access-test.py`; the
  extended suite is 11 checks with no lost assertion.
- Counts: database 67 checks, query interface 97 checks.

## Verification

Master audit 18/18; test-db 67/67; query 97/97; caption 13/13; MCP 12/12,
25/25, matrix 8/8 (161 calls); six agent audits 20/20 (Drifter 25/25);
conformance, docs-consistency, onboarding smoke 72/72; extended suite 11/11.

## Asset

`grimoire.db` (schema 1.10.0) plus `.xz`/`.gz` and `SHA256SUMS`.

# v0.39.4 - Ecosystem contract and MCP compatibility

**2026-11-10**

Tooling, documentation and API patch. The database is byte-identical to v0.39.3
(schema 1.9.0, 9,229 transcripts / 125,324 lines / 63,359 sightings).

## What's Changed

- Agnostic contract in `STANDARDS.md`; shared scripts read `series/agents.json`
  and `tests/agnostic-test.py` guards it.
- Template fixture harness, atomic generator, stricter finalize and
  `setup.sh --dry-run`/`GRIMOIRE_DB`.
- Six agents share the setup contract; generated knowledge-web snapshots;
  `tests/agent-access-test.py` proves missing-DB, dangling-link, read-only and
  site-roster behavior.
- MCP `stats` reports `missing_tables`/`schema_version` on a pre-1.9 database;
  README and skill document caption tiers and `v_speakers`.
- Site stats and roster metadata regenerated; card creation deferred.

## Verification

Master audit 18/18; six agent audits 20/20 (Drifter 25/25); template fixture and
real-corpus tests; MCP 12/12, 25/25, matrix 8/8 (161 calls); site check and live
spot check; docs-consistency 5/5.

## Asset

`grimoire.db` plus `.xz`/`.gz` is byte-identical to v0.39.3 and is attached again
so `releases/latest/download/grimoire.db` keeps working.
