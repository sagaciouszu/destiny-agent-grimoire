# v1.8.1 - Character lookup and ranking fixes

**2026-11-03**

## What's Changed

- **Fixed:** character lookup resolves exact names first; `drifter` no longer returns Blue's Ghost
- **Search ranking:** relevance order boosts titles but penalizes item-title matches, keeping transcripts and books visible
- **Docs:** search rank/offset and CLI `--no-rank` documented

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 38/38 database, 29/29 interface, 6/6 MCP, 141-call matrix, extended 5/5, conformance PASS.

## Asset

`grimoire.db` is unchanged (169 MB, sha256 `a3957e1e5f82c38be40baa54038e35734c492d442a8621f727dee55bb89cc226`). `SHA256SUMS` is attached.
