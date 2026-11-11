# Grimoire MCP server

Typed tool access to `db/grimoire.db` over the Model Context Protocol (stdio).
Uses the official MCP Python SDK (`mcp==2.3.0`). Read-only.

## Why

- **One adapter, every agent.** The server lives in the archive, so every
  destiny agent in the series shares one install and one database.
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
config snippet. It picks the hash-locked requirements file for your platform:
`requirements.lock.txt` on Unix or `requirements.windows.lock.txt` on Windows
(win_amd64, including the Windows-only `pywin32`). Agent workspaces do it during
onboarding:

```bash
./setup.sh --mcp        # or answer yes at the MCP prompt
```

The adapter lives in this archive, so **one install serves every agent
in the series** that mounts it (Drifter, Eris, Calus, Zavala, Ghost, Mara Sov,
or any other runtime entry point).

The virtualenv is gitignored. The CLI stays dependency-free; only this adapter
needs the SDK.

## Run

Linux/macOS:

```bash
./mcp-server/run.sh
```

Windows (cmd or Git Bash):

```bat
mcp-server\run.cmd
```

Windows (PowerShell):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File mcp-server\run.ps1
```

All three launchers detect the virtualenv layout (`.venv/bin` or
`.venv/Scripts`). If your ExecutionPolicy blocks scripts, keep using `run.cmd`
or invoke PowerShell with `-ExecutionPolicy Bypass` as shown above.

It speaks MCP on stdio and exits when the client disconnects. The process is
**stdio-bound**: OpenCode starts it and keeps it running for the session, then
stops it. If you launch it by hand, keep that window open while any client is
using it; closing it drops the connection. Do not run it as a long-lived
background service.

## Database compatibility

The adapter targets schema **1.11.0**. It does not invent a schema upgrade.

- `stats` includes `caption_sightings`. On a pre-1.9 database the response
  carries `missing_tables: ["caption_sightings", ...]` and omits that count
  instead of failing the call. Show the gap; do not present the counts as
  complete.
- `character` rows carry `source_tier`, and the header names the
  `game_caption` tier when present. A caption line is searchable canon but not
  persona canon; filter `source_tier` explicitly when a caller needs the
  curated voice only.
- `list_records(kind="speakers")` is a discovery listing. It includes
  caption-only names and is not a canon roster.
- If a table or column is missing, rebuild the database from the current
  release asset or `python3 db/migrate.py` rather than editing it in place.

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

On Windows point at either launcher:

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

PowerShell variant (add the policy flags so a locked-down host still runs it):

```json
{
  "mcp": {
    "servers": {
      "grimoire": {
        "type": "local",
        "command": ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", "lore\\mcp-server\\run.ps1"]
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
| `activities` | `activity_type?`, `season?`, `event?`, `limit=100`, `offset=0` | raids, dungeons and seasonal activities with coverage |
| `activity` | `ref`, `limit=50`, `offset=0` | activity details, coverage, speakers, transcripts |
| `book` | `ref`, `limit=20`, `offset=0`, `full=false` | book metadata and entries |
| `character` | `name`, `about?`, `all_lines=false`, `limit=20`, `offset=0`, `canon_only=false`, `class_tag?`, `tier?`, `exclude_tier?` | `{found, header, rows}`; rows carry `source_tier`, and the header names the caption tier when present |
| `character_info` | `name` | aliases, quote count, spoken lines |
| `coverage` | none | coverage matrix, gap lists and `coverage_notes` statuses/evidence |
| `entity` | `ref`, `kind?`, `limit=10`, `include_unreviewed=false` | ranked candidates (exact folded match first; phonetic fallback flagged `fuzzy` with `score <= 0.5`); exact match also returns aliases, relations, document counts and top documents |
| `event` | `ref` | event details, yearly occurrences and transcripts |
| `events` | none | rotating events with coverage and occurrence counts |
| `find_item` | `query`, `limit=10`, `offset=0` | item rows with flavor-text snippets and linked lore titles (no follow-up `item` call needed for most lookups) |
| `item` | `slug` | bounded item row (title, `text` trimmed, `source_url`, `lore` links; no internal fields) |
| `list_records` | `kind`, `limit=50`, `offset=0` | `{count, rows}` for books, characters, speakers, canon_speakers, records (alias: triumphs), activities, seasons, events, lore, seals; `speakers` includes caption-only names, `canon_speakers` does not |
| `lore` | `ref` | manifest lore entry (body trimmed) with linked item names |
| `record` | `ref` | triumph or seal details |
| `seal` | `ref` | seal details and its triumph records |
| `seals` | none | `{count, rows}` for every manifest seal with record counts |
| `search` | `query`, `type?`, `limit=10`, `full=false`, `offset=0`, `rank=true`, `activity?`, `season?`, `event?`, `expansion?`, `class_tag?`, `exclude_stage=false`, `timeline?`, `lang?`, `entity?` | `{count, total, next_offset, rows}` with `snippet` and `timeline` (story-chapter slug) fields; ranked results demote stage directions/cutscene captions, `exclude_stage` drops them, `timeline` filters to one in-universe chapter, `entity` restricts to documents one entity is linked to (e.g. `entity="Savathûn"`) |
| `seasons` | none | all 28 seasons/episodes with official numbers and coverage |
| `stats` | none | row counts, top item types, top speakers |
| `transcript` | `ref`, `speaker?`, `limit=50`, `offset=0`, `full=false`, `include_stage=false`, `canon_only=false`, `section?`, `class_tag?` | transcript metadata and lines |
| `verify` | `quote`, `speaker?`, `exact=false` | `{quote, verified, speaker, exact, matches}`; a miss is a normal result, not an error |
| `verify_many` | `quotes`, `speaker?`, `exact=false` | up to 20 quote checks: `{verified, total, results}`, one result per quote in input order |

**Failure modes.** A search or listing with no match returns an empty `rows`
list and `total: 0`, not an error. Reference tools (`item`, `book`, `transcript`,
`activity`, `event`, `record`, `seal`, `lore`, `character_info`) raise a
`ToolError` naming the missing reference; use the matching `find_*` or `list_*`
tool to discover a valid one. Invalid arguments raise `ToolError` with the
accepted range.

MCP limits clamp to 1-100 to protect the agent's context; the CLI is not clamped
to 100 (the shared API allows up to 10,000). `offset` values above 10,000 clamp
to 10,000 (deep paging past that bound returns no rows by design). Full text is
trimmed to 4000 characters per row, and resource reads are capped at ~16,000
characters with a `[truncated; page via the matching tool]` marker.
`verify` is the quote-safety primitive: `verified` is true only for canonical text.
It matches normalized phrases against the verification index; punctuation-only
quotes fall back to an exact normalized-row lookup (mid-word fragments no longer
verify - submit the quote as written in canon).
`speaker` requires attribution (books and items, which have no speaker, are then
excluded); `exact` requires the normalized quote to equal a full canonical row
instead of matching a fragment.

## Resources

Read-only JSON resources for discovery without tool calls:

- `grimoire://books` - all lore books
- `grimoire://characters` - curated characters
- `grimoire://records` - triumphs and seals
- `grimoire://stats` - row counts
- `grimoire://entities` - the entity web index (every entity, alias and document counts)
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
- No arbitrary SQL tool is exposed. The twenty-two tools are the whole surface.
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
