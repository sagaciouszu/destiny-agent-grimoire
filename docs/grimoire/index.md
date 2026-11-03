---
section: grimoire
layout: page
title: The Grimoire
category: The Grimoire · Overview
lede: One place to look up Destiny lore, check a quote, and hand the whole archive to an AI without teaching it your filing system.
---

## What it is

The Grimoire is a single database built from committed source files. It holds
books, transcripts, grimoire cards, short dialogue beats, item lore, triumphs and
a hand-picked character index. Search runs through an FTS5 index, so you get the
passage back instead of a list of files to open.

Nothing is fetched at runtime. Once the database is on disk, every lookup is a
local read against that one file.

## What's inside

The current build has 110 books and 1,158 book entries, 1,229 transcripts with
71,221 dialogue lines, 2,889 Destiny 1 grimoire cards, 2,699 short interactions,
58,764 items, 71 triumphs and seals, and 20 curated characters with 1,229
quote-ready lines. The search index covers 120,731 rows.

Those numbers are a map, not a citation. The row you quote is the citation.

## Where it came from

Every content row records its source. Speaker names are cleaned up through aliases
during the build, so one character does not end up split across several spellings.

The archive also carries a quote checker. `verify` takes a line and an optional
speaker, cleans it up the same way as canon, and exits non-zero when the line is
not there. Exact mode wants a whole canonical row, not a fragment. That is the
check to run before putting words in a character's mouth.

## How you can read it

There are four ways in:

- **The command line** is the reference tool. Search, character lines, items,
  books, transcripts, records and quote checks, with JSON output for scripts.
- **The MCP server** gives an AI client the same thing as twelve typed tools over
  a local connection. It is read-only and exposes no arbitrary SQL.
- **The agent skill** is a drop-in instruction file for runtimes that load skills
  instead of MCP servers.
- **`db/capabilities.json`** is the machine-readable manifest of tables, views,
  commands and contracts, for tools that need to discover the surface.

The command line and the MCP server call the same Python layer. Fix a query or a
permission once and both get it.

## The MCP server

MCP is the plug that turns the archive into tools an AI client can call directly.
It wraps the same query layer: twelve read-only tools for search, character
lines, items, books, transcripts, records, stats and quote checks.

It runs locally over stdio, opens the database read-only and never exposes SQL.
That is enough to leave an assistant connected while it works, without giving it
a way to change the archive.

[Set up the MCP server]({{ '/grimoire/mcp/' | url }}) for client configuration and
the full tool list.

## One archive, many agents

The Grimoire is the shared canon for a series of independent agents. A small
registry, `series/agents.json`, records each agent's id, source repository and
entry file. Deployment reads that registry instead of a hard-coded list, so a new
agent is a repository plus one registry row.

The agents do not share memory. They share this archive.

## What it isn't

This is a fan-built, non-commercial project. Destiny, its text, characters and art
belong to Bungie. The database is a reading and checking aid; it is not a
substitute for the source material or for Bungie's own published lore.

## Next

- [Install and query the Grimoire]({{ '/grimoire/install/' | url }})
- [Set up the MCP server]({{ '/grimoire/mcp/' | url }})
- [Troubleshoot a missing database or tool]({{ '/troubleshooting/' | url }})
- [Read the standards](https://github.com/sagaciouszu/destiny-agent-grimoire/blob/master/STANDARDS.md)
