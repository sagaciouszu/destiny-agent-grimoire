# Destiny Agent Grimoire - Index

Short orientation. Counts and the full guide live in `README.md`; the contract is
`STANDARDS.md`.

## Where to start

| Need | File |
|---|---|
| Human setup, counts, maintenance | `README.md` |
| Agent skill | `skills/destiny-grimoire/SKILL.md` |
| Schema and table contract | `db/README.md`, `db/schema.sql` |
| Naming, provenance, quote policy, gates | `STANDARDS.md` |
| Machine-readable interface | `db/capabilities.json` |
| MCP adapter (optional) | `mcp-server/README.md` |

## Quick commands

```bash
python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
python3 db/query.py character "eris" --limit 20
python3 db/query.py verify "Absolutely not." --speaker "Eris Morn" --exact   # exit 0 when canon, 1 otherwise
```

The database is a build artifact: `python3 db/migrate.py`, or download the asset
from the latest release. `source/` is ingestion input only; never treat it as
canon at runtime.
