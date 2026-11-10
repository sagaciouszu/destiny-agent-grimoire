# Reference Commands

Runtime commands for using the archive and the agents. Run them from the
`destiny-agent-grimoire` checkout unless a step says otherwise.

## Get the database

```bash
mkdir -p db
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
python3 db/query.py stats
```

## Query

```bash
python3 db/query.py search "Crota" --limit 5
python3 db/query.py search "witness" --entity "The Witness" --limit 5
python3 db/query.py entity "Savathûn"
python3 db/query.py character "Eris Morn" --limit 20
python3 db/query.py transcript "Contact - Io" --speaker "Drifter"
python3 db/query.py activity salvations-edge
python3 db/query.py event festival-of-the-lost
python3 db/query.py coverage
python3 db/query.py stats
```

Add `--json` to any command for scripts. Search and list commands accept
`--limit` and `--offset`; search accepts `--rank`.

## Verify a quote

```bash
python3 db/query.py verify "<line>" --speaker "Eris Morn" --exact
python3 db/query.py verify-many "<line one>" "<line two>" --speaker "Eris Morn"
```

A non-zero exit means the line is not in the corpus. Use `--speaker` when the
attribution matters and `--exact` for a full line.

## Run the agents

Deploy every ready agent into OpenCode:

```bash
bash scripts/sync-live-agents.sh
```

Preview the plan first:

```bash
bash scripts/sync-live-agents.sh --dry-run
```

OpenClaw:

```bash
bash scripts/sync-live-agents.sh --openclaw
```

Set up one agent repository:

```bash
cd destiny-agent-eris-morn
bash setup.sh ../destiny-agent-grimoire
```

Use `--no-mcp` to skip the optional MCP install. See
[Agent Setup](Agent-Setup.md) for destinations and platform notes.

## MCP

```bash
bash mcp-server/install.sh
./mcp-server/run.sh
```

The installer prints a client config snippet. See [MCP Server](MCP-Server.md)
for the tool list and client examples.

## Useful environment variables

| Variable | Purpose |
|---|---|
| `GRIMOIRE_DB` | alternate database path for the CLI |
| `AGENT_REPOS_DIR` | parent directory for the agent repositories |
| `SERIES_MANIFEST` | alternate agent registry |
| `OPENCODE_AGENTS` | OpenCode agent destination |
| `OPENCLAW_ROOT` | OpenClaw root |
| `NO_RELOAD=1` | skip the OpenCode reload after sync |
