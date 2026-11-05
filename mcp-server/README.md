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

Linux/macOS:

```bash
./mcp-server/run.sh
```

Windows (Git Bash or cmd):

```bat
mcp-server\run.cmd
```

Both launchers detect the virtualenv layout (`.venv/bin` or `.venv/Scripts`).

It speaks MCP on stdio and exits when the client disconnects. The process is
**stdio-bound**: OpenCode starts it and keeps it running for the session, then
stops it. If you launch it by hand, keep that window open while any client is
using it; closing it drops the connection. Do not run it as a long-lived
background service.

## Client configuration

OpenCode (`~/.config/opencode/opencode.json`), from an agent workspace where the
archive is mounted at `lore/`:

```json
{
  "mcp": {
    "servers": {
      "grimoire": {
        "type": "local",
        "command": ["lore/mcp-server/run.sh"]
      }
    }
  }
}
```

On Windows point at the launcher instead:

```json
{
  "mcp": {
    "servers": {
      "grimoire": {
        "type": "local",
        "command": ["lore\\mcp-server\\run.cmd"]
      }
    }
  }
}
```

Some clients resolve commands relative to their working directory and some
require an absolute path. Use whichever your client documents; do not commit
machine-specific paths to this repository.

### Verify the install

One command performs a real `initialize` -> `tools/list` handshake and prints
the exposed tools:

```bash
bash mcp-server/probe.sh        # Unix
python mcp-server\probe.py      # Windows
```

### OpenClaw

OpenClaw's update doctor probes MCP servers the same way, so its config must
use an **absolute path** to the launcher; a bare `run.sh` cannot be resolved
from the doctor's working directory and is reported as "not started for update
validation":

```json
{
  "mcp": {
    "servers": {
      "grimoire": {
        "command": ["/absolute/path/to/destiny-agent-grimoire/mcp-server/run.sh"]
      }
    }
  }
}
```

Replace the prefix with your checkout (or the workspace-mounted
`lore/mcp-server/run.sh`). After an OpenClaw update, confirm the tool schema:

```bash
openclaw doctor --lint --only core/doctor/runtime-tool-schemas
```

If the doctor still reports the server as not started, run the probe above by
hand to separate a config-path problem from a server problem.

## Tools

| Tool | Arguments | Returns |
|---|---|---|
| `search` | `query`, `type?`, `limit=10`, `full=false`, `offset=0`, `rank=true`, `activity?`, `season?`, `event?`, `expansion?`, `class_tag?` | `{count, total, next_offset, rows}` |
| `character` | `name`, `about?`, `all_lines=false`, `limit=20` | `{found, header, rows}` |
| `item` | `slug` | item row, `text` trimmed |
| `verify` | `quote`, `speaker?`, `exact=false` | `{quote, verified, matches}` with `exact` flags |
| `list_records` | `kind`, `limit=50` | `{count, rows}` for books, characters, speakers, records, activities, seasons, events |
| `stats` | none | row counts, top item types, top speakers |
| `book` | `ref`, `limit=20`, `offset=0`, `full=false` | book metadata and entries |
| `transcript` | `ref`, `speaker?`, `limit=50`, `offset=0`, `full=false`, `include_stage=false` | transcript metadata and lines |
| `find_item` | `query`, `limit=10`, `offset=0` | items matching a title or slug fragment |
| `record` | `ref` | triumph or seal details |
| `verify_many` | `quotes`, `speaker?`, `exact=false` | up to 20 quote checks at once |
| `character_info` | `name` | aliases, quote count, spoken lines |
| `activities` | `activity_type?`, `season?`, `event?`, `limit=100`, `offset=0` | raids, dungeons and seasonal activities with coverage |
| `activity` | `ref`, `limit=50`, `offset=0` | activity details, coverage, speakers, transcripts |
| `seasons` | none | all 28 seasons/episodes with official numbers and coverage |
| `events` | none | rotating events with coverage and occurrence counts |
| `event` | `ref` | event details, yearly occurrences and transcripts |
| `coverage` | none | coverage matrix, gap lists and `coverage_notes` statuses/evidence |

MCP limits clamp to 1-100 to protect the agent's context; the CLI is not clamped
to 100 (the shared API allows up to 10,000). Full text is trimmed to 4000
characters per row.
`verify` is the quote-safety primitive: `verified` is true only for canonical text.
It uses the verification index for speed and falls back to a full scan for
mid-word fragments.
`speaker` requires attribution (books and items, which have no speaker, are then
excluded); `exact` requires the normalized quote to equal a full canonical row
instead of matching a fragment.

## Resources

Read-only JSON resources for discovery without tool calls:

- `grimoire://books` - all lore books
- `grimoire://characters` - curated characters
- `grimoire://records` - triumphs and seals
- `grimoire://stats` - row counts
- `grimoire://activities` - activities with coverage
- `grimoire://seasons` - official seasons and episodes
- `grimoire://events` - rotating events
- `grimoire://coverage` - coverage matrix and gaps
- `grimoire://book/{slug}`, `grimoire://transcript/{slug}`,
  `grimoire://character/{slug}`, `grimoire://record/{slug}` - full documents

## Prompts

- `quote_safe_lookup(topic)` - search, then verify every quote before use
- `character_brief(name)` - metadata plus verified lines for a character brief

## Safety

- SQLite is opened with URI `mode=ro`; writes fail at the driver level.
- No arbitrary SQL tool is exposed. The eighteen query shapes are the whole surface.
- No network access. The database path is resolved from `GRIMOIRE_DB` or
  `db/grimoire.db`.
- Inputs are bounded: queries 1-500 chars, quotes 1-2000, limits 1-100.
- User text is never interpolated into SQL. Search runs as FTS5 syntax when
  valid and falls back to quoted literal terms, so punctuation cannot break or
  escape the query.
- Prompts are sanitized: control characters and bidi/zero-width marks are
  stripped, double quotes neutralized, and topics capped at 300 chars.
- `verify` matches speakers on name boundaries and ignores a leading "The";
  `ris` and `Morn` do not satisfy `Eris Morn`, while `Eris` and `Drifter` do.

## Transport security

- **stdio only.** The server has no TCP listener, no port and no authentication
  surface; the client starts it and talks over its own pipes.
- Access is therefore the client's local user context. Run it as the user who
  should be able to read the archive.
- Shared or hosted use needs an authenticated wrapper or proxy in front of it;
  that is deliberately not built in.
- The SDK is installed from a hash-locked requirements file into a gitignored
  virtualenv (`--require-hashes`).

## Test

```bash
mcp-server/.venv/bin/python tests/mcp-test.py
```

Covers tool registration, search, verify accept/reject, limit clamping, the
read-only guard and a real stdio handshake (`initialize`, `tools/list`,
`tools/call`).
