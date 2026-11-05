# MCP Server

The optional MCP adapter exposes the archive as typed tools over stdio. It uses
the official MCP Python SDK (`mcp==2.3.0`) and opens SQLite read-only.

## Why MCP

- one adapter serves every agent and client
- no shell quoting or path handling
- structured arguments and JSON results
- limits, read-only access and quote verification enforced centrally
- same tools for OpenCode, Claude Desktop, Cursor and hosted agents

## Install

Linux/macOS:

```bash
bash mcp-server/install.sh
```

Windows:

```bat
cd mcp-server
python3 -m venv .venv
.venv\Scripts\pip.exe install --require-hashes -r requirements.lock.txt
```

The installer uses a hash-locked requirements file. Python 3.10+ is required.
The virtualenv is gitignored; the CLI remains dependency-free.

## Run

```bash
./mcp-server/run.sh
```

Windows (cmd):

```bat
mcp-server\run.cmd
```

Windows (PowerShell):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File mcp-server\run.ps1
```

The server speaks MCP on stdio and exits when the client disconnects. It must
stay running for as long as a client is using it: OpenCode starts and stops it
automatically, and a manually launched window must stay open. Do not run it as
a background daemon. Both launchers locate the virtualenv whether it uses
`.venv/bin` (Unix) or `.venv/Scripts` (Windows).

### Verify the install

```bash
bash mcp-server/probe.sh
```

The probe performs a real `initialize` -> `tools/list` handshake and prints the
21 exposed tools. On Windows run `python mcp-server\probe.py`.

### OpenClaw

OpenClaw's update doctor starts the server to validate its tool schema. Its
config must use an **absolute** launcher path; a bare `run.sh` is reported as
"not started for update validation". After an update:

```bash
openclaw doctor --lint --only core/doctor/runtime-tool-schemas
```

## OpenCode configuration

From this checkout:

```json
{
  "mcp": {
    "servers": {
      "grimoire": {
        "type": "local",
        "command": ["mcp-server/run.sh"]
      }
    }
  }
}
```

From an agent workspace, the archive is usually mounted at `lore/`:

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

Some clients require an absolute path. Use the path your client documents,
without committing machine-specific paths here. On Windows, point at `run.cmd`
or `run.ps1` (the latter via `powershell.exe -NoProfile -ExecutionPolicy Bypass -File`).

## Tools

| Tool | Purpose |
|---|---|
| `search` | full-text search with taxonomy filters |
| `character` | verified character lines |
| `item` | item details and lore |
| `verify` | quote verification |
| `verify_many` | up to 20 quotes at once |
| `character_info` | aliases and quote counts |
| `list_records` | books, characters, speakers, records, activities, seasons, events |
| `book` | book metadata and entries |
| `transcript` | transcript metadata and lines |
| `find_item` | item title or slug lookup |
| `activities` | activity list with coverage |
| `activity` | one activity with speakers and transcripts |
| `seasons` | all seasons and episodes with coverage |
| `events` | rotating events with occurrence counts |
| `event` | one event with yearly occurrences |
| `coverage` | coverage matrix, statuses and gap notes |
| `record` | triumph or seal record details |
| `seals` | every manifest seal with record counts |
| `seal` | one seal with its triumph records |
| `lore` | manifest lore entry with linked item names |
| `stats` | row counts and top values |

All 28 seasons and 9 events are exposed. Activity and coverage results include
`coverage_status` and evidence notes.

## Resources and prompts

Resources mirror the main reads: books, characters, records, stats, activities,
seasons, events, coverage and individual documents.

Prompts:

- `quote_safe_lookup(topic)` - search, then verify every quote
- `character_brief(name)` - metadata plus verified lines

## Safety

- SQLite URI `mode=ro`; writes fail at the driver level
- no arbitrary SQL tool
- no network access
- bounded inputs and clamped limits
- user text never interpolated into SQL
- control characters, bidi marks and zero-width characters stripped
- speaker matching respects name boundaries

## Test

```bash
mcp-server/.venv/bin/python tests/mcp-test.py
```

The contract test covers tool registration, search, verify accept/reject, limits,
read-only access and a real stdio handshake.
