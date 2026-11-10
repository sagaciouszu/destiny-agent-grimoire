# Agent Setup

## Sync all agents

OpenCode:

```bash
bash scripts/sync-live-agents.sh
```

Dry run first if you want to inspect the plan:

```bash
bash scripts/sync-live-agents.sh --dry-run
```

OpenClaw:

```bash
bash scripts/sync-live-agents.sh --openclaw
```

## Environment variables

| Variable | Purpose |
|---|---|
| `AGENT_REPOS_DIR` | parent directory containing the agent repos |
| `SERIES_MANIFEST` | alternate registry file |
| `OPENCODE_AGENTS` | OpenCode destination, default `~/.config/opencode/agents` |
| `OPENCLAW_ROOT` | OpenClaw root, default `~/.openclaw` |
| `NO_RELOAD` | set to `1` to skip reloading OpenCode after sync |

## Default OpenCode destination

```text
~/.config/opencode/agents/
```

Each ready agent gets:

- `agents/<id>.md`
- `agents/<id>-consult.md`
- `agents/<id>/`

The primary agent file is active. Other Markdown files in the workspace are
marked `disabled: true` so only the intended entry point loads.

## Set up one agent

Linux/macOS:

```bash
cd destiny-agent-eris-morn
bash setup.sh ../destiny-agent-grimoire --no-mcp
```

Windows:

```bat
cd destiny-agent-eris-morn
bash setup.sh path\to\destiny-agent-grimoire --no-mcp
```

Pass a path to this archive, for example `../destiny-agent-grimoire`.
`--no-mcp` skips the optional MCP install.

## OpenClaw MCP path

OpenClaw's update doctor starts MCP servers to validate their tool schema, and
it cannot resolve a bare `run.sh`. Onboarding takes care of this itself:

- `setup.sh` runs `lore/scripts/ensure-openclaw-mcp.sh` after the archive is
  linked. The ensure script pins openclaw.json's `grimoire` entry to the
  stable wrapper `~/.local/bin/grimoire-mcp` (which execs
  `$GRIMOIRE_ROOT/mcp-server/run.sh` via the `~/.local/share/grimoire`
  pointer symlink to this checkout), so relocating the archive only needs the
  symlink refreshed — openclaw.json stays untouched. Idempotent; backs up
  `openclaw.json` first; skips when OpenClaw is not installed.
- `scripts/sync-live-agents.sh --openclaw` re-checks it on every sync.

Verify with:

```bash
openclaw doctor --lint --only core/doctor/runtime-tool-schemas
```

## Windows links

`setup.sh` links the archive in three steps, so no manual work is usually
needed:

1. `ln -s` (works on Unix and on Git Bash with native symlinks)
2. `mklink /J` directory junction when `ln -s` is unavailable
3. `git clone` of the archive as a last resort

To link it yourself:

```bat
mklink /J lore ..\destiny-agent-grimoire
```

The agent expects `lore/` to resolve to this archive. If a stale copy blocks
the link, clear it first:

```bat
attrib -r -s -h lore /s /d
rmdir /s /q lore
```

## Check it works

```bash
python3 lore/db/query.py stats
```

If the counts print, the agent can read the archive. Start a conversation and ask
a question in the agent's area; a grounded answer cites verified lines from the
database.

## Use the agent

OpenCode lists the agent by its display name. Choose it, then talk normally.
The agent loads its core voice first and escalates to deeper modules only when
the conversation needs them.

To consult another persona from inside a conversation, use the matching
`<id>-consult` agent. Consult agents are read-only and answer in character; they
do not change your files or delegate further.
