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
  linked (idempotent; backs up `openclaw.json` first; skips when OpenClaw is
  not installed).
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

## Verify the deployment

```bash
python3 lore/db/query.py stats
bash lore/tests/agent-layout-test.sh
bash tests/master-audit.sh
```

Agent master audits:

| Agent | Suites |
|---|---:|
| Drifter | 22 |
| Eris | 17 |
| Calus | 15 |
| Zavala | 15 |
| Ghost | 15 |

The shared runner reads `tests/suites.json`:

```bash
bash tests/run-suites.sh
bash tests/run-suites.sh --tier core
```

Suite additions are allowed. Removals fail the central manifest guard.
