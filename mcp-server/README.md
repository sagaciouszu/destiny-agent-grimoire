# Grimoire MCP server

Typed tool access to `db/grimoire.db` over the Model Context Protocol (stdio).
Uses the official MCP Python SDK (`mcp==2.3.0`). Read-only.

## Why

- **One adapter, every agent.** The server lives in the archive, so Drifter, Eris
  and any future agent share one install and one database.
- **No shell required.** The CLI needs a shell and Python on the host; MCP clients
  (OpenCode, Claude Desktop, Cursor, hosted agents) call the same tools directly.
- **Typed, not typed-by-hand.** Structured arguments and JSON results replace
  shell quoting and path handling, so tool calls fail less and cost fewer tokens.
- **Guardrails in one place.** Read-only connections, no SQL tool, clamped limits
  and quote verification are enforced by the server for every client.
- **Portable later.** The same server can run locally over stdio or be hosted for
  a team without changing the tools.

## Install

```bash
bash mcp-server/install.sh
```

That creates `mcp-server/.venv`, installs the pinned SDK and prints a client
config snippet. Agent workspaces do it during onboarding:

```bash
./setup.sh --mcp        # or answer yes at the MCP prompt
```

The adapter lives in this archive, so **one install serves every agent** that
mounts it (Drifter, Eris, or any other runtime).

The virtualenv is gitignored. The CLI stays dependency-free; only this adapter
needs the SDK.

## Run

```bash
./mcp-server/run.sh
```

It speaks MCP on stdio and exits when the client disconnects.

## Client configuration

OpenCode (`~/.config/opencode/opencode.json`):

```json
{
  "mcp": {
    "servers": {
      "grimoire": {
        "type": "local",
        "command": ["/absolute/path/to/destiny-agent-grimoire/mcp-server/run.sh"]
      }
    }
  }
}
```

From an agent workspace, the archive is usually mounted at `lore/`, so the same
path is `<agent>/lore/mcp-server/run.sh`. Use an absolute path in client config.

## Tools

| Tool | Arguments | Returns |
|---|---|---|
| `search` | `query`, `type?`, `limit=10`, `full=false` | `{count, rows}` with snippet or full text |
| `character` | `name`, `about?`, `all_lines=false`, `limit=20` | `{found, header, rows}` |
| `item` | `slug` | item row, `text` trimmed |
| `verify` | `quote`, `speaker?`, `exact=false` | `{quote, verified, matches}` with `exact` flags |
| `list_records` | `kind`, `limit=50` | `{count, rows}` for books, characters, speakers, records |
| `stats` | none | row counts, top item types, top speakers |

MCP limits clamp to 1-100 to protect the agent's context; the CLI is not clamped
to 100 (the shared API allows up to 10,000). Full text is trimmed to 4000
characters per row.
`verify` is the quote-safety primitive: `verified` is true only for canonical text.
`speaker` requires attribution (books and items, which have no speaker, are then
excluded); `exact` requires the normalized quote to equal a full canonical row
instead of matching a fragment.

## Safety

- SQLite is opened with URI `mode=ro`; writes fail at the driver level.
- No arbitrary SQL tool is exposed. The six query shapes are the whole surface.
- No network access. The database path is resolved from `GRIMOIRE_DB` or
  `db/grimoire.db`.

## Test

```bash
mcp-server/.venv/bin/python tests/mcp-test.py
```

Covers tool registration, search, verify accept/reject, limit clamping, the
read-only guard and a real stdio handshake (`initialize`, `tools/list`,
`tools/call`).
