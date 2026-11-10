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

# v0.39.2 - Live-build refresh tooling

> **Depends On:** STANDARDS.md
> **Token Estimate:** ~0.8K tokens

**2026-11-10**

Tooling release, schema 1.9.0. `archive/data/builds.json` is now the data-driven
build registry; `archive/data/live-builds/<build>.jsonl` holds future builds
with build-scoped slugs; `scripts/refresh-live-build.py` automates unpack,
merge, resolve, extract, validate, combine, drift, register, rebuild and gates.
Current-build no-op, `--dry-run` and `--self-test` included.

## Verification

Master audit 14/14; test-db 65/65; caption 12/12; query 91/91; MCP suites green;
refresh self-test and no-op pass.

## Asset

`grimoire.db` (plus `.xz`/`.gz`) attached to this release.
