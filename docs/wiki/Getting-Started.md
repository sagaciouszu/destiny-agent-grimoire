# Getting Started

## Requirements

| Need | Version | Used for |
|---|---|---|
| Git | any current release | clone and updates |
| Python | 3.8+ | migration, query CLI, tests |
| `curl` | any current release | optional prebuilt database download |
| Python | 3.10+ | optional MCP adapter |

The query CLI and tests use the Python standard library only. No API keys or
network access are required at runtime.

## Clone

```bash
git clone https://github.com/sagaciouszu/destiny-agent-grimoire.git
cd destiny-agent-grimoire
```

On Windows, use Git Bash or PowerShell with Git for Windows installed.

## Get the database

Choose **one** path.

**Download the prebuilt database** (seconds):

```bash
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
```

Windows PowerShell:

```powershell
curl.exe -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
```

Smaller companions of the same bytes live at the same endpoint:
`grimoire.db.xz` (41.9 MiB, `xz -d`; use 7-Zip on Windows) and
`grimoire.db.gz` (78.6 MiB, `gzip -d`; use 7-Zip on Windows). The gzip asset
needs nothing beyond gzip, which is what Android apps decompress with
`GZIPInputStream`.

**Or build from this checkout** (about two minutes):

```bash
python3 db/migrate.py
```

The prebuilt asset is checked against the release `SHA256SUMS` by the agent
installers. To check it yourself:

```bash
grep '  grimoire.db$' SHA256SUMS | sha256sum -c -
```

`SHA256SUMS` also lists the `.xz` and `.gz` companions. Checking the whole file
fails unless every listed asset is present, so select the line for the file you
actually downloaded.

## First queries

```bash
python3 db/query.py stats
python3 db/query.py search "Crota" --limit 5
python3 db/query.py character "Eris Morn" --limit 10
python3 db/query.py verify --speaker "Eris Morn" --exact "You did well to find this point of infestation."
```

`stats` confirms the database opened. `verify` exits non-zero when a quote is
not canon, which is the safety primitive every agent uses.

## Optional MCP setup

```bash
bash mcp-server/install.sh
```

The installer creates a private virtualenv, installs the pinned MCP SDK and
prints a client config snippet. See [MCP Server](MCP-Server.md).

## Next steps

- [Database](Database.md) for enrichment and rebuilds
- [Query CLI](Query-CLI.md) for filters and JSON output
- [Agent Setup](Agent-Setup.md) to deploy the character agents
- [Testing and Auditing](Testing-and-Auditing.md) before changing anything
