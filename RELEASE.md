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

11/11 archive, 18/18 Drifter, 13/13 Eris, 35/35 database, 23/23 interface, conformance PASS, onboarding 24/24.

## Asset

`grimoire.db` is unchanged since v1.3.0 (sha256 `8ed73a8682e7405c09f01663d499d1c652c7b367185a7440e06f11d01bb4c4fb`). No rebuild needed; `python3 db/migrate.py` reproduces it.
