# Troubleshooting

## Database missing

Symptom: `FATAL: database not built` or `no such table`.

```bash
python3 db/migrate.py
```

Or download the release asset:

```bash
curl -fsSL https://github.com/sagaciouszu/destiny-agent-grimoire/releases/latest/download/grimoire.db -o db/grimoire.db
```

The release also carries `grimoire.db.xz` (29 MiB) and `grimoire.db.gz`
(56 MiB) at the same static endpoint if the plain asset transfers slowly.

## Query returns nothing

Check the obvious causes first:

- FTS syntax in the query. Quote literal terms if needed.
- A filter that excludes the result, such as `--season`, `--activity` or
  `--expansion`.
- The database is unenriched. Run the enrichment steps and rebuild FTS.

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

## Agent audit fails after a data update

The persona count or generated quote index can be stale:

```bash
cd destiny-agent-grimoire
python3 tests/sync-doc-counts.py
```

Then rerun the agent master audit. Do not lower a count to make a test pass; fix
the data or regenerate the persona.

## Suite manifest failure

Symptom: `baseline suites missing` or `manifest and master-audit commands differ`.

A suite was removed or its command changed without updating
`tests/suites.json`. Re-add the suite or explicitly update the manifest and the
central baseline if the removal is intentional.

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

```bash
mcp-server/.venv/bin/python tests/mcp-test.py
```

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
partially downloaded database. If the mismatch persists, rebuild from the tagged
commit and treat the release asset as bad.

## Slow build

A full build takes about two minutes. Manifest enrichment can take longer on a
cold filesystem. If the build is much slower, check disk space and whether the
manifest archive is present under `archive/data/manifest/`.
