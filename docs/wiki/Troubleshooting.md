# Troubleshooting

## Database missing

Symptom: `FATAL: database not built` or `no such table`.

Download the release asset:

```bash
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
```

The release also carries `grimoire.db.xz` (33.6 MiB) and `grimoire.db.gz`
(60.5 MiB) at the same static endpoint if the plain asset transfers slowly.

## Query returns nothing

Check the obvious causes first:

- FTS syntax in the query. Quote literal terms if needed.
- A filter that excludes the result, such as `--season`, `--activity` or
  `--expansion`.
- You built a core database instead of using the release asset; some optional tables are intentionally absent.

Use `python3 db/query.py stats` to confirm the database is populated.

## Agent not appearing in OpenCode

1. Restart OpenCode.
2. Re-run:

```bash
bash scripts/sync-live-agents.sh
```

3. Check the destination:

```text
~/.config/opencode/agents/<id>.md
```

4. Check `persona.json`; `ready: false` skips the agent.

## MCP not connecting

Run the server directly:

```bash
mcp-server/run.sh
```

Windows:

```bat
mcp-server\run.cmd
```

Check the client config at `~/.config/opencode/opencode.json` and use an absolute
path. Confirm the virtualenv exists:


## Lore directory left behind

If sync or setup leaves a partial `lore/` entry, remove it manually and re-run
sync. On Windows, remove the junction with `rmdir lore` (not `del`).

## Windows symlink failure

Use a junction:

```bat
mklink /J lore path\to\destiny-agent-grimoire
```

## Release checksum mismatch

Re-download the asset and compare against `SHA256SUMS`. Do not use a truncated or
partially downloaded database. If the mismatch persists, delete the file and download it again; do not
open or migrate a truncated database.

## First query is slow

The database is about 260 MB. Local SSD access is fast; a network drive, a cold
cache or a container bind mount can add seconds. Confirm the file is local and
that `python3 db/query.py stats` opens it without copying.
