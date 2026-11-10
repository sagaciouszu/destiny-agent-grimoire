# v0.40.2 - Truth and onboarding pass

> **Depends On:** INDEX.md
> **Token Estimate:** ~152 tokens
**2026-11-10**

## What's Changed

- Install instructions now match the release: the checksum step selects the
  downloaded file because `SHA256SUMS` lists the plain, xz and gzip assets;
  decompression uses `xz -d` / `gzip -d` (7-Zip on Windows) instead of treating
  a raw stream as a tar archive.
- Compressed asset sizes are stated from the published files: 41.9 MiB xz and
  78.6 MiB gzip.
- Live gate counts are documented from the gates themselves: database 67,
  query interface 97, agent layout 108, master audit 18/18.
- Coverage-note figures are labelled as entries, since the table spans
  activities, events and seasons.
- Build-identity wording replaces era guesses; the Beyond Light roadmap is
  marked historical and no longer claims to track the live build.
- The shared-helper guard now has canonical copies under
  `tests/agent-helpers/` and fails on drift or a missing canonical file instead
  of silently skipping.
- Nineteen MCP tools gained `Returns:` contracts; three terse descriptions were
  expanded; the MCP README documents the tier parameters and the
  empty-result-versus-`ToolError` distinction.
- `search --json` no longer runs a second FTS pass just to compute a total the
  JSON path never prints.
- `docs-consistency` now rejects the stale sizes, gate counts and decompression
  instructions that this release fixes.

## Database

No database content change. This release publishes the same `grimoire.db`
bytes as v0.40.1 (sha256 `34b5bf1c…3445d044`, 316,776,448 bytes), so an existing
install needs no re-download.

## Verification

- `bash grimoire-master-audit.sh`: 18/18.
- `bash tests/test-db.sh`: 67/67.
- `bash tests/query-interface-test.sh`: 97/97.
- `python3 tests/caption-test.py`: pass.
- `python3 tests/agent-access-test.py`: pass.
- MCP: 12/12 contract, 25/25 matrix, 8/8 optimization.
- Six agent audits: 20/20 each, Drifter 27/27, Eris 22/22.
- Site `npm run check`: pass.
