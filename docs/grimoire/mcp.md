---
layout: page
title: MCP Server
category: The Grimoire · MCP
lede: MCP is the adapter that lets an AI client ask the archive questions as tools, instead of running shell commands itself.
section: grimoire
---

## What it is

The MCP server wraps the same query layer as `db/query.py`. Your client gets a
set of named tools — search, character lines, item lore, quote checks — and calls
them directly. You do not have to teach the model a command line.

It runs locally over stdio. There is no network service, no port and no account.
The client starts the server, talks to it through a pipe, and stops it when the
session ends.

## Set it up

From the Grimoire checkout:

<pre><code>bash mcp-server/install.sh</code></pre>

The installer creates a small virtual environment, installs the locked
dependencies, and prints a client configuration snippet. Point your client at the
`mcp-server/run.sh` path it prints. Use the absolute path if the client starts in
a different directory.

A typical local configuration looks like this:

<pre><code>{
  "mcp": {
    "servers": {
      "grimoire": {
        "type": "local",
        "command": ["/absolute/path/to/destiny-agent-grimoire/mcp-server/run.sh"]
      }
    }
  }
}</code></pre>

The exact shape depends on your client. If it only accepts remote servers, put a
local bridge in front of the stdio process.

## The tools

There are twelve, all read-only:

- `search` — full-text search across books, transcripts, cards, interactions,
  items and records, with an optional source filter.
- `character` — curated lines for a character, or every transcript line with
  `all_lines`.
- `character_info` — aliases, quote count and spoken-line count for a character.
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

The two verification tools are the important ones. A line that fails `verify` is
not canon, even if it sounds right.

## Safety

The database is opened read-only. There is no SQL tool, no write path and no
network access. Limits are clamped, long text is trimmed, and queries are capped
before they reach SQLite.

That makes the server safe to leave connected while you work. It also means it
cannot fix or ingest anything; those steps stay in the repository.

## If it will not connect

See [MCP tools do not appear]({{ '/troubleshooting/#mcp-tools' | url }}) for the
usual causes: missing virtual environment, wrong path, or a client that cannot
launch a local process.
