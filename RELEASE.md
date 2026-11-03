# v1.5.0 - Faster verification and hardened delivery

**2026-11-03**

## What's Changed

- **Verification index:** `verify_fts` cuts quote checks from ~58 ms to ~1.4 ms; database is now 164 MB and reproducible
- **Delivery integrity:** onboarding verifies the prebuilt database against release `SHA256SUMS` and rejects mismatches
- **MCP supply chain:** dependencies are hash-locked and installed with `--require-hashes`; stdio-only security posture documented
- **Failure handling:** corrupt, truncated or missing databases fail cleanly in CLI and MCP; inputs are bounded
- **Regression suite:** robustness (25 checks), MCP matrix (125 calls, 3 concurrent clients), checksum faults, DB/source cross-check
- **Privacy:** seeded runtime memory is owner-only (`0600`)

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 37/37 database, 23/23 interface, 6/6 MCP, extended 5/5 groups, conformance PASS.

## Asset

`grimoire.db` (164 MB) in `journal_mode=delete` with the verification index. sha256 `285e31e6cd5415f7a5d92b15ffde9cb41d0c260df2fc451fba838f9b10a401e9`. `SHA256SUMS` is attached. Rebuild with `python3 db/migrate.py`.
