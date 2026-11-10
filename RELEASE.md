# v0.40.3 - Tooling and public-surface hygiene

> **Depends On:** INDEX.md
> **Token Estimate:** ~152 tokens
**2026-11-10**

## What's Changed

- `verify_many` now shares one SQLite connection across a batch of up to 20
  quotes instead of opening a connection per quote.
- `docs-consistency` now fails when a public document carries an internal plan
  or a private absolute path: vault paths, home paths, model/provider notes,
  token budgets, work queues, checkpoint or billing notes, scratch-agent notes
  and plan-only section headings.
- The internal work queue is no longer part of the public repository.
- The Beyond Light page is a factual coverage record; it no longer carries
  phases, decision rules or deliverables.
- The generated slim database is ignored by git.

## Verification

- `bash grimoire-master-audit.sh`: 18/18.
- `bash tests/test-db.sh`: 67/67.
- `bash tests/query-interface-test.sh`: 97/97.
- MCP: 12/12 contract, 25/25 matrix, 8/8 optimization (161 calls).
- `verify_many` positive-match check: 1/1.
- Six agent audits: 20/20 each, Drifter 27/27, Eris 22/22.
- Site `npm run check`: pass.

## Database

No database content change. The release publishes the same `grimoire.db` bytes
as v0.40.2 (sha256 `34b5bf1c…3445d044`, 316,776,448 bytes).

## Asset

`grimoire.db` (316,776,448 bytes, sha256 `34b5bf1c…3445d044`) is attached with
`SHA256SUMS`; the release workflow adds `grimoire.db.xz` and `grimoire.db.gz`
and refreshes the manifest.
