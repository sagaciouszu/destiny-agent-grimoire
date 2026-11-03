# v1.7.1 - Clone-mode quote scan fix

**2026-11-03**

## What's Changed

- **Fixed:** Drifter quote verification no longer scans a cloned `lore/` archive; it previously flagged unrelated files and failed fresh-clone audits
- **Removed:** an unrelated session note accidentally committed in v1.7.0
- Fresh-clone onboarding now reports 18/18 again

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 38/38 database, 29/29 interface, 6/6 MCP, extended 5/5, conformance PASS.

## Asset

`grimoire.db` is unchanged (170 MB, sha256 `c7fa3acc80f63ed43f0b90acb1e9f09ddb5dbaffdd161d4100a7285c3354072b`). `SHA256SUMS` is attached.
