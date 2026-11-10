# Destiny Agent Grimoire Wiki

The Grimoire is one canonical SQLite archive for Destiny lore, dialogue, items,
activities, seasons and events. Agents and MCP clients query the same database,
so a fact verified in one place is verified everywhere.

This wiki documents the runtime artifact: how to install it, query it, connect
MCP clients, deploy the agents and fix problems.

## Start here

| I want to... | Read |
|---|---|
| Set up the archive | [Getting Started](Getting-Started.md) |
| Query from a shell | [Query CLI](Query-CLI.md) |
| Find a command fast | [Reference Commands](Reference-Commands.md) |
| Connect an MCP client | [MCP Server](MCP-Server.md) |
| Work with the agents | [Agent Series](Agent-Series.md), [Agent Setup](Agent-Setup.md) |
| Install on my OS | [Platform Notes](Platforms.md) |
| Fix a problem | [Troubleshooting](Troubleshooting.md) |
| Check limits and provenance | [Limits and provenance](https://sagaciouszu.github.io/destiny-agent-grimoire-site/grimoire/limits/) |

## Core principle

The database is the runtime source of truth. Do not parse `source/` markdown at
runtime, and do not scrape live sites during a query. Sources are ingested when
the database is built; agents read the built database.

## What the runtime gives you

- **One archive, many voices.** Six character agents share the same canon.
- **Quote safety first.** `verify` checks a line before an agent may quote it.
- **Additive discovery.** Expansion, season, activity and event classifications
  sit beside the canon tables and never rewrite them.
- **Honest gaps.** Missing coverage carries an explicit status instead of a
  guess.
- **Read-only runtime.** The CLI and MCP adapter open SQLite in read-only mode.

## Limits

The user-facing honesty contract is the site page linked above. It records the
caption tier, missing timelines, source gaps and non-completeness. If a claim
elsewhere conflicts with that page, that page wins.

## Developer documentation

This wiki is not build or process documentation. Build steps, schema internals,
provenance rules and test gates live in the repository: `README.md`,
`STANDARDS.md`, `docs/process/` and `tests/README.md`.
