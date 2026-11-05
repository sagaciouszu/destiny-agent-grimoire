# Architecture

## Data flow

```text
source/ + archive/          build inputs
        |
        v
db/migrate.py               schema, canon tables, classification
        |
        v
db/grimoire.db              runtime source of truth
        |
        +--> db/query.py    shell interface
        +--> mcp-server/    typed MCP interface
        +--> agent repos    generated personas and suites
```

The database is built once and read many times. Runtime code never parses
markdown, scrapes a site or invents a missing field.

## Main directories

| Path | Role |
|---|---|
| `db/` | schema, migration, taxonomy, query CLI |
| `source/` | ingested markdown: books, cards, transcripts, records, items |
| `archive/` | raw scraper output and fetch scripts |
| `compendium/` | character quote index feeding the character tables |
| `scripts/` | ingestion, reporting, release and sync helpers |
| `tests/` | archive gates, agent gates, shared suite runner |
| `series/` | agent registry and suite baseline |
| `skills/` | agent-facing skill instructions |
| `mcp-server/` | optional stdio MCP adapter |
| `docs/` | taxonomy, discovery, gap ledger and this wiki |

## Build time and runtime

**Build time** covers ingestion, normalisation, classification, enrichment and
index construction. It may read local files or the network.

**Runtime** covers `query.py`, the MCP server and agent tools. It opens SQLite
read-only and does no network access.

Keeping that line sharp is what makes quote verification and agent behaviour
predictable.

## Discovery layer

Four independent axes sit beside the canon tables:

- expansion
- official season or episode number
- activity
- event occurrence

`transcript_classification`, `item_classification` and
`document_classification` hold the assignments. They are additive: existing
tables and queries keep working even if the discovery layer is rebuilt.

## Agent deployment

`series/agents.json` is the registry. Sync writes a primary agent file, a
read-only consult file and a workspace directory for each ready agent.

Agents are independent repositories. They mount this archive as `lore/` and
share its database, query CLI, tests and MCP adapter.

## Why SQLite

- single-file distribution and checksummed releases
- FTS5 search and a verification index in the same file
- read-only URI connections at runtime
- no service to operate
- easy backup and local inspection
