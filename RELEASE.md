# v1.4.0 - MCP adapter and attribution-aware verification

**2026-11-03**

## What's Changed

- **MCP adapter:** official SDK, stdio, six typed tools (`search`, `character`, `item`, `verify`, `list_records`, `stats`), read-only
- **Shared query layer:** `db/api.py` backs both the CLI and MCP; CLI output unchanged
- **Verification:** `verify` gains `--speaker` (attribution) and `--exact` (full line, not fragment)
- **Clean artifact:** database ships in `journal_mode=delete`, no WAL/SHM sidecars; 36 database checks
- **Onboarding:** `./setup.sh --mcp` and an interactive prompt; one install serves both agents
- **Docs:** README contract, agent document parity, source credits and thanks

## Verification

11/11 archive, 18/18 Drifter, 13/13 Eris, 36/36 database, 23/23 interface, 6/6 MCP, conformance PASS, onboarding 24/24.

## Asset

`grimoire.db` (128 MB, content unchanged since v1.3.0) in `journal_mode=delete`. sha256 `0cd21db4c2ef80e001d81b865979aea2370348b61b5d329ca232c3c849f046e8`. Rebuild with `python3 db/migrate.py`.
