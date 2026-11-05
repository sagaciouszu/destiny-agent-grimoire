# Destiny Agent Grimoire Wiki

The Grimoire is one canonical SQLite archive for Destiny lore, dialogue, items,
activities, seasons and events. Agents and MCP clients query the same database,
so a fact verified in one place is verified everywhere.

This directory is the versioned copy of the project wiki. It is safe to edit and
review in the same pull request as the code.

## Start here

| I want to... | Read |
|---|---|
| Set up the archive | [Getting Started](Getting-Started.md) |
| Understand the pieces | [Architecture](Architecture.md) |
| Build or rebuild the database | [Database](Database.md) |
| Query from a shell | [Query CLI](Query-CLI.md) |
| Connect an MCP client | [MCP Server](MCP-Server.md) |
| Work with the agents | [Agent Series](Agent-Series.md), [Agent Setup](Agent-Setup.md) |
| Run the gates | [Testing and Auditing](Testing-and-Auditing.md) |
| Fix a problem | [Troubleshooting](Troubleshooting.md) |
| Find a command fast | [Reference Commands](Reference-Commands.md) |
| Install on my OS | [Platform Notes](Platforms.md) |

## Core principle

The database is the runtime source of truth. Do not parse `source/` markdown at
runtime, and do not scrape live sites during a query. Sources are ingested at
build time; agents read the built database.

## What makes it different

- **One archive, many voices.** Five character agents share the same canon.
- **Quote safety first.** `verify` checks a line before an agent may quote it.
- **Additive discovery.** Expansion, season, activity and event classifications
  sit beside the canon tables and never rewrite them.
- **Honest gaps.** Missing coverage carries an explicit status instead of a
  guess.
- **Read-only runtime.** The CLI and MCP adapter open SQLite in read-only mode.

## Outside this wiki

- `README.md` - quick start and repository map
- `STANDARDS.md` - schema, provenance and change rules
- `docs/TAXONOMY.md` - classification contract
- `docs/DISCOVERY.md` - why discovery is organised this way
- `docs/GAPS.md` - current coverage ledger
