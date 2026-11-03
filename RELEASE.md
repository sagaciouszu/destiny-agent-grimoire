# v1.3.1 - Documentation and verification overhaul

**2026-11-02**

## What's Changed

- **README standard:** banner, version, last push and a Guardian-first quick start, then the agent contract; identical shape in all three repos
- **Release notes:** compact What's Changed format, gated to 40 lines
- **Docs rewritten:** SOUL, TOOLS, INDEX and templates share one section order across both agents
- **New gates:** README contract, command targets, agent parity (setup, gitignore, docs, IDENTITY), measured load tiers, release-note shape
- **New tests:** offline onboarding smoke (24 checks) and link checker (private-repo aware)
- **Fixed:** `orix` renamed to `oryx`; conformance resolves paths through the `lore/` symlink

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 36/36 database, 23/23 interface, conformance PASS, onboarding 24/24.

## Asset

`grimoire.db` content is unchanged since v1.3.0; the asset was refreshed to ship
in `journal_mode=delete` (no WAL/SHM sidecars). sha256
`0cd21db4c2ef80e001d81b865979aea2370348b61b5d329ca232c3c849f046e8`.
Rebuild with `python3 db/migrate.py`.
