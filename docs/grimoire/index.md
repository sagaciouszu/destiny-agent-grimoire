---
section: grimoire
layout: page
title: The Grimoire
category: The Grimoire · Overview
lede: A single, citable Destiny archive, plus the interfaces that let people and agents read it without guessing.
---

## What it is

The Grimoire is one SQLite database built from committed source files. It holds
books, transcripts, grimoire cards, dialogue interactions, item lore, triumphs and
a curated character index. Search runs through an FTS5 index, so a query returns
the passage rather than a list of files to open.

Nothing is fetched at runtime. Once the database exists, the archive is a local
file and every query is a read against it.

## The archive

The current build contains 110 books and 1,158 book entries; 1,229 transcripts
with 71,221 dialogue lines; 2,889 Destiny 1 grimoire cards; 2,699 short
interactions; 58,764 items; 71 triumphs and seals; and 20 curated characters with
1,229 quote-ready lines. The search index covers 120,731 rows.

Those counts are useful for orientation, not for citation. The row you quote is
the citation.

## Provenance and verification

Every content row records where it came from. Speaker names are canonicalised
through aliases during the build, so the same character is not split across
spellings.

The archive also ships a quote-safety primitive. `verify` takes a line and an
optional speaker, normalises it the same way as canon, and exits non-zero when the
line is absent. Exact mode requires a full canonical row rather than a fragment.
That is the check to run before putting words in a character's mouth.

## Interfaces

There are four supported ways to read the archive:

- **The query CLI** is the reference interface. It exposes search, character
  lines, items, books, transcripts, records and quote verification, with JSON
  output for scripts.
- **The MCP server** wraps the same query layer in twelve typed tools over local
  stdio. It is read-only, applies limits and exposes no arbitrary SQL.
- **The agent skill** is a drop-in instruction file for runtimes that load skills
  rather than MCP servers.
- **`db/capabilities.json`** is the machine-readable manifest of tables, views,
  commands and contracts, for tooling that needs to discover the surface.

The CLI and the MCP server call the same Python API. A fix or a permission rule
applies to both.

## The MCP tools

The MCP adapter exposes twelve read-only tools. Each wraps one slice of the query
layer, so an agent can ask a direct question instead of constructing shell
commands.

- `search` — full-text search across books, transcripts, cards, interactions,
  items and records, with an optional source filter.
- `character` — curated lines for a character, or every transcript line with
  `all_lines`.
- `character_info` — aliases, curated quote count and spoken-line count for a
  character.
- `item` — item lore and metadata by slug.
- `find_item` — find items by a title or slug fragment.
- `book` — book metadata and its entries.
- `transcript` — transcript metadata and dialogue lines, optionally filtered by
  speaker.
- `record` — a triumph or seal by slug or title.
- `list_records` — cheap listings of books, characters, speakers or records.
- `stats` — row counts, top item types and top speakers.
- `verify` — check one quote, optionally with a speaker and exact mode.
- `verify_many` — check up to twenty quotes in one call.

All twelve share the same normalisation and read-only database connection. A
quote that fails `verify` is not canon, whichever interface asked.

## The series

The Grimoire is the shared canon for a series of independent agents. A small
registry, `series/agents.json`, records each agent's id, source repository and
entry file. Deployment reads that registry rather than hard-coding a list, so a
new agent is a repository plus one registry row.

The agents do not share memory. They share this archive.

## What it is not

The archive is fan-built and non-commercial. Destiny, its text, characters and art
belong to Bungie. The database is a reading and verification aid; it is not a
substitute for the source material or for Bungie's own published lore.

## Next

- [Install and query the Grimoire]({{ '/grimoire/install/' | url }})
- [Troubleshoot a missing database or MCP tool]({{ '/troubleshooting/' | url }})
- [Read the standards](https://github.com/sagaciouszu/destiny-agent-grimoire/blob/master/STANDARDS.md)
