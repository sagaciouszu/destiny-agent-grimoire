# Agent Series

## Registry

`series/agents.json` is the only source of truth. It holds the agent id, display
name, source repository, entry file, summary and consult scope.

| Id | Agent | Source repository | Consult scope |
|---|---|---|---|
| `drifter` | The Drifter | `destiny-agent-drifter` | Gambit, the Nine, the Dark Age, his own past |
| `eris` | Eris Morn | `destiny-agent-eris-morn` | Hive, the Moon, Savathun, the Witness, ritual lore |
| `calus` | Emperor Calus | `destiny-agent-calus` | Calus, the Cabal, the Leviathan, Opulence |
| `zavala` | Commander Zavala | `destiny-agent-zavala` | The Vanguard, the Last City, the coalition |
| `ghost` | Ghost | `destiny-agent-ghost` | The Light, resurrection, the Traveler, the Guardian |
| `mara-sov` | Mara Sov | `destiny-agent-mara-sov` | The Awoken, the Dreaming City, the Ascendant Plane, Riven |

## Source repositories

By default the sync script expects the agent repos beside this archive:

```text
../
  destiny-agent-grimoire/
  destiny-agent-drifter/
  destiny-agent-eris-morn/
  destiny-agent-calus/
  destiny-agent-zavala/
  destiny-agent-ghost/
  destiny-agent-mara-sov/
```

Override the parent directory with `AGENT_REPOS_DIR`.

## Readiness

Each agent has a `persona.json`. If `ready` is `false`, sync skips that agent
without deleting an existing deployment.

## Consult IDs

- `drifter-consult`
- `eris-consult`
- `calus-consult`
- `zavala-consult`
- `ghost-consult`
- `mara-sov-consult`

Consult agents are read-only. They answer questions in character and must verify
quotes before using them.

## How to run one

```bash
cd destiny-agent-eris-morn
bash setup.sh ../destiny-agent-grimoire
```

Then choose the agent in your runtime. See [Agent Setup](Agent-Setup.md) for
OpenCode and OpenClaw deployment, destinations and environment variables.

## How to use them together

The primary agent answers in its own voice. A `<id>-consult` copy answers
questions from a peer persona when you need a second perspective. Consult copies
are read-only: they do not edit files, run commands or delegate again.

## Sync

```bash
bash scripts/sync-live-agents.sh
bash scripts/sync-live-agents.sh --dry-run
bash scripts/sync-live-agents.sh --openclaw
```

See [Agent Setup](Agent-Setup.md) for environment variables and destinations.
