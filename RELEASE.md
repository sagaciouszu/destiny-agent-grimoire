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

# v0.39.3 - Refresh tooling hardening

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.9K tokens

**2026-11-10**

Tooling patch. The database is byte-identical to v0.39.2 (schema 1.9.0, 9,229
transcripts / 125,324 lines / 63,359 sightings). This release fixes the refresh
script's failure and multi-build paths after review.

## What's Changed

- **Failure rollback.** A failed gate restores `archive/data/builds.json` and the previous
  tier file, so a failed refresh cannot make the next run a no-op against a
  half-built database.
- **Correct drift baseline.** Drift compares against the latest registered
  build (`live-builds/<current>.jsonl` when present), not always the original
  `captions-live.jsonl`.
- **No silent partial tiers.** Language validation must produce its output and
  report; a crash aborts the refresh instead of silently omitting a package.
- **`--force` guard.** Forcing the registered current build is refused because
  it would create a second per-build file and duplicate sightings.
- **Source identity.** `destiny2.exe` sha256 is checked before and after
  extraction (optional `--expected-sha256`) and recorded in the build note. A
  source change mid-run aborts.
- **Counts propagate.** After a successful rebuild the script exports site
  stats, syncs doc counts and runs `tests/docs-consistency.py`; failures are
  reported with a nonzero exit.
- **Drift detail.** Text comparison is raw, so punctuation/case-only changes
  are reported; `latest_live_build` sorts by date/numeric id; `--report out.json`
  no longer crashes on an empty dirname.

## Verification

Refresh self-test, current-build no-op, synthetic dry-run, master audit 14/14,
test-db 65/65, caption 12/12, docs-consistency 5/5. DB artifact unchanged.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) is byte-identical to v0.39.2 and is attached
again so `releases/latest/download/grimoire.db` keeps working.
